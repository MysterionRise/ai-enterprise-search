"""Search request and response models"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SearchFilters(BaseModel):
    """Filters for search queries"""

    sources: list[str] | None = Field(None, description="Filter by source systems")
    languages: list[str] | None = Field(None, description="Filter by language codes")
    countries: list[str] | None = Field(None, description="Filter by country tags")
    departments: list[str] | None = Field(None, description="Filter by departments")
    content_types: list[str] | None = Field(None, description="Filter by content types")
    tags: list[str] | None = Field(None, description="Filter by tags")
    date_from: datetime | None = Field(None, description="Filter documents modified after")
    date_to: datetime | None = Field(None, description="Filter documents modified before")


class SearchRequest(BaseModel):
    """Search request with query and options"""

    query: str = Field(..., min_length=1, description="Search query text")
    filters: SearchFilters | None = Field(None, description="Search filters")
    size: int = Field(default=10, ge=1, le=100, description="Number of results to return")
    offset: int = Field(default=0, ge=0, description="Pagination offset")

    # Search mode
    use_hybrid: bool = Field(default=True, description="Use hybrid BM25 + vector search")
    use_rerank: bool = Field(default=False, description="Use cross-encoder reranking")

    # Personalization (auto-populated from user context)
    user_country: str | None = None
    user_department: str | None = None
    user_groups: list[str] = Field(default_factory=list)

    # Boosting
    boost_recency: bool = Field(default=True, description="Boost recent documents")
    boost_personalization: bool = Field(default=True, description="Boost user-relevant docs")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "how to request time off",
                "filters": {"sources": ["servicenow"], "countries": ["UK"]},
                "size": 10,
                "use_hybrid": True,
            }
        }


class SearchResult(BaseModel):
    """A single search result"""

    doc_id: str
    chunk_id: str | None = None
    source: str
    title: str
    url: str | None = None
    snippet: str = Field(..., description="Highlighted text snippet")
    score: float = Field(..., description="Relevance score")

    # Display fields
    content_type: str
    language: str
    last_modified: datetime | None = None

    # Personalization signals
    country_tags: list[str] = Field(default_factory=list)
    department: str | None = None

    # Highlighting
    highlights: dict[str, list[str]] = Field(
        default_factory=dict, description="Highlighted field matches"
    )

    # Metadata badges
    is_official: bool = Field(default=False, description="Marked as official/verified")
    is_pinned: bool = Field(default=False, description="Pinned to top for this query")

    class Config:
        json_schema_extra = {
            "example": {
                "doc_id": "kb-12345",
                "source": "servicenow",
                "title": "How to Request Time Off",
                "url": "https://company.service-now.com/kb_view.do?sysparm_article=KB0010001",
                "snippet": "To request time off, navigate to the HR Portal...",
                "score": 0.95,
                "content_type": "text/html",
                "language": "en",
                "country_tags": ["UK"],
                "is_official": True,
            }
        }


class Facet(BaseModel):
    """Facet for result filtering"""

    name: str
    value: str
    count: int


class FacetGroup(BaseModel):
    """Group of facets for a field"""

    field: str
    facets: list[Facet]


class SearchResponse(BaseModel):
    """Search response with results and metadata"""

    query: str
    results: list[SearchResult]
    total: int = Field(..., description="Total number of matching documents")
    took_ms: int = Field(..., description="Query execution time in milliseconds")

    # Facets for filtering
    facets: list[FacetGroup] = Field(default_factory=list)

    # Applied filters (for display)
    applied_filters: dict[str, list[str]] = Field(default_factory=dict)

    # Personalization info
    personalized: bool = Field(default=False, description="Results were personalized")
    personalization_context: dict[str, Any] | None = None

    # Suggestions
    suggestions: list[str] = Field(default_factory=list, description="Query suggestions")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "time off request",
                "results": [],
                "total": 42,
                "took_ms": 127,
                "personalized": True,
                "personalization_context": {"country": "UK", "department": "HR"},
            }
        }


class SuggestRequest(BaseModel):
    """Autocomplete suggestion request"""

    query: str = Field(..., min_length=1, description="Partial query text")
    size: int = Field(default=5, ge=1, le=20, description="Number of suggestions")


class SuggestResponse(BaseModel):
    """Autocomplete suggestions"""

    query: str
    suggestions: list[str]
