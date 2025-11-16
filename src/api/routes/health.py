"""Health check endpoints"""

from fastapi import APIRouter, status
from pydantic import BaseModel
from datetime import datetime
import psycopg2
from opensearchpy import OpenSearch

from src.core.config import settings

router = APIRouter()


class HealthStatus(BaseModel):
    """Health check response"""

    status: str
    timestamp: datetime
    version: str
    services: dict


@router.get("/health", response_model=HealthStatus)
async def health_check():
    """
    Comprehensive health check for all services

    Returns service status for:
    - API (always healthy if responding)
    - PostgreSQL database
    - OpenSearch cluster
    - Redis cache
    """
    services = {}

    # Check PostgreSQL
    try:
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            connect_timeout=5,
        )
        conn.close()
        services["postgres"] = "healthy"
    except Exception as e:
        services["postgres"] = f"unhealthy: {str(e)}"

    # Check OpenSearch
    try:
        es = OpenSearch(
            hosts=[{"host": settings.OPENSEARCH_HOST, "port": settings.OPENSEARCH_PORT}],
            http_auth=(
                (settings.OPENSEARCH_USER, settings.OPENSEARCH_PASSWORD)
                if settings.OPENSEARCH_USER
                else None
            ),
            use_ssl=settings.OPENSEARCH_USE_SSL,
            verify_certs=settings.OPENSEARCH_VERIFY_CERTS,
            timeout=5,
        )
        health = es.cluster.health()
        services["opensearch"] = health["status"]
    except Exception as e:
        services["opensearch"] = f"unhealthy: {str(e)}"

    # Check Redis
    try:
        import redis

        r = redis.from_url(settings.redis_url, socket_connect_timeout=5)
        r.ping()
        services["redis"] = "healthy"
    except Exception as e:
        services["redis"] = f"unhealthy: {str(e)}"

    # Overall status
    overall_status = (
        "healthy"
        if all(s in ["healthy", "green", "yellow"] for s in services.values())
        else "degraded"
    )

    return HealthStatus(
        status=overall_status,
        timestamp=datetime.utcnow(),
        version=settings.APP_VERSION,
        services=services,
    )


@router.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness_check():
    """Kubernetes readiness probe"""
    return {"status": "ready"}


@router.get("/health/live", status_code=status.HTTP_200_OK)
async def liveness_check():
    """Kubernetes liveness probe"""
    return {"status": "alive"}
