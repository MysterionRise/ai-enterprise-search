"""
RAG (Retrieval-Augmented Generation) API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from src.models.rag import (
    RAGRequest,
    RAGResponse,
    RAGHealthResponse,
    SourceDocument,
    Citation,
    RAGMetadata,
)
from src.models.auth import User
from src.core.security import get_current_user
from src.services.rag_service import RAGService
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/rag", tags=["RAG"])

# Initialize RAG service (singleton)
rag_service = RAGService()


@router.post("/ask", response_model=RAGResponse)
async def ask_question(request: RAGRequest, current_user: User = Depends(get_current_user)):
    """
    Generate AI answer to question using RAG

    Retrieves relevant documents and uses LLM to generate answer with citations.

    **Process**:
    1. Retrieve relevant document chunks using hybrid search
    2. Build context from top chunks
    3. Generate answer using LLM with context
    4. Extract citations from answer

    **Returns**:
    - answer: Generated answer with citations
    - sources: Documents used to generate answer
    - citations: List of cited documents
    - metadata: Timing and model information
    """
    try:
        logger.info(f"RAG request from user {current_user.username}: {request.query}")

        result = await rag_service.generate_answer(
            query=request.query,
            user=current_user,
            num_chunks=request.num_chunks,
            temperature=request.temperature,
        )

        # Convert to response model
        response = RAGResponse(
            query=result["query"],
            answer=result["answer"],
            sources=[SourceDocument(**src) for src in result["sources"]],
            citations=[Citation(**cit) for cit in result["citations"]],
            metadata=RAGMetadata(**result["metadata"]),
        )

        logger.info(
            f"RAG response generated in {result['metadata']['total_time_ms']:.0f}ms "
            f"with {result['metadata']['chunks_used']} chunks"
        )

        return response

    except Exception as e:
        logger.error(f"RAG generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate answer: {str(e)}")


@router.post("/ask/stream")
async def ask_question_stream(request: RAGRequest, current_user: User = Depends(get_current_user)):
    """
    Stream AI answer generation in real-time (Server-Sent Events)

    Returns a stream of events:
    - **sources**: Retrieved source documents
    - **token**: Each generated token
    - **done**: Generation complete
    - **error**: Error occurred

    **Usage**:
    ```javascript
    const eventSource = new EventSource('/api/v1/rag/ask/stream');
    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'token') {
            console.log(data.token);
        }
    };
    ```
    """

    async def event_generator():
        try:
            logger.info(f"RAG streaming request from user {current_user.username}: {request.query}")

            async for chunk in rag_service.stream_answer(
                query=request.query, user=current_user, num_chunks=request.num_chunks
            ):
                # Format as Server-Sent Event
                yield f"data: {json.dumps(chunk)}\n\n"

            logger.info(f"RAG streaming complete for query: {request.query}")

        except Exception as e:
            logger.error(f"Streaming failed: {e}", exc_info=True)
            error_chunk = {"type": "error", "message": str(e)}
            yield f"data: {json.dumps(error_chunk)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable buffering in nginx
        },
    )


@router.get("/health", response_model=RAGHealthResponse)
async def rag_health():
    """
    Check RAG service health

    Verifies:
    - LLM service is available
    - Model is loaded
    - Service is responding

    **Returns**:
    - status: "healthy", "degraded", or "unhealthy"
    - llm_available: Whether LLM service is reachable
    - provider: LLM provider (ollama, openai, anthropic)
    - model: Current LLM model name
    """
    try:
        llm_healthy = await rag_service.llm_service.health_check()

        status = "healthy" if llm_healthy else "degraded"

        return RAGHealthResponse(
            status=status,
            llm_available=llm_healthy,
            provider=rag_service.llm_service.provider,
            model=rag_service.llm_service.model,
        )

    except Exception as e:
        logger.error(f"RAG health check failed: {e}")
        return RAGHealthResponse(
            status="unhealthy",
            llm_available=False,
            provider=rag_service.llm_service.provider,
            model=rag_service.llm_service.model,
        )


@router.get("/models")
async def get_available_models(current_user: User = Depends(get_current_user)):
    """
    Get list of available LLM models

    Only accessible to authenticated users.

    **Returns**:
    - models: List of available model names
    - current_model: Currently configured model
    - provider: LLM provider
    """
    try:
        models = await rag_service.llm_service.get_available_models()

        return {
            "models": models,
            "current_model": rag_service.llm_service.model,
            "provider": rag_service.llm_service.provider,
        }

    except Exception as e:
        logger.error(f"Failed to get available models: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve available models: {str(e)}"
        )
