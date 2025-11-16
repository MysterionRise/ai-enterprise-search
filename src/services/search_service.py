"""Search service with hybrid BM25 + k-NN retrieval"""

from typing import List, Dict, Any, Optional
from collections import defaultdict
import time
import logging

from src.models.search import SearchRequest, SearchResponse, SearchResult, Facet, FacetGroup
from src.services.opensearch_service import opensearch_service
from src.services.embedding_service import embedding_service
from src.core.config import settings

logger = logging.getLogger(__name__)


class SearchService:
    """Service for executing search queries"""

    def __init__(self):
        self.os_client = opensearch_service.client
        self.chunks_index = settings.CHUNKS_INDEX

    async def search(self, request: SearchRequest) -> SearchResponse:
        """
        Execute hybrid search with BM25 + k-NN + RRF fusion

        Args:
            request: Search request with query and filters

        Returns:
            Search response with results and facets
        """
        start_time = time.time()

        # Build ACL filter from user groups
        acl_filter = self._build_acl_filter(request.user_groups)

        # Build additional filters
        filters = self._build_filters(request)

        if request.use_hybrid:
            # Hybrid: BM25 + k-NN with RRF fusion
            results, total = await self._hybrid_search(
                query=request.query,
                acl_filter=acl_filter,
                filters=filters,
                size=request.size,
                offset=request.offset,
                boost_recency=request.boost_recency,
                boost_personalization=request.boost_personalization,
                user_country=request.user_country,
                user_department=request.user_department,
            )
        else:
            # BM25 only
            results, total = await self._bm25_search(
                query=request.query,
                acl_filter=acl_filter,
                filters=filters,
                size=request.size,
                offset=request.offset,
            )

        # Get facets
        facets = await self._get_facets(query=request.query, acl_filter=acl_filter, filters=filters)

        took_ms = int((time.time() - start_time) * 1000)

        return SearchResponse(
            query=request.query,
            results=results,
            total=total,
            took_ms=took_ms,
            facets=facets,
            applied_filters=self._extract_applied_filters(request),
            personalized=request.boost_personalization,
            personalization_context=(
                {"country": request.user_country, "department": request.user_department}
                if request.boost_personalization
                else None
            ),
        )

    async def _bm25_search(
        self, query: str, acl_filter: Dict, filters: List[Dict], size: int, offset: int
    ) -> tuple[List[SearchResult], int]:
        """Execute BM25 text search"""
        search_body = {
            "query": {
                "bool": {
                    "must": {
                        "multi_match": {
                            "query": query,
                            "fields": ["title^3", "text^1"],
                            "type": "best_fields",
                            "operator": "or",
                        }
                    },
                    "filter": [acl_filter] + filters,
                }
            },
            "size": size,
            "from": offset,
            "highlight": {
                "fields": {"title": {}, "text": {"fragment_size": 200, "number_of_fragments": 3}}
            },
        }

        response = self.os_client.search(index=self.chunks_index, body=search_body)
        results = self._format_results(response)
        total = response["hits"]["total"]["value"]

        return results, total

    async def _hybrid_search(
        self,
        query: str,
        acl_filter: Dict,
        filters: List[Dict],
        size: int,
        offset: int,
        boost_recency: bool,
        boost_personalization: bool,
        user_country: Optional[str],
        user_department: Optional[str],
    ) -> tuple[List[SearchResult], int]:
        """Execute hybrid BM25 + k-NN search with RRF fusion"""

        # 1. BM25 Search
        bm25_body = {
            "query": {
                "bool": {
                    "must": {
                        "multi_match": {
                            "query": query,
                            "fields": ["title^3", "text^1"],
                            "type": "best_fields",
                        }
                    },
                    "filter": [acl_filter] + filters,
                }
            },
            "size": size * 2,  # Get more for fusion
        }

        bm25_response = self.os_client.search(index=self.chunks_index, body=bm25_body)
        bm25_hits = bm25_response["hits"]["hits"]

        # 2. k-NN Vector Search
        query_vector = embedding_service.embed_text(query)

        knn_body = {
            "size": size * 2,
            "query": {
                "bool": {
                    "must": {"knn": {"embedding": {"vector": query_vector, "k": size * 2}}},
                    "filter": [acl_filter] + filters,
                }
            },
        }

        knn_response = self.os_client.search(index=self.chunks_index, body=knn_body)
        knn_hits = knn_response["hits"]["hits"]

        # 3. RRF Fusion
        fused_results = self._rrf_fusion(bm25_hits, knn_hits, k=settings.RRF_K)

        # 4. Apply personalization boosts
        if boost_personalization and (user_country or user_department):
            fused_results = self._apply_personalization_boost(
                fused_results, user_country, user_department
            )

        # 5. Sort by score and paginate
        fused_results.sort(key=lambda x: x["_score"], reverse=True)
        paginated = fused_results[offset : offset + size]

        # 6. Format results with highlights
        results = self._format_results({"hits": {"hits": paginated}})
        total = len(fused_results)

        return results, total

    def _rrf_fusion(self, bm25_hits: List[Dict], knn_hits: List[Dict], k: int = 60) -> List[Dict]:
        """
        Reciprocal Rank Fusion

        score = sum(1 / (k + rank_i))

        Args:
            bm25_hits: Results from BM25 search
            knn_hits: Results from k-NN search
            k: RRF constant (default 60)

        Returns:
            Fused and ranked results
        """
        scores = defaultdict(float)
        docs = {}

        # Process BM25 results
        for rank, hit in enumerate(bm25_hits, start=1):
            doc_id = hit["_id"]
            scores[doc_id] += 1.0 / (k + rank)
            docs[doc_id] = hit

        # Process k-NN results
        for rank, hit in enumerate(knn_hits, start=1):
            doc_id = hit["_id"]
            scores[doc_id] += 1.0 / (k + rank)
            if doc_id not in docs:
                docs[doc_id] = hit

        # Build final results with RRF scores
        fused = []
        for doc_id, score in scores.items():
            doc = docs[doc_id]
            doc["_score"] = score
            fused.append(doc)

        return fused

    def _apply_personalization_boost(
        self, results: List[Dict], user_country: Optional[str], user_department: Optional[str]
    ) -> List[Dict]:
        """Apply personalization score boosts"""
        for hit in results:
            source = hit["_source"]
            boost = 1.0

            # Boost matching country
            if user_country and user_country in source.get("country_tags", []):
                boost *= 1.3

            # Boost matching department
            if user_department and source.get("department") == user_department:
                boost *= 1.2

            hit["_score"] *= boost

        return results

    def _build_acl_filter(self, user_groups: List[str]) -> Dict:
        """Build ACL filter for security trimming"""
        if not user_groups:
            user_groups = ["all-employees"]

        return {
            "bool": {
                "must": {"terms": {"acl_allow": user_groups}},
                "must_not": {"terms": {"acl_deny": user_groups}},
            }
        }

    def _build_filters(self, request: SearchRequest) -> List[Dict]:
        """Build OpenSearch filters from search request"""
        filters = []

        if not request.filters:
            return filters

        if request.filters.sources:
            filters.append({"terms": {"source": request.filters.sources}})

        if request.filters.languages:
            filters.append({"terms": {"language": request.filters.languages}})

        if request.filters.countries:
            filters.append({"terms": {"country_tags": request.filters.countries}})

        if request.filters.departments:
            filters.append({"terms": {"department": request.filters.departments}})

        if request.filters.content_types:
            filters.append({"terms": {"content_type": request.filters.content_types}})

        if request.filters.date_from or request.filters.date_to:
            date_filter = {"range": {"last_modified": {}}}
            if request.filters.date_from:
                date_filter["range"]["last_modified"]["gte"] = request.filters.date_from
            if request.filters.date_to:
                date_filter["range"]["last_modified"]["lte"] = request.filters.date_to
            filters.append(date_filter)

        return filters

    def _format_results(self, response: Dict) -> List[SearchResult]:
        """Format OpenSearch response to SearchResult models"""
        results = []

        for hit in response["hits"]["hits"]:
            source = hit["_source"]

            # Get highlighted snippet
            highlights = hit.get("highlight", {})
            snippet = ""
            if "text" in highlights:
                snippet = " ... ".join(highlights["text"])
            elif "title" in highlights:
                snippet = highlights["title"][0]
            else:
                snippet = source.get("text", "")[:300]

            result = SearchResult(
                doc_id=source["doc_id"],
                chunk_id=source.get("chunk_id"),
                source=source["source"],
                title=source["title"],
                url=source.get("url"),
                snippet=snippet,
                score=hit["_score"],
                content_type=source.get("content_type", "unknown"),
                language=source.get("language", "en"),
                last_modified=source.get("last_modified"),
                country_tags=source.get("country_tags", []),
                department=source.get("department"),
                highlights=highlights,
            )
            results.append(result)

        return results

    async def _get_facets(
        self, query: str, acl_filter: Dict, filters: List[Dict]
    ) -> List[FacetGroup]:
        """Get facets for filtering"""
        # Build aggregations query
        agg_body = {
            "size": 0,
            "query": {
                "bool": {
                    "must": {"multi_match": {"query": query, "fields": ["title", "text"]}},
                    "filter": [acl_filter] + filters,
                }
            },
            "aggs": {
                "sources": {"terms": {"field": "source", "size": 20}},
                "languages": {"terms": {"field": "language", "size": 10}},
                "countries": {"terms": {"field": "country_tags", "size": 20}},
                "content_types": {"terms": {"field": "content_type", "size": 10}},
            },
        }

        response = self.os_client.search(index=self.chunks_index, body=agg_body)

        facet_groups = []
        for field, agg_name in [
            ("source", "sources"),
            ("language", "languages"),
            ("country", "countries"),
            ("content_type", "content_types"),
        ]:
            buckets = response["aggregations"][agg_name]["buckets"]
            facets = [
                Facet(name=field, value=bucket["key"], count=bucket["doc_count"])
                for bucket in buckets
            ]
            if facets:
                facet_groups.append(FacetGroup(field=field, facets=facets))

        return facet_groups

    def _extract_applied_filters(self, request: SearchRequest) -> Dict[str, List[str]]:
        """Extract applied filters for display"""
        applied = {}
        if request.filters:
            if request.filters.sources:
                applied["sources"] = request.filters.sources
            if request.filters.languages:
                applied["languages"] = request.filters.languages
            if request.filters.countries:
                applied["countries"] = request.filters.countries
        return applied

    async def get_suggestions(self, query: str, size: int = 5) -> List[str]:
        """Get autocomplete suggestions"""
        # Simple implementation - in production, use completion suggester
        # For now, return popular queries from search_queries table
        # This would query the database for matching queries
        return []


# Global instance
search_service = SearchService()
