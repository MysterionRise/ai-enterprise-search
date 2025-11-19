"""Document ingestion service"""

import hashlib
import logging
from datetime import datetime

from fastapi import UploadFile

from src.core.config import settings
from src.models.documents import (
    Document,
    DocumentChunk,
    DocumentIngestRequest,
    DocumentMetadata,
    IngestResponse,
)
from src.services.opensearch_service import opensearch_service
from src.utils.document_parser import document_parser
from src.utils.text_processing import chunk_text, clean_text, compute_hash, detect_language

logger = logging.getLogger(__name__)


class IngestService:
    """Service for ingesting documents"""

    def __init__(self):
        self.os_service = opensearch_service
        self.parser = document_parser

    def _get_embedding_service(self):
        """Lazy import of embedding service"""
        from src.services.embedding_service import embedding_service

        return embedding_service

    async def ingest_document(self, request: DocumentIngestRequest) -> IngestResponse:
        """
        Ingest a document from structured request

        Args:
            request: Document ingestion request

        Returns:
            Ingestion response with status
        """
        try:
            # Clean and normalize content
            content = clean_text(request.content)

            # Detect language if not provided
            language = request.language or detect_language(content)

            # Generate document ID
            doc_id = f"{request.source}-{hashlib.md5(request.source_id.encode()).hexdigest()[:8]}"

            # Create document
            document = Document(
                doc_id=doc_id,
                source=request.source,
                source_id=request.source_id,
                title=request.title,
                url=request.url,
                body=content,
                content_type=request.content_type,
                language=language,
                acl_allow=request.acl_allow,
                acl_deny=request.acl_deny,
                country_tags=request.country_tags,
                department=request.department,
                tags=request.tags,
                hash=compute_hash(content),
                indexed_at=datetime.utcnow(),
                metadata=DocumentMetadata(custom_fields=request.metadata or {}),
            )

            # Index document
            await self._index_document(document)

            # Chunk and index chunks
            chunks_created = await self._create_and_index_chunks(document)

            logger.info(f"Ingested document {doc_id} with {chunks_created} chunks")

            return IngestResponse(
                doc_id=doc_id,
                chunks_created=chunks_created,
                status="success",
                message=f"Document indexed with {chunks_created} chunks",
            )

        except Exception as e:
            logger.error(f"Ingestion failed: {e}", exc_info=True)
            return IngestResponse(doc_id="", chunks_created=0, status="error", message=str(e))

    async def ingest_file(
        self,
        file: UploadFile,
        source: str,
        source_id: str,
        acl_allow: list[str],
        country_tags: list[str],
        department: str | None,
    ) -> IngestResponse:
        """
        Ingest a file upload

        Args:
            file: Uploaded file
            source: Source system name
            source_id: Source ID
            acl_allow: ACL allow list
            country_tags: Country tags
            department: Department

        Returns:
            Ingestion response
        """
        try:
            # Read file content
            content_bytes = await file.read()

            # Parse file
            parsed = self.parser.parse_file(content_bytes, file.filename)

            if not parsed["text"]:
                raise ValueError("No text could be extracted from file")

            # Create ingestion request
            request = DocumentIngestRequest(
                source=source,
                source_id=source_id,
                title=file.filename,
                content=parsed["text"],
                content_type=file.content_type or "application/octet-stream",
                acl_allow=acl_allow,
                country_tags=country_tags,
                department=department,
                metadata=parsed["metadata"],
            )

            return await self.ingest_document(request)

        except Exception as e:
            logger.error(f"File ingestion failed: {e}", exc_info=True)
            return IngestResponse(doc_id="", chunks_created=0, status="error", message=str(e))

    async def delete_document(self, doc_id: str):
        """Delete a document and its chunks"""
        self.os_service.delete_document(doc_id)
        logger.info(f"Deleted document {doc_id}")

    async def reindex_document(self, doc_id: str) -> IngestResponse:
        """
        Reindex an existing document

        This is a placeholder - in production, you would:
        1. Fetch the original document from source
        2. Re-process and re-embed
        3. Update the index
        """
        raise NotImplementedError("Reindexing not yet implemented")

    async def _index_document(self, document: Document):
        """Index a single document to OpenSearch"""
        doc_dict = document.model_dump()

        # Remove embedding field if present (not in documents index)
        doc_dict.pop("embedding", None)

        self.os_service.bulk_index_documents([doc_dict])

    async def _create_and_index_chunks(self, document: Document) -> int:
        """
        Create chunks from document and index with embeddings

        Args:
            document: Source document

        Returns:
            Number of chunks created
        """
        # Chunk the document text
        chunks_data = chunk_text(
            document.body,
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP,
            doc_id=document.doc_id,
        )

        if not chunks_data:
            return 0

        # Prepare chunks for embedding
        chunk_texts = [text for _, text, _, _ in chunks_data]

        # Generate embeddings in batch
        logger.info(f"Generating embeddings for {len(chunk_texts)} chunks")
        embedding_service = self._get_embedding_service()
        embeddings = embedding_service.embed_batch(chunk_texts)

        # Create chunk objects
        chunks = []
        for (chunk_idx, text, char_start, char_end), embedding in zip(chunks_data, embeddings):
            chunk = DocumentChunk(
                chunk_id=f"{document.doc_id}-{chunk_idx}",
                doc_id=document.doc_id,
                chunk_idx=chunk_idx,
                text=text,
                source=document.source,
                title=document.title,
                url=document.url,
                language=document.language,
                content_type=document.content_type,
                acl_allow=document.acl_allow,
                acl_deny=document.acl_deny,
                country_tags=document.country_tags,
                department=document.department,
                embedding=embedding,
                char_start=char_start,
                char_end=char_end,
                last_modified=document.last_modified,
                indexed_at=datetime.utcnow(),
            )
            chunks.append(chunk.model_dump())

        # Bulk index chunks
        self.os_service.bulk_index_chunks(chunks)

        return len(chunks)


# Global instance
ingest_service = IngestService()
