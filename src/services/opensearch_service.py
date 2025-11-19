"""OpenSearch client and index management"""

import logging
from typing import Any

from opensearchpy import OpenSearch, helpers

from src.core.config import settings

logger = logging.getLogger(__name__)


class OpenSearchService:
    """Service for OpenSearch operations"""

    def __init__(self):
        """Initialize OpenSearch client"""
        self.client = OpenSearch(
            hosts=[{"host": settings.OPENSEARCH_HOST, "port": settings.OPENSEARCH_PORT}],
            http_auth=(
                (settings.OPENSEARCH_USER, settings.OPENSEARCH_PASSWORD)
                if settings.OPENSEARCH_USER
                else None
            ),
            use_ssl=settings.OPENSEARCH_USE_SSL,
            verify_certs=settings.OPENSEARCH_VERIFY_CERTS,
            timeout=settings.OPENSEARCH_TIMEOUT,
        )

    def create_documents_index(self, index_name: str | None = None) -> bool:
        """
        Create the documents index with BM25 text fields

        This index stores document-level metadata and full text for BM25 search.
        """
        index_name = index_name or settings.DOCUMENTS_INDEX

        index_body = {
            "settings": {
                "index": {
                    "number_of_shards": 2,
                    "number_of_replicas": 1,
                    "refresh_interval": "30s",
                },
                "analysis": {
                    "filter": {
                        "english_stop": {"type": "stop", "stopwords": "_english_"},
                        "english_stemmer": {"type": "stemmer", "language": "english"},
                        "synonym_filter": {
                            "type": "synonym",
                            "synonyms": [
                                "wfh, work from home, remote work",
                                "hr, human resources",
                                "pto, paid time off, vacation, leave",
                                "it, information technology",
                            ],
                        },
                    },
                    "analyzer": {
                        "default_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": [
                                "lowercase",
                                "english_stop",
                                "english_stemmer",
                                "synonym_filter",
                            ],
                        }
                    },
                },
            },
            "mappings": {
                "properties": {
                    "doc_id": {"type": "keyword"},
                    "source": {"type": "keyword"},
                    "source_id": {"type": "keyword"},
                    "title": {
                        "type": "text",
                        "analyzer": "default_analyzer",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "body": {"type": "text", "analyzer": "default_analyzer"},
                    "url": {"type": "keyword"},
                    "content_type": {"type": "keyword"},
                    "language": {"type": "keyword"},
                    # Access control
                    "acl_allow": {"type": "keyword"},
                    "acl_deny": {"type": "keyword"},
                    # Personalization
                    "country_tags": {"type": "keyword"},
                    "department": {"type": "keyword"},
                    "audience": {"type": "keyword"},
                    # Metadata
                    "tags": {"type": "keyword"},
                    "categories": {"type": "keyword"},
                    "hash": {"type": "keyword"},
                    # Timestamps
                    "last_modified": {"type": "date"},
                    "indexed_at": {"type": "date"},
                    # Extended metadata
                    "metadata": {"type": "object", "enabled": False},
                }
            },
        }

        if self.client.indices.exists(index=index_name):
            logger.info(f"Index {index_name} already exists")
            return False

        self.client.indices.create(index=index_name, body=index_body)
        logger.info(f"Created index {index_name}")
        return True

    def create_chunks_index(self, index_name: str | None = None) -> bool:
        """
        Create the chunks index with k-NN vectors for semantic search

        This index stores document chunks with dense vector embeddings
        for hybrid BM25 + k-NN retrieval.
        """
        index_name = index_name or settings.CHUNKS_INDEX

        index_body = {
            "settings": {
                "index": {
                    "number_of_shards": 2,
                    "number_of_replicas": 1,
                    "refresh_interval": "30s",
                    "knn": True,  # Enable k-NN
                    "knn.algo_param.ef_search": 100,
                },
                "analysis": {"analyzer": {"default": {"type": "standard"}}},
            },
            "mappings": {
                "properties": {
                    "chunk_id": {"type": "keyword"},
                    "doc_id": {"type": "keyword"},
                    "chunk_idx": {"type": "integer"},
                    "text": {"type": "text", "analyzer": "default"},
                    # Copy from parent document
                    "source": {"type": "keyword"},
                    "title": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                    "url": {"type": "keyword"},
                    "language": {"type": "keyword"},
                    "content_type": {"type": "keyword"},
                    # Access control
                    "acl_allow": {"type": "keyword"},
                    "acl_deny": {"type": "keyword"},
                    # Personalization
                    "country_tags": {"type": "keyword"},
                    "department": {"type": "keyword"},
                    # Vector embedding for semantic search
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": settings.EMBEDDING_DIMENSION,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "faiss",
                            "parameters": {"ef_construction": 256, "m": 16},
                        },
                    },
                    # Context
                    "char_start": {"type": "integer"},
                    "char_end": {"type": "integer"},
                    # Timestamps
                    "last_modified": {"type": "date"},
                    "indexed_at": {"type": "date"},
                }
            },
        }

        if self.client.indices.exists(index=index_name):
            logger.info(f"Index {index_name} already exists")
            return False

        self.client.indices.create(index=index_name, body=index_body)
        logger.info(f"Created index {index_name}")
        return True

    def initialize_indices(self):
        """Create all required indices"""
        self.create_documents_index()
        self.create_chunks_index()
        logger.info("All indices initialized")

    def bulk_index_documents(self, documents: list[dict[str, Any]], index_name: str | None = None):
        """
        Bulk index documents

        Args:
            documents: List of document dictionaries
            index_name: Target index (defaults to DOCUMENTS_INDEX)
        """
        index_name = index_name or settings.DOCUMENTS_INDEX

        actions = [
            {"_index": index_name, "_id": doc["doc_id"], "_source": doc} for doc in documents
        ]

        success, failed = helpers.bulk(self.client, actions, stats_only=True)
        logger.info(f"Bulk indexed {success} documents, {failed} failed")
        return success, failed

    def bulk_index_chunks(self, chunks: list[dict[str, Any]], index_name: str | None = None):
        """
        Bulk index document chunks

        Args:
            chunks: List of chunk dictionaries
            index_name: Target index (defaults to CHUNKS_INDEX)
        """
        index_name = index_name or settings.CHUNKS_INDEX

        actions = [
            {"_index": index_name, "_id": chunk["chunk_id"], "_source": chunk} for chunk in chunks
        ]

        success, failed = helpers.bulk(self.client, actions, stats_only=True)
        logger.info(f"Bulk indexed {success} chunks, {failed} failed")
        return success, failed

    def delete_document(self, doc_id: str):
        """Delete document and all its chunks"""
        # Delete from documents index
        try:
            self.client.delete(index=settings.DOCUMENTS_INDEX, id=doc_id)
        except Exception as e:
            logger.warning(f"Failed to delete document {doc_id}: {e}")

        # Delete all chunks
        query = {"query": {"term": {"doc_id": doc_id}}}
        self.client.delete_by_query(index=settings.CHUNKS_INDEX, body=query)
        logger.info(f"Deleted document {doc_id} and its chunks")

    def get_cluster_health(self) -> dict[str, Any]:
        """Get OpenSearch cluster health"""
        return self.client.cluster.health()

    def get_index_stats(self, index_name: str) -> dict[str, Any]:
        """Get statistics for an index"""
        return self.client.indices.stats(index=index_name)

    async def get_document(self, doc_id: str) -> dict[str, Any] | None:
        """
        Get a document by ID from the documents index

        Args:
            doc_id: Document ID to retrieve

        Returns:
            Document data dict or None if not found
        """
        try:
            response = self.client.get(index=settings.DOCUMENTS_INDEX, id=doc_id)
            return response["_source"]
        except Exception as e:
            logger.warning(f"Document {doc_id} not found: {e}")
            return None

    async def get_document_chunks(self, doc_id: str, limit: int = 100) -> list[dict[str, Any]]:
        """
        Get all chunks for a document

        Args:
            doc_id: Parent document ID
            limit: Maximum number of chunks to return

        Returns:
            List of chunk data dicts
        """
        try:
            query = {
                "query": {"term": {"doc_id": doc_id}},
                "sort": [{"chunk_idx": "asc"}],
                "size": limit,
            }
            response = self.client.search(index=settings.CHUNKS_INDEX, body=query)
            return [hit["_source"] for hit in response["hits"]["hits"]]
        except Exception as e:
            logger.error(f"Failed to get chunks for doc {doc_id}: {e}")
            return []


# Global instance
opensearch_service = OpenSearchService()
