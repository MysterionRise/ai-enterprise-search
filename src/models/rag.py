"""
Pydantic models for RAG (Retrieval-Augmented Generation) endpoints
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict


class RAGRequest(BaseModel):
    """Request model for RAG question answering"""

    query: str = Field(..., min_length=1, max_length=500, description="Question to answer")
    num_chunks: int = Field(default=5, ge=1, le=10, description="Number of chunks to retrieve")
    temperature: float = Field(
        default=0.3, ge=0.0, le=1.0, description="LLM temperature (0=deterministic, 1=creative)"
    )
    stream: bool = Field(default=False, description="Whether to stream the response")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "What is our remote work policy for UK employees?",
                "num_chunks": 5,
                "temperature": 0.3,
                "stream": False,
            }
        }


class SourceDocument(BaseModel):
    """Source document used to generate RAG answer"""

    doc_id: str
    chunk_id: Optional[str] = None
    title: str
    snippet: str
    score: float
    source: str


class Citation(BaseModel):
    """Citation linking answer to source document"""

    doc_id: str
    title: str
    reference: str  # e.g., "Document 1"


class RAGMetadata(BaseModel):
    """Metadata about RAG generation process"""

    retrieval_time_ms: float
    generation_time_ms: float
    total_time_ms: float
    chunks_used: int
    model: str
    temperature: float


class RAGResponse(BaseModel):
    """Response model for RAG question answering"""

    query: str
    answer: str
    sources: List[SourceDocument]
    citations: List[Citation] = []
    metadata: RAGMetadata

    class Config:
        json_schema_extra = {
            "example": {
                "query": "What is our remote work policy for UK employees?",
                "answer": "UK employees can work from home up to 3 days per week with manager approval. [Document 1]",
                "sources": [
                    {
                        "doc_id": "sn-kb001",
                        "chunk_id": "sn-kb001-0",
                        "title": "Remote Work Policy - UK",
                        "snippet": "UK employees are allowed to work remotely...",
                        "score": 0.95,
                        "source": "servicenow",
                    }
                ],
                "citations": [
                    {
                        "doc_id": "sn-kb001",
                        "title": "Remote Work Policy - UK",
                        "reference": "Document 1",
                    }
                ],
                "metadata": {
                    "retrieval_time_ms": 98.5,
                    "generation_time_ms": 2847.3,
                    "total_time_ms": 2945.8,
                    "chunks_used": 5,
                    "model": "llama3.1:8b-instruct-q4_0",
                    "temperature": 0.3,
                },
            }
        }


class RAGStreamChunk(BaseModel):
    """Streaming chunk for RAG response"""

    type: str  # "sources", "token", "done", "error"
    sources: Optional[List[SourceDocument]] = None
    token: Optional[str] = None
    message: Optional[str] = None


class RAGHealthResponse(BaseModel):
    """Health check response for RAG service"""

    status: str  # "healthy", "degraded", "unhealthy"
    llm_available: bool
    provider: str
    model: str
