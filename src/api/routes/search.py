"""Search endpoints"""

from fastapi import APIRouter, Security, HTTPException
from typing import Annotated
import logging

from src.models.search import SearchRequest, SearchResponse, SuggestRequest, SuggestResponse
from src.models.auth import TokenData
from src.core.security import get_current_user
from src.services.search_service import SearchService
from src.core.database import log_search_query

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/query", response_model=SearchResponse)
async def search(
    request: SearchRequest, current_user: Annotated[TokenData, Security(get_current_user)]
):
    """
    Execute hybrid search query with personalization

    This endpoint performs:
    1. Security trimming based on user's ACL groups
    2. BM25 + vector search with RRF fusion (if hybrid enabled)
    3. Personalization boosts based on user's country/department
    4. Faceted results for filtering

    User context (groups, department, country) is automatically
    extracted from the JWT token for personalization and access control.
    """
    try:
        # Inject user context for personalization and ACL
        request.user_groups = current_user.groups
        request.user_country = current_user.country
        request.user_department = current_user.department

        # Execute search
        search_service = SearchService()
        response = await search_service.search(request)

        # Log query for analytics
        try:
            log_search_query(
                query_text=request.query,
                username=current_user.username,
                user_groups=current_user.groups,
                filters=request.filters.dict() if request.filters else {},
                results_count=response.total,
            )
        except Exception as e:
            logger.warning(f"Failed to log search query: {e}")

        return response

    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.post("/suggest", response_model=SuggestResponse)
async def suggest(
    request: SuggestRequest, current_user: Annotated[TokenData, Security(get_current_user)]
):
    """
    Get autocomplete suggestions for search queries

    Returns popular/recent queries matching the input prefix.
    """
    try:
        search_service = SearchService()
        suggestions = await search_service.get_suggestions(request.query, request.size)

        return SuggestResponse(query=request.query, suggestions=suggestions)
    except Exception as e:
        logger.error(f"Suggestion error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Suggestion failed: {str(e)}")


@router.get("/popular")
async def get_popular_queries(
    limit: int = 10, current_user: Annotated[TokenData, Security(get_current_user)] = None
):
    """
    Get popular search queries

    Returns most frequently searched queries for discovery.
    """
    # This would query the search_queries table
    # For now, return empty list (will implement with analytics)
    return {"queries": [], "limit": limit}
