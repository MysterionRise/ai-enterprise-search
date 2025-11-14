"""Load mock data into the search index"""
import sys
import os
import json
import asyncio

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.models.documents import DocumentIngestRequest
from src.services.ingest_service import ingest_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def load_documents(data_file="data/mock/enterprise_documents.json"):
    """Load mock documents from JSON file"""

    if not os.path.exists(data_file):
        logger.error(f"Data file not found: {data_file}")
        logger.info("Run: python scripts/generate_mock_data.py first")
        sys.exit(1)

    with open(data_file, 'r', encoding='utf-8') as f:
        documents = json.load(f)

    logger.info(f"Loading {len(documents)} documents...")

    success_count = 0
    error_count = 0

    for doc in documents:
        try:
            request = DocumentIngestRequest(
                source=doc["source"],
                source_id=doc["source_id"],
                title=doc["title"],
                url=doc.get("url"),
                content=doc["content"],
                content_type=doc.get("content_type", "text/plain"),
                acl_allow=doc.get("acl_allow", ["all-employees"]),
                country_tags=doc.get("country_tags", []),
                department=doc.get("department"),
                tags=doc.get("tags", []),
                metadata=doc.get("metadata")
            )

            result = await ingest_service.ingest_document(request)

            if result.status == "success":
                logger.info(f"✓ Indexed: {doc['title']} ({result.chunks_created} chunks)")
                success_count += 1
            else:
                logger.error(f"✗ Failed: {doc['title']} - {result.message}")
                error_count += 1

        except Exception as e:
            logger.error(f"✗ Error indexing {doc['title']}: {e}")
            error_count += 1

    logger.info(f"\nComplete! Success: {success_count}, Errors: {error_count}")


if __name__ == "__main__":
    asyncio.run(load_documents())
