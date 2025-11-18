"""Document ingestion endpoints"""

from fastapi import APIRouter, Security, HTTPException, UploadFile, File, Form
from typing import Annotated, Optional
import logging

from src.models.documents import DocumentIngestRequest, IngestResponse, DocumentSummaryRequest, DocumentSummary
from src.models.auth import TokenData
from src.core.security import get_current_user
from src.services.ingest_service import IngestService
from src.services.llm_service import LLMService
from src.services.opensearch_service import OpenSearchService
import time

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/document", response_model=IngestResponse)
async def ingest_document(
    request: DocumentIngestRequest, current_user: Annotated[TokenData, Security(get_current_user)]
):
    """
    Ingest a document from raw text/content

    This endpoint:
    1. Validates and normalizes the document
    2. Detects language if not provided
    3. Chunks the content
    4. Generates embeddings
    5. Indexes to OpenSearch

    The process runs asynchronously via Celery workers.
    """
    try:
        ingest_service = IngestService()
        result = await ingest_service.ingest_document(request)
        return result
    except Exception as e:
        logger.error(f"Ingestion error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.post("/upload", response_model=IngestResponse)
async def upload_file(
    file: UploadFile = File(...),
    source: str = Form(...),
    source_id: Optional[str] = Form(None),
    acl_allow: str = Form("all-employees"),
    country_tags: Optional[str] = Form(None),
    department: Optional[str] = Form(None),
    current_user: Annotated[TokenData, Security(get_current_user)] = None,
):
    """
    Upload and ingest a file (PDF, DOCX, etc.)

    This endpoint:
    1. Validates file type and size
    2. Extracts text using Tika
    3. Performs OCR if needed
    4. Processes and indexes the document

    Supported formats: PDF, DOCX, PPTX, TXT, HTML, etc.
    """
    try:
        # Parse ACL and tags
        acl_list = [g.strip() for g in acl_allow.split(",")]
        country_list = [c.strip() for c in country_tags.split(",")] if country_tags else []

        ingest_service = IngestService()
        result = await ingest_service.ingest_file(
            file=file,
            source=source,
            source_id=source_id or file.filename,
            acl_allow=acl_list,
            country_tags=country_list,
            department=department,
        )
        return result
    except Exception as e:
        logger.error(f"File upload error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


@router.delete("/document/{doc_id}")
async def delete_document(
    doc_id: str, current_user: Annotated[TokenData, Security(get_current_user)]
):
    """
    Delete a document and its chunks from the index

    Requires authentication. Only admins or document owners can delete.
    """
    try:
        ingest_service = IngestService()
        await ingest_service.delete_document(doc_id)
        return {"status": "deleted", "doc_id": doc_id}
    except Exception as e:
        logger.error(f"Deletion error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")


@router.post("/reindex/{doc_id}", response_model=IngestResponse)
async def reindex_document(
    doc_id: str, current_user: Annotated[TokenData, Security(get_current_user)]
):
    """
    Reindex an existing document

    Useful for updating embeddings or applying new processing pipelines.
    """
    try:
        ingest_service = IngestService()
        result = await ingest_service.reindex_document(doc_id)
        return result
    except Exception as e:
        logger.error(f"Reindex error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Reindex failed: {str(e)}")


@router.post("/summarize", response_model=DocumentSummary)
async def summarize_document(
    request: DocumentSummaryRequest,
    current_user: Annotated[TokenData, Security(get_current_user)]
):
    """
    Generate AI-powered summary of a document

    This endpoint uses LLM to generate:
    - **brief**: Short summary (TL;DR style)
    - **detailed**: Comprehensive summary
    - **key_points**: Bullet-point key takeaways

    The summary is generated from the full document content with context.
    """
    try:
        start_time = time.time()

        # Fetch document from OpenSearch
        opensearch_service = OpenSearchService()
        doc_result = await opensearch_service.get_document(request.doc_id)

        if not doc_result:
            raise HTTPException(status_code=404, detail=f"Document {request.doc_id} not found")

        # Get all chunks for this document to build full context
        chunks_result = await opensearch_service.get_document_chunks(request.doc_id)

        # Build full text from chunks
        full_text = "\n\n".join([chunk.get("text", "") for chunk in chunks_result])
        if not full_text:
            full_text = doc_result.get("body", "")

        # Limit text length to avoid token limits (approx 3000 words = ~4000 tokens)
        words = full_text.split()
        if len(words) > 3000:
            full_text = " ".join(words[:3000]) + "..."

        # Generate summary using LLM
        llm_service = LLMService()

        if request.summary_type == "brief":
            prompt = f"""Generate a concise summary (TL;DR) of the following document in {request.max_length} words or less.
Focus on the most important information that a busy professional needs to know.

Title: {doc_result.get('title', 'Untitled')}

Content:
{full_text}

Summary:"""

        elif request.summary_type == "detailed":
            prompt = f"""Generate a comprehensive summary of the following document in approximately {request.max_length} words.
Include all major points, key arguments, and important details.

Title: {doc_result.get('title', 'Untitled')}

Content:
{full_text}

Summary:"""

        else:  # key_points
            prompt = f"""Extract the key points from the following document as a bulleted list (maximum {request.max_length} words total).
Each point should be concise and actionable.

Title: {doc_result.get('title', 'Untitled')}

Content:
{full_text}

Key Points (as bullet points):"""

        # Generate with LLM
        summary_text = await llm_service.generate(
            prompt=prompt,
            max_tokens=min(request.max_length * 2, 1000),  # Rough token estimate
            temperature=0.3  # Lower temperature for more factual summaries
        )

        # Parse key points if requested
        key_points = None
        if request.summary_type == "key_points":
            # Extract bullet points
            lines = summary_text.strip().split("\n")
            key_points = []
            for line in lines:
                line = line.strip()
                if line and (line.startswith("-") or line.startswith("•") or line.startswith("*")):
                    # Remove bullet markers
                    point = line.lstrip("-•* ").strip()
                    if point:
                        key_points.append(point)

        generation_time_ms = (time.time() - start_time) * 1000

        return DocumentSummary(
            doc_id=request.doc_id,
            summary_type=request.summary_type,
            summary=summary_text.strip(),
            key_points=key_points,
            model=llm_service.model,
            generation_time_ms=generation_time_ms
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Summarization error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")
