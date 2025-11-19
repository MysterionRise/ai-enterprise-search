"""Document and chunk data models"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    """Extended metadata for documents"""

    author: str | None = None
    created_date: datetime | None = None
    modified_date: datetime | None = None
    file_size: int | None = None
    page_count: int | None = None
    keywords: list[str] = Field(default_factory=list)
    custom_fields: dict[str, Any] = Field(default_factory=dict)


class Document(BaseModel):
    """Main document model representing a searchable document"""

    doc_id: str = Field(..., description="Unique document identifier")
    source: str = Field(..., description="Source system (servicenow, sharepoint, etc.)")
    source_id: str = Field(..., description="ID in the source system")
    title: str = Field(..., description="Document title")
    url: str | None = Field(None, description="URL to access the document")
    body: str = Field(..., description="Full text content")
    content_type: str = Field(..., description="MIME type or file extension")
    language: str = Field(default="en", description="ISO 639-1 language code")

    # Access control
    acl_allow: list[str] = Field(
        default_factory=lambda: ["all-employees"], description="Groups/roles allowed to access"
    )
    acl_deny: list[str] = Field(default_factory=list, description="Groups/roles denied access")

    # Personalization
    country_tags: list[str] = Field(default_factory=list, description="Relevant countries")
    department: str | None = Field(None, description="Relevant department")
    audience: list[str] = Field(default_factory=list, description="Target audience tags")

    # Metadata
    last_modified: datetime = Field(default_factory=datetime.utcnow)
    indexed_at: datetime | None = None
    hash: str | None = Field(None, description="Content hash for deduplication")
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)

    # Tags and categories
    tags: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "doc_id": "kb-12345",
                "source": "servicenow",
                "source_id": "KB0010001",
                "title": "How to Request Time Off",
                "url": "https://company.service-now.com/kb_view.do?sysparm_article=KB0010001",
                "body": "To request time off, navigate to the HR Portal...",
                "content_type": "text/html",
                "language": "en",
                "acl_allow": ["all-employees", "uk-hr"],
                "country_tags": ["UK"],
                "department": "HR",
                "tags": ["time-off", "vacation", "leave"],
            }
        }


class DocumentChunk(BaseModel):
    """A chunk of a document for embedding and retrieval"""

    chunk_id: str = Field(..., description="Unique chunk identifier")
    doc_id: str = Field(..., description="Parent document ID")
    chunk_idx: int = Field(..., description="Chunk sequence number")
    text: str = Field(..., description="Chunk text content")

    # Copy key fields from parent document for filtering
    source: str
    title: str
    url: str | None = None
    language: str = "en"
    content_type: str

    # Access control (inherited from parent)
    acl_allow: list[str] = Field(default_factory=lambda: ["all-employees"])
    acl_deny: list[str] = Field(default_factory=list)

    # Personalization (inherited from parent)
    country_tags: list[str] = Field(default_factory=list)
    department: str | None = None

    # Embedding
    embedding: list[float] | None = Field(None, description="Dense vector embedding")

    # Context
    char_start: int | None = Field(None, description="Character offset in original document")
    char_end: int | None = Field(None, description="Character end offset")

    # Timestamps
    last_modified: datetime = Field(default_factory=datetime.utcnow)
    indexed_at: datetime | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "chunk_id": "kb-12345-0",
                "doc_id": "kb-12345",
                "chunk_idx": 0,
                "text": (
                    "To request time off, navigate to the HR Portal and "
                    "click on 'Request Leave'..."
                ),
                "source": "servicenow",
                "title": "How to Request Time Off",
                "language": "en",
                "acl_allow": ["all-employees", "uk-hr"],
                "country_tags": ["UK"],
            }
        }


class DocumentIngestRequest(BaseModel):
    """Request to ingest a new document"""

    source: str
    source_id: str
    title: str
    url: str | None = None
    content: str
    content_type: str = "text/plain"
    language: str | None = None
    acl_allow: list[str] = Field(default_factory=lambda: ["all-employees"])
    acl_deny: list[str] = Field(default_factory=list)
    country_tags: list[str] = Field(default_factory=list)
    department: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] | None = None


class IngestResponse(BaseModel):
    """Response after document ingestion"""

    doc_id: str
    chunks_created: int
    status: str = "success"
    message: str | None = None


class DocumentSummaryRequest(BaseModel):
    """Request to generate document summary"""

    doc_id: str = Field(..., description="Document ID to summarize")
    summary_type: str = Field(
        default="brief", description="Type of summary: brief, detailed, or key_points"
    )
    max_length: int = Field(
        default=200, ge=50, le=1000, description="Maximum summary length in words"
    )


class DocumentSummary(BaseModel):
    """Generated document summary"""

    doc_id: str
    summary_type: str
    summary: str = Field(..., description="Generated summary text")
    key_points: list[str] | None = Field(None, description="Extracted key points (if applicable)")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    model: str = Field(..., description="LLM model used for generation")
    generation_time_ms: float = Field(
        ..., description="Time taken to generate summary in milliseconds"
    )
