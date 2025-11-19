"""
Recommendation Service
Provides content-based, collaborative, and trending recommendations
"""

import logging

from src.models.auth import User
from src.services.opensearch_service import opensearch_service

logger = logging.getLogger(__name__)


class RecommendationService:
    """Service for generating personalized recommendations"""

    def __init__(self):
        self.os_client = opensearch_service.client
        self.chunks_index = "enterprise-chunks"

    async def get_related_documents(self, doc_id: str, user: User, limit: int = 5) -> list[dict]:
        """
        Get documents similar to the given document (content-based filtering)
        Uses vector similarity on embeddings

        Args:
            doc_id: Document ID to find similar documents for
            user: Current user (for ACL filtering)
            limit: Maximum number of recommendations

        Returns:
            List of similar documents with scores
        """
        try:
            # Get the document's first chunk embedding to represent the document
            doc_query = {
                "query": {"match": {"doc_id": doc_id}},
                "size": 1,
                "_source": ["embedding", "doc_id", "title"],
            }

            doc_response = self.os_client.search(index=self.chunks_index, body=doc_query)

            if not doc_response["hits"]["hits"]:
                logger.warning(f"Document {doc_id} not found for recommendations")
                return []

            # Get the embedding from the first chunk
            doc_embedding = doc_response["hits"]["hits"][0]["_source"].get("embedding")
            if not doc_embedding:
                logger.warning(f"No embedding found for document {doc_id}")
                return []

            # Search for similar documents using k-NN
            # Get more results to account for filtering
            knn_query = {
                "size": limit * 3,
                "query": {
                    "bool": {
                        "must": {
                            "knn": {
                                "embedding": {
                                    "vector": doc_embedding,
                                    "k": limit * 3,
                                }
                            }
                        },
                        "filter": [
                            # ACL filtering
                            {"terms": {"acl_allow": user.groups}},
                        ],
                        "must_not": [
                            # Exclude the source document
                            {"term": {"doc_id": doc_id}},
                            # Exclude documents user can't access
                            {"terms": {"acl_deny": user.groups}},
                        ],
                    }
                },
                "_source": [
                    "doc_id",
                    "title",
                    "source",
                    "country_tags",
                    "department",
                ],
                "collapse": {"field": "doc_id"},  # One result per document
            }

            response = self.os_client.search(index=self.chunks_index, body=knn_query)

            # Process results
            related = []
            seen_docs = set()

            for hit in response["hits"]["hits"]:
                source = hit["_source"]
                doc_id_result = source.get("doc_id")

                # Deduplicate by doc_id
                if doc_id_result in seen_docs:
                    continue
                seen_docs.add(doc_id_result)

                # Apply personalization boost
                score = hit["_score"]
                if user.country and user.country in source.get("country_tags", []):
                    score *= 1.2
                if user.department and user.department == source.get("department"):
                    score *= 1.1

                related.append(
                    {
                        "doc_id": doc_id_result,
                        "title": source.get("title", "Unknown"),
                        "source": source.get("source", "unknown"),
                        "score": score,
                        "reason": "similar_content",
                    }
                )

                if len(related) >= limit:
                    break

            # Sort by score descending
            related.sort(key=lambda x: x["score"], reverse=True)

            logger.info(f"Found {len(related)} related documents for {doc_id}")
            return related[:limit]

        except Exception as e:
            logger.error(f"Failed to get related documents: {e}", exc_info=True)
            return []

    async def get_trending(
        self, hours: int = 24, limit: int = 10, user: User | None = None
    ) -> list[dict]:
        """
        Get trending documents (time-decayed popularity)

        For now, uses mock data. In production, would use:
        score = (view_count / age_hours^0.8) * (1 + avg_dwell_time/60000)

        Args:
            hours: Time window for trending calculation
            limit: Maximum number of results
            user: Optional user for ACL filtering

        Returns:
            List of trending documents
        """
        try:
            # Mock trending data for demo
            # In production, this would query document_views table
            trending_mock = [
                {
                    "doc_id": "confluence-policy-2024-q4",
                    "title": "Q4 2024 Company Strategy Update",
                    "source": "confluence",
                    "trend_score": 234.5,
                    "view_count": 156,
                    "age_hours": 12,
                    "reason": "trending",
                },
                {
                    "doc_id": "servicenow-kb-benefits-2024",
                    "title": "2024 Benefits Enrollment Deadline",
                    "source": "servicenow",
                    "trend_score": 187.3,
                    "view_count": 98,
                    "age_hours": 8,
                    "reason": "trending",
                },
                {
                    "doc_id": "sharepoint-expense-policy-new",
                    "title": "Updated Expense Reimbursement Policy",
                    "source": "sharepoint",
                    "trend_score": 156.8,
                    "view_count": 67,
                    "age_hours": 16,
                    "reason": "trending",
                },
                {
                    "doc_id": "confluence-wfh-guidelines-2024",
                    "title": "Work From Home Best Practices",
                    "source": "confluence",
                    "trend_score": 142.1,
                    "view_count": 89,
                    "age_hours": 24,
                    "reason": "trending",
                },
                {
                    "doc_id": "servicenow-it-vpn-setup",
                    "title": "VPN Setup Guide for New Employees",
                    "source": "servicenow",
                    "trend_score": 128.5,
                    "view_count": 45,
                    "age_hours": 6,
                    "reason": "trending",
                },
            ]

            # Filter by user ACL if provided
            # For now, return mock data
            # TODO: Implement real analytics-based trending

            logger.info(f"Returning {len(trending_mock)} trending documents")
            return trending_mock[:limit]

        except Exception as e:
            logger.error(f"Failed to get trending documents: {e}", exc_info=True)
            return []

    async def get_popular_in_department(
        self,
        department: str,
        country: str | None = None,
        days: int = 30,
        limit: int = 10,
    ) -> list[dict]:
        """
        Get most popular documents in a department (collaborative filtering)

        For now, uses mock data. In production, would query:
        - document_views table grouped by department
        - Filter by time window
        - Rank by view count and unique users

        Args:
            department: Department name (e.g., "HR", "Engineering")
            country: Optional country filter
            days: Time window in days
            limit: Maximum number of results

        Returns:
            List of popular documents
        """
        try:
            # Mock popular documents by department
            popular_by_dept = {
                "HR": [
                    {
                        "doc_id": "servicenow-leave-policy",
                        "title": "Annual Leave Policy",
                        "source": "servicenow",
                        "view_count": 245,
                        "unique_viewers": 87,
                        "avg_dwell_time_ms": 180000,  # 3 minutes
                        "reason": "popular_in_hr",
                    },
                    {
                        "doc_id": "sharepoint-recruitment",
                        "title": "Recruitment Guidelines 2024",
                        "source": "sharepoint",
                        "view_count": 198,
                        "unique_viewers": 65,
                        "avg_dwell_time_ms": 240000,  # 4 minutes
                        "reason": "popular_in_hr",
                    },
                    {
                        "doc_id": "confluence-performance-review",
                        "title": "Performance Review Process",
                        "source": "confluence",
                        "view_count": 187,
                        "unique_viewers": 78,
                        "avg_dwell_time_ms": 300000,  # 5 minutes
                        "reason": "popular_in_hr",
                    },
                ],
                "Engineering": [
                    {
                        "doc_id": "confluence-deployment-guide",
                        "title": "Production Deployment Checklist",
                        "source": "confluence",
                        "view_count": 312,
                        "unique_viewers": 98,
                        "avg_dwell_time_ms": 420000,  # 7 minutes
                        "reason": "popular_in_engineering",
                    },
                    {
                        "doc_id": "github-code-review",
                        "title": "Code Review Best Practices",
                        "source": "github",
                        "view_count": 289,
                        "unique_viewers": 102,
                        "avg_dwell_time_ms": 360000,  # 6 minutes
                        "reason": "popular_in_engineering",
                    },
                    {
                        "doc_id": "confluence-oncall-runbook",
                        "title": "On-Call Incident Response Runbook",
                        "source": "confluence",
                        "view_count": 267,
                        "unique_viewers": 89,
                        "avg_dwell_time_ms": 480000,  # 8 minutes
                        "reason": "popular_in_engineering",
                    },
                ],
                "IT": [
                    {
                        "doc_id": "servicenow-helpdesk-guide",
                        "title": "IT Helpdesk Ticket Guidelines",
                        "source": "servicenow",
                        "view_count": 423,
                        "unique_viewers": 134,
                        "avg_dwell_time_ms": 240000,
                        "reason": "popular_in_it",
                    },
                    {
                        "doc_id": "confluence-security-policy",
                        "title": "Information Security Policy",
                        "source": "confluence",
                        "view_count": 398,
                        "unique_viewers": 156,
                        "avg_dwell_time_ms": 360000,
                        "reason": "popular_in_it",
                    },
                ],
            }

            # Get popular docs for department
            popular = popular_by_dept.get(
                department, popular_by_dept.get("HR", [])
            )  # Default to HR

            logger.info(f"Returning {len(popular)} popular documents for {department}")
            return popular[:limit]

        except Exception as e:
            logger.error(f"Failed to get popular documents: {e}", exc_info=True)
            return []

    async def get_personalized_recommendations(self, user: User, limit: int = 10) -> list[dict]:
        """
        Get personalized recommendations for user
        Combines: popular in department + trending + similar to recent views

        Args:
            user: Current user
            limit: Maximum number of recommendations

        Returns:
            List of personalized recommendations
        """
        try:
            recommendations = []

            # 1. Popular in user's department (40% weight)
            popular = await self.get_popular_in_department(
                department=user.department or "HR",
                country=user.country,
                days=30,
                limit=4,
            )
            recommendations.extend(popular[:4])

            # 2. Trending (40% weight)
            trending = await self.get_trending(hours=48, limit=4, user=user)
            recommendations.extend(trending[:4])

            # 3. For remaining slots, add more trending content
            if len(recommendations) < limit:
                additional_trending = await self.get_trending(
                    hours=72, limit=limit - len(recommendations), user=user
                )
                recommendations.extend(additional_trending)

            # Deduplicate by doc_id
            seen = set()
            unique_recommendations = []
            for rec in recommendations:
                if rec["doc_id"] not in seen:
                    seen.add(rec["doc_id"])
                    unique_recommendations.append(rec)

            logger.info(
                f"Generated {len(unique_recommendations)} personalized "
                f"recommendations for {user.username}"
            )
            return unique_recommendations[:limit]

        except Exception as e:
            logger.error(f"Failed to get personalized recommendations: {e}", exc_info=True)
            return []
