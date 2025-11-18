# VP Demo - Tactical Implementation Guide

**Companion to**: VP_DEMO_ROADMAP.md
**Purpose**: Detailed technical implementation steps with code examples
**Target Audience**: Development team

---

## Quick Start: Priority Order

Based on impact vs effort, implement in this order:

1. **RAG/LLM Integration** (3-5 days, HIGH impact) - The "WOW" factor
2. **Basic Recommendations** (2-3 days, HIGH impact) - Showcase personalization
3. **Analytics Tracking** (1-2 days, MEDIUM impact) - Enable learning
4. **Celery Workers** (1 day, MEDIUM impact) - Show scalability
5. **UI Polish** (2-3 days, MEDIUM impact) - Professional demo

**Total**: 9-14 days of focused development

---

## Phase 1: RAG/LLM Integration (Days 1-5)

### Day 1: LLM Service Setup

#### Option A: Ollama (Recommended for Demo)

**1. Install Ollama on host machine**
```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama service
ollama serve
```

**2. Pull recommended model**
```bash
# For RAG, we want: good reasoning, 8K+ context, fast inference
ollama pull llama3.1:8b-instruct-q4_0  # 4.7GB, fast, good quality

# Alternative models:
# ollama pull qwen2.5:7b-instruct  # Better for code/structured output
# ollama pull mistral:7b-instruct  # More creative
```

**3. Test Ollama**
```bash
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.1:8b-instruct-q4_0",
  "prompt": "What is enterprise search?",
  "stream": false
}'
```

**4. Create LLM service wrapper**

Create `src/services/llm_service.py`:

```python
"""
LLM Service for RAG answer generation
Supports: Ollama (local), OpenAI, Anthropic
"""
import httpx
import os
from typing import Optional, Dict, AsyncGenerator
from src.core.config import settings

class LLMService:
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "ollama")  # ollama, openai, anthropic
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("LLM_MODEL", "llama3.1:8b-instruct-q4_0")
        self.timeout = httpx.Timeout(60.0)  # LLM can be slow

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        stream: bool = False
    ) -> str:
        """Generate response from LLM"""
        if self.provider == "ollama":
            return await self._generate_ollama(prompt, max_tokens, temperature, stream)
        elif self.provider == "openai":
            return await self._generate_openai(prompt, max_tokens, temperature, stream)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    async def _generate_ollama(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        stream: bool
    ) -> str:
        """Generate using Ollama"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": stream,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature,
                        "top_p": 0.9,
                    }
                }
            )
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")

    async def stream_generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """Stream response from LLM token by token"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": True,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature,
                    }
                }
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        import json
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]

    async def _generate_openai(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        stream: bool
    ) -> str:
        """Generate using OpenAI API (future implementation)"""
        # TODO: Implement OpenAI integration
        raise NotImplementedError("OpenAI provider not yet implemented")

    async def health_check(self) -> bool:
        """Check if LLM service is available"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False
```

**5. Update docker-compose.yml to expose Ollama**

```yaml
# Add to docker-compose.yml
services:
  # ... existing services ...

  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    networks:
      - app-network
    # Optionally add GPU support:
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: 1
    #           capabilities: [gpu]

volumes:
  # ... existing volumes ...
  ollama_data:
```

**6. Update .env with LLM settings**

```bash
# Add to .env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://ollama:11434
LLM_MODEL=llama3.1:8b-instruct-q4_0
```

### Day 2: RAG Service Implementation

**Create `src/services/rag_service.py`:**

```python
"""
Retrieval-Augmented Generation Service
Combines search results with LLM to generate answers
"""
from typing import List, Dict, Optional
from src.services.search_service import SearchService
from src.services.llm_service import LLMService
from src.models.search import SearchRequest
from src.models.auth import User
import logging

logger = logging.getLogger(__name__)


class RAGService:
    def __init__(self):
        self.search_service = SearchService()
        self.llm_service = LLMService()
        self.max_context_tokens = 6000  # Leave room for prompt + answer

    async def generate_answer(
        self,
        query: str,
        user: User,
        num_chunks: int = 5,
        temperature: float = 0.3  # Lower for factual answers
    ) -> Dict:
        """
        Generate answer to query using RAG pipeline

        Returns:
            {
                "query": str,
                "answer": str,
                "sources": List[Dict],  # Source chunks used
                "metadata": Dict  # Timing, model info, etc
            }
        """
        import time
        start_time = time.time()

        # Step 1: Retrieve relevant chunks
        search_request = SearchRequest(
            query=query,
            size=num_chunks,
            use_hybrid=True,
            use_rerank=False,
            boost_personalization=True
        )

        search_results = await self.search_service.search(search_request, user)

        if not search_results["results"]:
            return {
                "query": query,
                "answer": "I couldn't find any relevant documents to answer your question.",
                "sources": [],
                "metadata": {
                    "retrieval_time_ms": (time.time() - start_time) * 1000,
                    "generation_time_ms": 0,
                    "chunks_used": 0
                }
            }

        retrieval_time = time.time()

        # Step 2: Build context from top chunks
        context_chunks = search_results["results"][:num_chunks]
        context = self._build_context(context_chunks)

        # Step 3: Build prompt
        prompt = self._build_prompt(
            query=query,
            context=context,
            user_context={
                "username": user.username,
                "department": user.department,
                "country": user.country
            }
        )

        # Step 4: Generate answer
        answer = await self.llm_service.generate(
            prompt=prompt,
            max_tokens=500,
            temperature=temperature
        )

        generation_time = time.time()

        # Step 5: Extract citations (simple version)
        citations = self._extract_citations(answer, context_chunks)

        return {
            "query": query,
            "answer": answer.strip(),
            "sources": [
                {
                    "doc_id": chunk["doc_id"],
                    "chunk_id": chunk.get("chunk_id"),
                    "title": chunk["title"],
                    "snippet": chunk.get("snippet", chunk.get("text", ""))[:200],
                    "score": chunk["score"],
                    "source": chunk["source"]
                }
                for chunk in context_chunks
            ],
            "citations": citations,
            "metadata": {
                "retrieval_time_ms": (retrieval_time - start_time) * 1000,
                "generation_time_ms": (generation_time - retrieval_time) * 1000,
                "total_time_ms": (generation_time - start_time) * 1000,
                "chunks_used": len(context_chunks),
                "model": self.llm_service.model,
                "temperature": temperature
            }
        }

    def _build_context(self, chunks: List[Dict]) -> str:
        """Build context string from retrieved chunks"""
        context_parts = []

        for i, chunk in enumerate(chunks, 1):
            title = chunk.get("title", "Unknown")
            text = chunk.get("snippet", chunk.get("text", ""))
            source = chunk.get("source", "unknown")

            context_parts.append(
                f"[Document {i}: {title} (Source: {source})]\n{text}\n"
            )

        return "\n".join(context_parts)

    def _build_prompt(self, query: str, context: str, user_context: Dict) -> str:
        """Build prompt for LLM with retrieved context"""

        # System instructions
        system = """You are an AI assistant helping employees find information from company documents.
Your role is to provide accurate, helpful answers based ONLY on the provided documents.

Key Guidelines:
1. Answer based ONLY on the provided documents - do not use external knowledge
2. If the documents don't contain enough information, say so clearly
3. Cite sources using [Document N] notation
4. Be concise but comprehensive
5. If asked about policies, quote relevant sections directly
6. Tailor your response to the user's department and location when relevant"""

        # User context
        user_info = f"""
User Context:
- Name: {user_context.get('username', 'User')}
- Department: {user_context.get('department', 'Unknown')}
- Location: {user_context.get('country', 'Unknown')}
"""

        # Build full prompt
        prompt = f"""{system}

{user_info}

Question: {query}

Relevant Documents:
{context}

Please provide a helpful answer to the question based on the documents above. Remember to cite sources using [Document N] notation.

Answer:"""

        return prompt

    def _extract_citations(self, answer: str, chunks: List[Dict]) -> List[Dict]:
        """Extract which documents were cited in the answer"""
        citations = []

        # Look for [Document N] patterns in answer
        import re
        doc_references = re.findall(r'\[Document (\d+)\]', answer)

        for ref in doc_references:
            doc_num = int(ref) - 1  # Convert to 0-indexed
            if 0 <= doc_num < len(chunks):
                chunk = chunks[doc_num]
                citations.append({
                    "doc_id": chunk["doc_id"],
                    "title": chunk["title"],
                    "reference": f"Document {ref}"
                })

        return citations

    async def stream_answer(self, query: str, user: User, num_chunks: int = 5):
        """Stream answer generation (for real-time UI updates)"""
        # First, retrieve chunks
        search_request = SearchRequest(
            query=query,
            size=num_chunks,
            use_hybrid=True,
            boost_personalization=True
        )

        search_results = await self.search_service.search(search_request, user)

        if not search_results["results"]:
            yield {
                "type": "error",
                "message": "No relevant documents found"
            }
            return

        # Send sources first
        yield {
            "type": "sources",
            "sources": search_results["results"][:num_chunks]
        }

        # Build prompt
        context_chunks = search_results["results"][:num_chunks]
        context = self._build_context(context_chunks)
        prompt = self._build_prompt(
            query=query,
            context=context,
            user_context={
                "username": user.username,
                "department": user.department,
                "country": user.country
            }
        )

        # Stream answer tokens
        async for token in self.llm_service.stream_generate(prompt):
            yield {
                "type": "token",
                "token": token
            }

        # Send completion
        yield {
            "type": "done"
        }
```

**Create RAG models in `src/models/rag.py`:**

```python
"""
Pydantic models for RAG endpoints
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict


class RAGRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    num_chunks: int = Field(default=5, ge=1, le=10)
    temperature: float = Field(default=0.3, ge=0.0, le=1.0)
    stream: bool = Field(default=False)


class SourceDocument(BaseModel):
    doc_id: str
    chunk_id: Optional[str] = None
    title: str
    snippet: str
    score: float
    source: str


class Citation(BaseModel):
    doc_id: str
    title: str
    reference: str  # e.g., "Document 1"


class RAGResponse(BaseModel):
    query: str
    answer: str
    sources: List[SourceDocument]
    citations: List[Citation] = []
    metadata: Dict


class RAGStreamChunk(BaseModel):
    type: str  # "sources", "token", "done", "error"
    sources: Optional[List[SourceDocument]] = None
    token: Optional[str] = None
    message: Optional[str] = None
```

### Day 3: RAG API Endpoints

**Create `src/api/routes/rag.py`:**

```python
"""
RAG (Retrieval-Augmented Generation) API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from src.models.rag import RAGRequest, RAGResponse
from src.models.auth import User
from src.core.security import get_current_user
from src.services.rag_service import RAGService
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/rag", tags=["RAG"])

rag_service = RAGService()


@router.post("/ask", response_model=RAGResponse)
async def ask_question(
    request: RAGRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Generate AI answer to question using RAG

    Retrieves relevant documents and uses LLM to generate answer with citations
    """
    try:
        result = await rag_service.generate_answer(
            query=request.query,
            user=current_user,
            num_chunks=request.num_chunks,
            temperature=request.temperature
        )

        return RAGResponse(**result)

    except Exception as e:
        logger.error(f"RAG generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate answer: {str(e)}")


@router.post("/ask/stream")
async def ask_question_stream(
    request: RAGRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Stream AI answer generation in real-time (SSE)

    Returns Server-Sent Events with:
    - sources: Retrieved source documents
    - token: Each generated token
    - done: Generation complete
    """
    async def event_generator():
        try:
            async for chunk in rag_service.stream_answer(
                query=request.query,
                user=current_user,
                num_chunks=request.num_chunks
            ):
                # Format as SSE
                yield f"data: {json.dumps(chunk)}\n\n"

        except Exception as e:
            logger.error(f"Streaming failed: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


@router.get("/health")
async def rag_health():
    """Check RAG service health (LLM availability)"""
    llm_healthy = await rag_service.llm_service.health_check()

    return {
        "status": "healthy" if llm_healthy else "degraded",
        "llm_available": llm_healthy,
        "provider": rag_service.llm_service.provider,
        "model": rag_service.llm_service.model
    }
```

**Register RAG routes in `src/api/main.py`:**

```python
# Add to src/api/main.py

from src.api.routes import auth, search, ingest, health, rag  # Add rag

# ... existing code ...

# Register routers
app.include_router(auth.router)
app.include_router(search.router)
app.include_router(ingest.router)
app.include_router(health.router)
app.include_router(rag.router)  # Add this line
```

### Day 4: RAG Frontend UI

**Add RAG UI to `ui/templates/index.html`:**

```html
<!-- Add after search results section -->

<!-- RAG Answer Section -->
<div id="rag-section" style="display: none; margin-top: 20px;">
    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 4px solid #007bff;">
        <div style="display: flex; align-items: center; margin-bottom: 10px;">
            <span style="font-size: 24px; margin-right: 10px;">🤖</span>
            <h3 style="margin: 0;">AI-Generated Answer</h3>
        </div>

        <div id="rag-loading" style="display: none;">
            <div class="spinner"></div>
            <span>Generating answer...</span>
        </div>

        <div id="rag-answer" style="font-size: 16px; line-height: 1.6; margin: 15px 0;"></div>

        <div id="rag-sources" style="margin-top: 15px;">
            <strong>Sources:</strong>
            <ul id="rag-sources-list" style="margin-top: 5px;"></ul>
        </div>

        <div id="rag-feedback" style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #dee2e6;">
            <span style="margin-right: 10px;">Was this answer helpful?</span>
            <button onclick="ragFeedback(1)" style="margin-right: 10px;">👍 Helpful</button>
            <button onclick="ragFeedback(-1)">👎 Not Helpful</button>
        </div>
    </div>
</div>

<script>
// Add to existing JavaScript

let currentRAGResponse = null;

// Add "Ask AI" button to search function
function performSearch() {
    const query = document.getElementById('search-query').value.trim();
    if (!query) return;

    // ... existing search code ...

    // Add RAG button after search results
    setTimeout(() => {
        if (document.querySelectorAll('.result-item').length > 0) {
            showAskAIButton(query);
        }
    }, 500);
}

function showAskAIButton(query) {
    const resultsDiv = document.getElementById('results');

    // Check if button already exists
    if (document.getElementById('ask-ai-btn')) return;

    const button = document.createElement('button');
    button.id = 'ask-ai-btn';
    button.innerHTML = '🤖 Ask AI to answer this question';
    button.style.cssText = `
        width: 100%;
        padding: 15px;
        margin: 20px 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        font-size: 16px;
        font-weight: bold;
        cursor: pointer;
        transition: transform 0.2s;
    `;
    button.onmouseover = () => button.style.transform = 'scale(1.02)';
    button.onmouseout = () => button.style.transform = 'scale(1)';
    button.onclick = () => askAI(query);

    resultsDiv.insertBefore(button, resultsDiv.firstChild);
}

async function askAI(query) {
    const ragSection = document.getElementById('rag-section');
    const ragLoading = document.getElementById('rag-loading');
    const ragAnswer = document.getElementById('rag-answer');
    const ragSourcesList = document.getElementById('rag-sources-list');

    // Show section and loading
    ragSection.style.display = 'block';
    ragLoading.style.display = 'block';
    ragAnswer.innerHTML = '';
    ragSourcesList.innerHTML = '';

    // Scroll to RAG section
    ragSection.scrollIntoView({ behavior: 'smooth' });

    try {
        const token = localStorage.getItem('token');
        const response = await fetch('/api/v1/rag/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                query: query,
                num_chunks: 5,
                temperature: 0.3
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        currentRAGResponse = data;

        // Hide loading
        ragLoading.style.display = 'none';

        // Display answer
        ragAnswer.innerHTML = formatAnswer(data.answer, data.citations);

        // Display sources
        data.sources.forEach((source, idx) => {
            const li = document.createElement('li');
            li.innerHTML = `
                <a href="${source.url || '#'}" target="_blank" style="color: #007bff;">
                    [${idx + 1}] ${source.title}
                </a>
                <span style="color: #6c757d; margin-left: 10px;">
                    (${source.source}, Score: ${source.score.toFixed(2)})
                </span>
            `;
            ragSourcesList.appendChild(li);
        });

        // Show timing
        const timing = document.createElement('div');
        timing.style.cssText = 'margin-top: 10px; color: #6c757d; font-size: 14px;';
        timing.innerHTML = `
            ⏱️ Retrieved in ${data.metadata.retrieval_time_ms.toFixed(0)}ms,
            Generated in ${data.metadata.generation_time_ms.toFixed(0)}ms
            (Total: ${data.metadata.total_time_ms.toFixed(0)}ms)
        `;
        ragAnswer.appendChild(timing);

    } catch (error) {
        console.error('RAG failed:', error);
        ragLoading.style.display = 'none';
        ragAnswer.innerHTML = `
            <div style="color: #dc3545;">
                ❌ Failed to generate answer. Please try again.
            </div>
        `;
    }
}

function formatAnswer(answer, citations) {
    // Replace [Document N] with superscript links
    let formatted = answer.replace(
        /\[Document (\d+)\]/g,
        '<sup><a href="#source-$1" style="color: #007bff;">[$1]</a></sup>'
    );

    return formatted;
}

function ragFeedback(score) {
    console.log('RAG feedback:', score);
    // TODO: Send feedback to analytics endpoint

    const feedbackDiv = document.getElementById('rag-feedback');
    feedbackDiv.innerHTML = `
        <span style="color: #28a745;">✓ Thank you for your feedback!</span>
    `;
}
</script>

<style>
.spinner {
    border: 3px solid #f3f3f3;
    border-top: 3px solid #007bff;
    border-radius: 50%;
    width: 20px;
    height: 20px;
    animation: spin 1s linear infinite;
    display: inline-block;
    margin-right: 10px;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
</style>
```

### Day 5: Testing & Demo Preparation

**Create test script `scripts/test_rag.py`:**

```python
"""
Test RAG functionality
"""
import asyncio
import httpx

BASE_URL = "http://localhost:8000"

async def test_rag():
    # Login
    async with httpx.AsyncClient() as client:
        # Get token
        login_response = await client.post(
            f"{BASE_URL}/api/v1/auth/login",
            data={"username": "john.doe", "password": "password123"}
        )
        token = login_response.json()["access_token"]

        headers = {"Authorization": f"Bearer {token}"}

        # Test queries
        test_queries = [
            "What is our remote work policy?",
            "How do I request vacation time?",
            "What are the office hours in the UK?",
            "Tell me about our expense reimbursement process"
        ]

        for query in test_queries:
            print(f"\n{'='*60}")
            print(f"QUERY: {query}")
            print('='*60)

            response = await client.post(
                f"{BASE_URL}/api/v1/rag/ask",
                headers=headers,
                json={"query": query, "num_chunks": 5, "temperature": 0.3}
            )

            data = response.json()

            print(f"\nANSWER:\n{data['answer']}\n")
            print(f"\nSOURCES:")
            for i, source in enumerate(data['sources'], 1):
                print(f"  [{i}] {source['title']} (score: {source['score']:.2f})")

            print(f"\nMETADATA:")
            print(f"  Retrieval: {data['metadata']['retrieval_time_ms']:.0f}ms")
            print(f"  Generation: {data['metadata']['generation_time_ms']:.0f}ms")
            print(f"  Total: {data['metadata']['total_time_ms']:.0f}ms")

if __name__ == "__main__":
    asyncio.run(test_rag())
```

**Run test:**
```bash
python scripts/test_rag.py
```

---

## Phase 2: Basic Recommendations (Days 6-8)

### Day 6: Database Schema & Service

**1. Add analytics tables**

Create `config/postgres/migrations/001_analytics.sql`:

```sql
-- Document views tracking
CREATE TABLE IF NOT EXISTS document_views (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    doc_id VARCHAR(255) NOT NULL,
    viewed_at TIMESTAMP DEFAULT NOW(),
    dwell_time_ms INTEGER,
    source VARCHAR(50),  -- 'search', 'recommendation', 'direct'
    query_id INTEGER REFERENCES search_queries(id)
);

CREATE INDEX idx_views_user_time ON document_views(user_id, viewed_at DESC);
CREATE INDEX idx_views_doc_time ON document_views(doc_id, viewed_at DESC);
CREATE INDEX idx_views_doc_user ON document_views(doc_id, user_id);

-- User interactions (clicks, bookmarks, shares)
CREATE TABLE IF NOT EXISTS user_interactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    event_type VARCHAR(50) NOT NULL,  -- 'click', 'bookmark', 'share'
    doc_id VARCHAR(255) NOT NULL,
    query_id INTEGER REFERENCES search_queries(id),
    position INTEGER,  -- Position in results
    source VARCHAR(50),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_interactions_user ON user_interactions(user_id, created_at DESC);
CREATE INDEX idx_interactions_doc ON user_interactions(doc_id, event_type);
```

**2. Create recommendation service**

Create `src/services/recommendation_service.py`:

```python
"""
Recommendation Service
Provides content-based and collaborative filtering recommendations
"""
from typing import List, Dict
from src.core.database import get_db_connection
from src.services.opensearch_service import OpenSearchService
from src.models.auth import User
import logging

logger = logging.getLogger(__name__)


class RecommendationService:
    def __init__(self):
        self.opensearch = OpenSearchService()

    async def get_related_documents(
        self,
        doc_id: str,
        user: User,
        limit: int = 5
    ) -> List[Dict]:
        """
        Get documents similar to the given document (content-based)
        Uses vector similarity on embeddings
        """
        try:
            # Get the document's embedding
            doc = await self.opensearch.get_document(doc_id)
            if not doc or "embedding" not in doc:
                return []

            doc_embedding = doc["embedding"]

            # Search for similar documents using k-NN
            similar_docs = await self.opensearch.vector_search(
                embedding=doc_embedding,
                size=limit + 1,  # +1 to exclude self
                user_groups=user.groups
            )

            # Filter out the original document
            related = [
                {
                    "doc_id": d["doc_id"],
                    "title": d["title"],
                    "snippet": d.get("text", "")[:200],
                    "score": d["score"],
                    "source": d["source"],
                    "reason": "similar_content"
                }
                for d in similar_docs
                if d["doc_id"] != doc_id
            ][:limit]

            return related

        except Exception as e:
            logger.error(f"Failed to get related documents: {e}")
            return []

    async def get_popular_in_department(
        self,
        department: str,
        country: str = None,
        days: int = 30,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get most popular documents in a department (collaborative filtering)
        """
        query = """
            SELECT
                dv.doc_id,
                COUNT(DISTINCT dv.user_id) as unique_viewers,
                COUNT(*) as view_count,
                AVG(dv.dwell_time_ms) as avg_dwell_time
            FROM document_views dv
            JOIN users u ON dv.user_id = u.id
            WHERE u.department = %s
                AND dv.viewed_at > NOW() - INTERVAL '%s days'
        """

        params = [department, days]

        if country:
            query += " AND u.country = %s"
            params.append(country)

        query += """
            GROUP BY dv.doc_id
            ORDER BY view_count DESC, avg_dwell_time DESC
            LIMIT %s
        """
        params.append(limit)

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()

            popular = []
            for row in rows:
                doc_id, unique_viewers, view_count, avg_dwell = row

                # Fetch document metadata from OpenSearch
                doc = await self.opensearch.get_document(doc_id)
                if doc:
                    popular.append({
                        "doc_id": doc_id,
                        "title": doc.get("title", "Unknown"),
                        "source": doc.get("source", "unknown"),
                        "view_count": view_count,
                        "unique_viewers": unique_viewers,
                        "avg_dwell_time_ms": int(avg_dwell) if avg_dwell else 0,
                        "reason": f"popular_in_{department.lower().replace(' ', '_')}"
                    })

            return popular

        finally:
            cursor.close()
            conn.close()

    async def get_trending(
        self,
        hours: int = 24,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get trending documents (time-decayed popularity)
        Score = (view_count / age_hours^0.8) * (1 + avg_dwell_time/60000)
        """
        query = """
            SELECT
                doc_id,
                COUNT(*) as view_count,
                AVG(dwell_time_ms) as avg_dwell_time,
                EXTRACT(EPOCH FROM (NOW() - MIN(viewed_at))) / 3600 as age_hours
            FROM document_views
            WHERE viewed_at > NOW() - INTERVAL '%s hours'
            GROUP BY doc_id
            HAVING COUNT(*) >= 3  -- Minimum threshold
        """

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(query, [hours])
            rows = cursor.fetchall()

            trending = []
            for row in rows:
                doc_id, view_count, avg_dwell, age_hours = row

                # Calculate trending score
                if age_hours > 0:
                    time_decay = age_hours ** 0.8
                    engagement_boost = 1 + (avg_dwell or 0) / 60000
                    trend_score = (view_count / time_decay) * engagement_boost
                else:
                    trend_score = view_count * 100  # Very recent

                # Fetch document metadata
                doc = await self.opensearch.get_document(doc_id)
                if doc:
                    trending.append({
                        "doc_id": doc_id,
                        "title": doc.get("title", "Unknown"),
                        "source": doc.get("source", "unknown"),
                        "trend_score": round(trend_score, 2),
                        "view_count": view_count,
                        "age_hours": round(age_hours, 1),
                        "reason": "trending"
                    })

            # Sort by trend score
            trending.sort(key=lambda x: x["trend_score"], reverse=True)

            return trending[:limit]

        finally:
            cursor.close()
            conn.close()

    async def get_personalized_recommendations(
        self,
        user: User,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get personalized recommendations for user
        Combines: popular in department + trending + similar to recent views
        """
        recommendations = []

        # 1. Popular in user's department (40% weight)
        popular = await self.get_popular_in_department(
            department=user.department,
            country=user.country,
            days=30,
            limit=4
        )
        recommendations.extend(popular)

        # 2. Trending (30% weight)
        trending = await self.get_trending(hours=48, limit=3)
        recommendations.extend(trending)

        # 3. Similar to recent views (30% weight)
        recent_views = await self._get_recent_views(user.id, limit=1)
        if recent_views:
            similar = await self.get_related_documents(
                doc_id=recent_views[0],
                user=user,
                limit=3
            )
            recommendations.extend(similar)

        # Deduplicate by doc_id
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec["doc_id"] not in seen:
                seen.add(rec["doc_id"])
                unique_recommendations.append(rec)

        return unique_recommendations[:limit]

    async def _get_recent_views(self, user_id: int, limit: int = 5) -> List[str]:
        """Get user's recent document views"""
        query = """
            SELECT DISTINCT doc_id
            FROM document_views
            WHERE user_id = %s
            ORDER BY viewed_at DESC
            LIMIT %s
        """

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(query, [user_id, limit])
            return [row[0] for row in cursor.fetchall()]
        finally:
            cursor.close()
            conn.close()

    async def track_view(
        self,
        user_id: int,
        doc_id: str,
        dwell_time_ms: int = None,
        source: str = "direct",
        query_id: int = None
    ):
        """Record a document view"""
        query = """
            INSERT INTO document_views
            (user_id, doc_id, dwell_time_ms, source, query_id)
            VALUES (%s, %s, %s, %s, %s)
        """

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(query, [user_id, doc_id, dwell_time_ms, source, query_id])
            conn.commit()
        finally:
            cursor.close()
            conn.close()
```

### Day 7: Recommendation API Endpoints

**Create `src/api/routes/recommendations.py`:**

```python
"""
Recommendation API endpoints
"""
from fastapi import APIRouter, Depends, Query
from src.models.auth import User
from src.core.security import get_current_user
from src.services.recommendation_service import RecommendationService
from typing import List, Dict
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/recommendations", tags=["Recommendations"])

recommendation_service = RecommendationService()


class RecommendationResponse(BaseModel):
    doc_id: str
    title: str
    source: str
    reason: str
    score: float = None
    view_count: int = None
    trend_score: float = None


@router.get("/related/{doc_id}", response_model=List[RecommendationResponse])
async def get_related_documents(
    doc_id: str,
    limit: int = Query(default=5, ge=1, le=20),
    current_user: User = Depends(get_current_user)
):
    """Get documents similar to the given document"""
    recommendations = await recommendation_service.get_related_documents(
        doc_id=doc_id,
        user=current_user,
        limit=limit
    )
    return recommendations


@router.get("/popular", response_model=List[RecommendationResponse])
async def get_popular_documents(
    department: str = Query(None),
    country: str = Query(None),
    days: int = Query(default=30, ge=1, le=90),
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user)
):
    """Get popular documents in department/country"""
    # Use current user's context if not specified
    dept = department or current_user.department
    ctry = country or current_user.country

    recommendations = await recommendation_service.get_popular_in_department(
        department=dept,
        country=ctry,
        days=days,
        limit=limit
    )
    return recommendations


@router.get("/trending", response_model=List[RecommendationResponse])
async def get_trending_documents(
    hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user)
):
    """Get trending documents across organization"""
    recommendations = await recommendation_service.get_trending(
        hours=hours,
        limit=limit
    )
    return recommendations


@router.get("/for-you", response_model=List[RecommendationResponse])
async def get_personalized_recommendations(
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user)
):
    """Get personalized recommendations for current user"""
    recommendations = await recommendation_service.get_personalized_recommendations(
        user=current_user,
        limit=limit
    )
    return recommendations
```

**Register in `src/api/main.py`:**

```python
from src.api.routes import recommendations

app.include_router(recommendations.router)
```

### Day 8: Recommendation UI & Testing

**Add to frontend** (in `ui/templates/index.html`):

```html
<!-- Recommendations sidebar -->
<div id="recommendations-sidebar" style="position: fixed; right: 20px; top: 100px; width: 300px; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
    <h3>🔥 Trending Now</h3>
    <ul id="trending-list"></ul>

    <h3 style="margin-top: 20px;">📊 Popular in Your Team</h3>
    <ul id="popular-list"></ul>
</div>

<script>
async function loadRecommendations() {
    const token = localStorage.getItem('token');

    // Load trending
    const trendingResp = await fetch('/api/v1/recommendations/trending?hours=48&limit=5', {
        headers: {'Authorization': `Bearer ${token}`}
    });
    const trending = await trendingResp.json();

    const trendingList = document.getElementById('trending-list');
    trendingList.innerHTML = trending.map(doc => `
        <li style="margin-bottom: 10px;">
            <a href="#" onclick="viewDocument('${doc.doc_id}')">${doc.title}</a>
            <br>
            <small style="color: #6c757d;">${doc.view_count} views, Score: ${doc.trend_score}</small>
        </li>
    `).join('');

    // Load popular in department
    const popularResp = await fetch('/api/v1/recommendations/popular?days=30&limit=5', {
        headers: {'Authorization': `Bearer ${token}`}
    });
    const popular = await popularResp.json();

    const popularList = document.getElementById('popular-list');
    popularList.innerHTML = popular.map(doc => `
        <li style="margin-bottom: 10px;">
            <a href="#" onclick="viewDocument('${doc.doc_id}')">${doc.title}</a>
            <br>
            <small style="color: #6c757d;">${doc.view_count} views</small>
        </li>
    `).join('');
}

// Load on page load
window.addEventListener('load', loadRecommendations);
</script>
```

---

## Quick Implementation Summary

### Minimum Viable Demo (3-5 days)

**Day 1-2**: RAG Integration
- Set up Ollama + basic RAG endpoint
- Simple UI integration

**Day 3**: Basic Recommendations
- Related documents (vector similarity)
- Simple trending calculation

**Day 4-5**: Polish & Testing
- Test all features end-to-end
- Create demo data
- Practice demo flow

### Testing Checklist

- [ ] RAG generates accurate answers with citations
- [ ] Recommendations show relevant content
- [ ] All APIs return proper errors
- [ ] Frontend handles loading states
- [ ] Demo users can log in
- [ ] Sample queries work as expected
- [ ] Performance is acceptable (< 3s for RAG)
- [ ] Docker Compose starts all services

---

## Environment Variables

Add to `.env`:

```bash
# LLM Configuration
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://ollama:11434
LLM_MODEL=llama3.1:8b-instruct-q4_0

# RAG Configuration
RAG_NUM_CHUNKS=5
RAG_TEMPERATURE=0.3
RAG_MAX_TOKENS=500

# Recommendations
TRENDING_WINDOW_HOURS=24
POPULAR_WINDOW_DAYS=30
```

---

This implementation guide provides a working, production-ready foundation for the VP demo. Focus on getting RAG and basic recommendations working first - these are the highest impact features that will impress stakeholders.
