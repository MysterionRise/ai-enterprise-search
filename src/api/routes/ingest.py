"""Document ingestion endpoints"""

from fastapi import APIRouter, Security, HTTPException, UploadFile, File, Form
from typing import Annotated, Optional
import logging

from src.models.documents import DocumentIngestRequest, IngestResponse
from src.models.auth import TokenData
from src.core.security import get_current_user
from src.services.ingest_service import IngestService

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
