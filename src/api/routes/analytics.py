"""Analytics and activity tracking endpoints"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Annotated
import logging
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import random

from src.models.analytics import (
    TrackViewRequest,
    ActivityStats,
    SearchAnalytics,
)
from src.models.auth import User
from src.core.security import get_current_user

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])
logger = logging.getLogger(__name__)

# In-memory storage for demo (in production, use PostgreSQL/Redis)
document_views = []  # List of DocumentView objects
search_queries = []  # List of SearchQuery objects


@router.post("/track/view")
async def track_document_view(
    request: TrackViewRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Track when a user views a document

    This helps build:
    - "5 people from Engineering viewed this today"
    - Trending documents
    - Popular documents by department
    - User engagement metrics
    """
    try:
        # In production, save to PostgreSQL analytics table
        from src.models.analytics import DocumentView

        view = DocumentView(
            doc_id=request.doc_id,
            user_id=current_user.username,
            username=current_user.username,
            department=current_user.department,
            country=current_user.country,
            dwell_time_ms=request.dwell_time_ms,
            source=request.source
        )

        document_views.append(view.model_dump())
        logger.info(f"Tracked view: {current_user.username} viewed {request.doc_id}")

        return {"status": "tracked", "doc_id": request.doc_id}

    except Exception as e:
        logger.error(f"Failed to track view: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/activity/{doc_id}", response_model=ActivityStats)
async def get_document_activity(
    doc_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get real-time activity stats for a document

    Returns:
    - Views in last 24h and 7d
    - Unique viewers count
    - Departments viewing
    - Trending score
    """
    try:
        # For demo, generate mock data with some randomness
        # In production, query from analytics tables

        now = datetime.utcnow()
        views_24h = random.randint(5, 50)
        views_7d = views_24h + random.randint(20, 100)
        unique_viewers = random.randint(3, views_24h)

        departments = ["HR", "Engineering", "Sales", "IT", "Finance", "Marketing"]
        active_depts = random.sample(departments, k=random.randint(1, 3))

        # Calculate trending score (simplified)
        trending_score = views_24h * 1.5 + (unique_viewers * 2.0)
        is_trending = trending_score > 30

        return ActivityStats(
            doc_id=doc_id,
            title="Document Title",  # In production, fetch from OpenSearch
            views_24h=views_24h,
            views_7d=views_7d,
            unique_viewers_24h=unique_viewers,
            departments_viewing=active_depts,
            trending_score=trending_score,
            is_trending=is_trending
        )

    except Exception as e:
        logger.error(f"Failed to get activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard", response_model=SearchAnalytics)
async def get_search_analytics(
    days: int = Query(default=7, ge=1, le=90, description="Days of analytics data"),
    current_user: User = Depends(get_current_user)
):
    """
    Get search analytics dashboard data

    **Includes**:
    - Total searches and documents
    - Average response time
    - Top search queries
    - Zero-result queries
    - Search trends over time
    - Popular documents
    - User engagement metrics

    **Use case**: Analytics dashboard for admins/power users
    """
    try:
        # For demo, return mock data
        # In production, aggregate from analytics tables

        # Mock top queries
        top_queries = [
            {"query": "remote work policy", "count": 145, "avg_ctr": 0.82},
            {"query": "vacation time", "count": 98, "avg_ctr": 0.91},
            {"query": "expense reimbursement", "count": 76, "avg_ctr": 0.78},
            {"query": "kubernetes setup", "count": 64, "avg_ctr": 0.55},
            {"query": "benefits enrollment", "count": 52, "avg_ctr": 0.88},
        ]

        # Mock zero-result queries (opportunities!)
        zero_result_queries = [
            {"query": "pet insurance coverage", "count": 12, "last_searched": "2025-11-17T10:23:00Z"},
            {"query": "remote work reimbursement", "count": 8, "last_searched": "2025-11-17T14:15:00Z"},
            {"query": "career development program", "count": 6, "last_searched": "2025-11-16T09:30:00Z"},
        ]

        # Mock search trends (last N days)
        search_trends = []
        for i in range(days):
            date = (datetime.utcnow() - timedelta(days=days-i-1)).strftime("%Y-%m-%d")
            search_trends.append({
                "date": date,
                "searches": random.randint(50, 200),
                "unique_users": random.randint(20, 80)
            })

        # Mock popular documents
        popular_documents = [
            {"doc_id": "kb-001", "title": "Remote Work Policy 2024", "views": 456, "dept": "HR"},
            {"doc_id": "kb-002", "title": "Time Off Request Guide", "views": 342, "dept": "HR"},
            {"doc_id": "kb-003", "title": "Kubernetes Deployment Guide", "views": 234, "dept": "Engineering"},
            {"doc_id": "kb-004", "title": "Expense Report Process", "views": 198, "dept": "Finance"},
            {"doc_id": "kb-005", "title": "Benefits Overview 2024", "views": 187, "dept": "HR"},
        ]

        user_engagement = {
            "avg_searches_per_user": 12.3,
            "avg_dwell_time_ms": 45000,
            "bounce_rate": 0.23,
            "click_through_rate": 0.78
        }

        return SearchAnalytics(
            total_searches=len(search_queries) or 1234,
            total_documents=10543,
            avg_response_time_ms=42.5,
            top_queries=top_queries,
            zero_result_queries=zero_result_queries,
            search_trends=search_trends,
            popular_documents=popular_documents,
            user_engagement=user_engagement
        )

    except Exception as e:
        logger.error(f"Failed to get analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trending-badges")
async def get_trending_badges(
    doc_ids: str = Query(..., description="Comma-separated document IDs"),
    current_user: User = Depends(get_current_user)
):
    """
    Get trending/activity badges for multiple documents

    Returns badges like:
    - "🔥 Trending in Engineering"
    - "👥 15 people viewed today"
    - "⭐ Popular in your department"

    **Use case**: Enrich search results with social proof
    """
    try:
        doc_id_list = [d.strip() for d in doc_ids.split(",")]
        badges = {}

        for doc_id in doc_id_list:
            doc_badges = []

            # Randomly assign badges for demo
            if random.random() > 0.6:
                views = random.randint(5, 30)
                doc_badges.append(f"👥 {views} people viewed today")

            if random.random() > 0.7:
                doc_badges.append("🔥 Trending in " + random.choice(["Engineering", "HR", "Sales", "IT"]))

            if random.random() > 0.8 and current_user.department:
                doc_badges.append(f"⭐ Popular in {current_user.department}")

            if random.random() > 0.85:
                doc_badges.append("✨ Recently updated")

            badges[doc_id] = doc_badges

        return {"badges": badges}

    except Exception as e:
        logger.error(f"Failed to get badges: {e}")
        raise HTTPException(status_code=500, detail=str(e))
