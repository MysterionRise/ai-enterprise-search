"""
Pydantic models for Recommendation endpoints
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class RecommendationItem(BaseModel):
    """A single recommendation"""

    doc_id: str
    title: str
    source: str
    score: Optional[float] = None
    reason: str  # "similar_content", "trending", "popular_in_hr", etc.
    view_count: Optional[int] = None
    unique_viewers: Optional[int] = None
    trend_score: Optional[float] = None
    age_hours: Optional[float] = None


class RelatedDocumentsResponse(BaseModel):
    """Response for related documents endpoint"""

    doc_id: str
    related: List[RecommendationItem]
    count: int

    class Config:
        json_schema_extra = {
            "example": {
                "doc_id": "sn-kb001",
                "related": [
                    {
                        "doc_id": "sn-kb002",
                        "title": "Related Document Title",
                        "source": "servicenow",
                        "score": 0.89,
                        "reason": "similar_content",
                    }
                ],
                "count": 5,
            }
        }


class TrendingResponse(BaseModel):
    """Response for trending documents endpoint"""

    trending: List[RecommendationItem]
    time_window_hours: int
    count: int
    last_updated: str

    class Config:
        json_schema_extra = {
            "example": {
                "trending": [
                    {
                        "doc_id": "conf-001",
                        "title": "Q4 2024 Company Strategy",
                        "source": "confluence",
                        "trend_score": 234.5,
                        "view_count": 156,
                        "age_hours": 12,
                        "reason": "trending",
                    }
                ],
                "time_window_hours": 24,
                "count": 10,
                "last_updated": "2025-11-18T10:30:00Z",
            }
        }


class PopularResponse(BaseModel):
    """Response for popular documents endpoint"""

    popular: List[RecommendationItem]
    department: str
    country: Optional[str] = None
    period_days: int
    count: int

    class Config:
        json_schema_extra = {
            "example": {
                "popular": [
                    {
                        "doc_id": "sn-leave-policy",
                        "title": "Annual Leave Policy",
                        "source": "servicenow",
                        "view_count": 245,
                        "unique_viewers": 87,
                        "reason": "popular_in_hr",
                    }
                ],
                "department": "HR",
                "country": "UK",
                "period_days": 30,
                "count": 10,
            }
        }


class PersonalizedRecommendationsResponse(BaseModel):
    """Response for personalized recommendations endpoint"""

    recommendations: List[RecommendationItem]
    personalization_context: dict
    count: int

    class Config:
        json_schema_extra = {
            "example": {
                "recommendations": [
                    {
                        "doc_id": "sn-kb001",
                        "title": "Document Title",
                        "source": "servicenow",
                        "score": 0.87,
                        "reason": "popular_in_hr_uk",
                    }
                ],
                "personalization_context": {
                    "department": "HR",
                    "country": "UK",
                    "username": "john.doe",
                },
                "count": 10,
            }
        }
