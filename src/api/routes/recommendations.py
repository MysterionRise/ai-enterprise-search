"""
Recommendation API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from src.models.recommendations import (
    RelatedDocumentsResponse,
    TrendingResponse,
    PopularResponse,
    PersonalizedRecommendationsResponse,
    RecommendationItem,
)
from src.models.auth import User
from src.core.security import get_current_user
from src.services.recommendation_service import RecommendationService
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/recommendations", tags=["Recommendations"])

# Initialize recommendation service (singleton)
recommendation_service = RecommendationService()


@router.get("/related/{doc_id}", response_model=RelatedDocumentsResponse)
async def get_related_documents(
    doc_id: str,
    limit: int = Query(default=5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
):
    """
    Get documents similar to the given document (content-based filtering)

    Uses vector similarity on document embeddings to find related content.
    Results are ACL-filtered and personalized based on user context.

    **Args**:
    - doc_id: ID of the document to find similar documents for
    - limit: Maximum number of recommendations (1-20)

    **Returns**:
    - List of similar documents with similarity scores
    - Reason: "similar_content"
    """
    try:
        logger.info(f"Getting related documents for {doc_id}, user: {current_user.username}")

        related = await recommendation_service.get_related_documents(
            doc_id=doc_id, user=current_user, limit=limit
        )

        return RelatedDocumentsResponse(
            doc_id=doc_id,
            related=[RecommendationItem(**item) for item in related],
            count=len(related),
        )

    except Exception as e:
        logger.error(f"Failed to get related documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get related documents: {str(e)}")


@router.get("/trending", response_model=TrendingResponse)
async def get_trending_documents(
    hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
):
    """
    Get trending documents across organization

    Trending score formula:
    score = (view_count / age_hours^0.8) * (1 + avg_dwell_time/60000)

    **Args**:
    - hours: Time window for trending calculation (1-168 hours / 1 week)
    - limit: Maximum number of results (1-50)

    **Returns**:
    - List of trending documents with trend scores
    - Reason: "trending"

    **Note**: Currently uses mock data. In production, queries analytics tables.
    """
    try:
        logger.info(f"Getting trending documents for last {hours}h, user: {current_user.username}")

        trending = await recommendation_service.get_trending(
            hours=hours, limit=limit, user=current_user
        )

        return TrendingResponse(
            trending=[RecommendationItem(**item) for item in trending],
            time_window_hours=hours,
            count=len(trending),
            last_updated=datetime.utcnow().isoformat() + "Z",
        )

    except Exception as e:
        logger.error(f"Failed to get trending documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get trending documents: {str(e)}")


@router.get("/popular", response_model=PopularResponse)
async def get_popular_documents(
    department: str = Query(None),
    country: str = Query(None),
    days: int = Query(default=30, ge=1, le=90),
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
):
    """
    Get most popular documents in a department/country

    Collaborative filtering: "People in your department are viewing..."

    **Args**:
    - department: Department filter (defaults to user's department)
    - country: Optional country filter (defaults to user's country)
    - days: Time window in days (1-90)
    - limit: Maximum number of results (1-50)

    **Returns**:
    - List of popular documents with view counts
    - Reason: "popular_in_{department}"

    **Note**: Currently uses mock data. In production, queries analytics tables.
    """
    try:
        # Use current user's context if not specified
        dept = department or current_user.department or "HR"
        ctry = country or current_user.country

        logger.info(f"Getting popular documents for {dept}/{ctry}, user: {current_user.username}")

        popular = await recommendation_service.get_popular_in_department(
            department=dept, country=ctry, days=days, limit=limit
        )

        return PopularResponse(
            popular=[RecommendationItem(**item) for item in popular],
            department=dept,
            country=ctry,
            period_days=days,
            count=len(popular),
        )

    except Exception as e:
        logger.error(f"Failed to get popular documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get popular documents: {str(e)}")


@router.get("/for-you", response_model=PersonalizedRecommendationsResponse)
async def get_personalized_recommendations(
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
):
    """
    Get personalized recommendations for current user

    Combines multiple recommendation strategies:
    - 40% Popular in your department
    - 40% Trending content
    - 20% Similar to your recent views (future)

    **Args**:
    - limit: Maximum number of recommendations (1-50)

    **Returns**:
    - Mixed list of personalized recommendations
    - Personalization context (dept, country, username)
    - Various reasons based on recommendation type

    **Use case**: Homepage "For You" section
    """
    try:
        logger.info(f"Getting personalized recommendations for user: {current_user.username}")

        recommendations = await recommendation_service.get_personalized_recommendations(
            user=current_user, limit=limit
        )

        return PersonalizedRecommendationsResponse(
            recommendations=[RecommendationItem(**item) for item in recommendations],
            personalization_context={
                "department": current_user.department,
                "country": current_user.country,
                "username": current_user.username,
            },
            count=len(recommendations),
        )

    except Exception as e:
        logger.error(f"Failed to get personalized recommendations: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get personalized recommendations: {str(e)}",
        )
