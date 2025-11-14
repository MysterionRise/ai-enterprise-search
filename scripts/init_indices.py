"""Initialize OpenSearch indices"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.services.opensearch_service import opensearch_service
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Initialize all OpenSearch indices"""
    try:
        logger.info("Initializing OpenSearch indices...")

        # Create indices
        opensearch_service.initialize_indices()

        # Check cluster health
        health = opensearch_service.get_cluster_health()
        logger.info(f"Cluster health: {health['status']}")

        logger.info("Indices initialized successfully!")

    except Exception as e:
        logger.error(f"Failed to initialize indices: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
