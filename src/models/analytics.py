"""Analytics and activity tracking models"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DocumentView(BaseModel):
    """Record of a document view/access"""

    doc_id: str
    user_id: str
    username: str
    department: Optional[str] = None
    country: Optional[str] = None
    viewed_at: datetime = Field(default_factory=datetime.utcnow)
    dwell_time_ms: Optional[int] = Field(None, description="Time spent viewing (milliseconds)")
    source: str = Field(..., description="How they accessed it (search, recommendation, direct)")


class SearchQuery(BaseModel):
    """Record of a search query"""

    query: str
    user_id: str
    username: str
    department: Optional[str] = None
    country: Optional[str] = None
    results_count: int
    clicked_doc_ids: List[str] = Field(default_factory=list)
    searched_at: datetime = Field(default_factory=datetime.utcnow)
    response_time_ms: float


class ActivityStats(BaseModel):
    """Real-time activity statistics for a document"""

    doc_id: str
    title: str
    views_24h: int = Field(..., description="Views in last 24 hours")
    views_7d: int = Field(..., description="Views in last 7 days")
    unique_viewers_24h: int = Field(..., description="Unique viewers in last 24 hours")
    departments_viewing: List[str] = Field(default_factory=list, description="Departments viewing this")
    trending_score: float = Field(..., description="Calculated trending score")
    is_trending: bool = False


class SearchAnalytics(BaseModel):
    """Search analytics dashboard data"""

    total_searches: int
    total_documents: int
    avg_response_time_ms: float
    top_queries: List[Dict[str, Any]] = Field(default_factory=list)
    zero_result_queries: List[Dict[str, Any]] = Field(default_factory=list)
    search_trends: List[Dict[str, Any]] = Field(default_factory=list, description="Search volume over time")
    popular_documents: List[Dict[str, Any]] = Field(default_factory=list)
    user_engagement: Dict[str, Any] = Field(default_factory=dict)


class TrackViewRequest(BaseModel):
    """Request to track a document view"""

    doc_id: str
    source: str = Field(default="search", description="Source: search, recommendation, direct, etc.")
    dwell_time_ms: Optional[int] = None
