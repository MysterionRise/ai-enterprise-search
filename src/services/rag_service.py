"""
Retrieval-Augmented Generation (RAG) Service
Combines search results with LLM to generate answers
"""
from typing import List, Dict, Optional
from src.services.search_service import SearchService
from src.services.llm_service import LLMService
from src.models.search import SearchRequest
from src.models.auth import User
import logging
import time
import re

logger = logging.getLogger(__name__)


class RAGService:
    """Service for generating AI-powered answers using RAG"""

    def __init__(self):
        self.search_service = SearchService()
        self.llm_service = LLMService()
        self.max_context_tokens = 6000  # Leave room for prompt + answer

    async def generate_answer(
        self,
        query: str,
        user: User,
        num_chunks: int = 5,
        temperature: float = 0.3
    ) -> Dict:
        """
        Generate answer to query using RAG pipeline

        Args:
            query: User's question
            user: Current user (for personalization and ACL)
            num_chunks: Number of document chunks to retrieve
            temperature: LLM sampling temperature (0=deterministic, 1=creative)

        Returns:
            Dict with answer, sources, citations, and metadata
        """
        start_time = time.time()

        # Step 1: Retrieve relevant chunks using hybrid search
        logger.info(f"RAG: Retrieving chunks for query: {query}")
        search_request = SearchRequest(
            query=query,
            size=num_chunks,
            use_hybrid=True,
            use_rerank=False,
            boost_personalization=True,
            user_groups=user.groups,
            user_country=user.country,
            user_department=user.department
        )

        try:
            search_results = await self.search_service.search(search_request)
        except Exception as e:
            logger.error(f"RAG: Search failed: {e}", exc_info=True)
            raise Exception(f"Failed to retrieve relevant documents: {str(e)}")

        if not search_results.results:
            logger.warning(f"RAG: No results found for query: {query}")
            return {
                "query": query,
                "answer": "I couldn't find any relevant documents to answer your question. Please try rephrasing your query or contact support for assistance.",
                "sources": [],
                "citations": [],
                "metadata": {
                    "retrieval_time_ms": (time.time() - start_time) * 1000,
                    "generation_time_ms": 0,
                    "total_time_ms": (time.time() - start_time) * 1000,
                    "chunks_used": 0,
                    "model": self.llm_service.model,
                    "temperature": temperature
                }
            }

        retrieval_time = time.time()

        # Step 2: Build context from top chunks
        context_chunks = search_results.results[:num_chunks]
        context = self._build_context(context_chunks)

        # Step 3: Build prompt with context
        prompt = self._build_prompt(
            query=query,
            context=context,
            user_context={
                "username": user.username,
                "department": user.department,
                "country": user.country
            }
        )

        logger.info(f"RAG: Generating answer with {len(context_chunks)} chunks")

        # Step 4: Generate answer using LLM
        try:
            answer = await self.llm_service.generate(
                prompt=prompt,
                max_tokens=500,
                temperature=temperature
            )
        except Exception as e:
            logger.error(f"RAG: LLM generation failed: {e}", exc_info=True)
            raise Exception(f"Failed to generate answer: {str(e)}")

        generation_time = time.time()

        # Step 5: Extract citations from answer
        citations = self._extract_citations(answer, context_chunks)

        logger.info(f"RAG: Answer generated successfully in {(generation_time - retrieval_time) * 1000:.0f}ms")

        return {
            "query": query,
            "answer": answer.strip(),
            "sources": [
                {
                    "doc_id": chunk.doc_id,
                    "chunk_id": chunk.chunk_id if hasattr(chunk, 'chunk_id') else None,
                    "title": chunk.title,
                    "snippet": chunk.snippet[:200] if chunk.snippet else "",
                    "score": chunk.score,
                    "source": chunk.source
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

    def _build_context(self, chunks: List) -> str:
        """
        Build context string from retrieved chunks

        Args:
            chunks: List of search results (chunks)

        Returns:
            Formatted context string for LLM
        """
        context_parts = []

        for i, chunk in enumerate(chunks, 1):
            title = chunk.title
            text = chunk.snippet if chunk.snippet else ""
            source = chunk.source

            context_parts.append(
                f"[Document {i}: {title} (Source: {source})]\n{text}\n"
            )

        return "\n".join(context_parts)

    def _build_prompt(self, query: str, context: str, user_context: Dict) -> str:
        """
        Build prompt for LLM with retrieved context

        Args:
            query: User's question
            context: Retrieved document context
            user_context: User information (name, dept, country)

        Returns:
            Complete prompt for LLM
        """
        # System instructions
        system = """You are an AI assistant helping employees find information from company documents.
Your role is to provide accurate, helpful answers based ONLY on the provided documents.

Key Guidelines:
1. Answer based ONLY on the provided documents - do not use external knowledge
2. If the documents don't contain enough information, say so clearly
3. Cite sources using [Document N] notation where N is the document number
4. Be concise but comprehensive (2-3 paragraphs maximum)
5. If asked about policies, quote relevant sections directly
6. Tailor your response to the user's department and location when relevant
7. Use a professional, helpful tone
8. If multiple documents contain relevant information, synthesize them coherently"""

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

    def _extract_citations(self, answer: str, chunks: List) -> List[Dict]:
        """
        Extract which documents were cited in the answer

        Args:
            answer: Generated answer text
            chunks: Retrieved chunks

        Returns:
            List of citation dictionaries
        """
        citations = []

        # Look for [Document N] patterns in answer
        doc_references = re.findall(r'\[Document (\d+)\]', answer)

        for ref in doc_references:
            doc_num = int(ref) - 1  # Convert to 0-indexed
            if 0 <= doc_num < len(chunks):
                chunk = chunks[doc_num]
                citations.append({
                    "doc_id": chunk.doc_id,
                    "title": chunk.title,
                    "reference": f"Document {ref}"
                })

        # Deduplicate citations
        seen = set()
        unique_citations = []
        for citation in citations:
            if citation["doc_id"] not in seen:
                seen.add(citation["doc_id"])
                unique_citations.append(citation)

        return unique_citations

    async def stream_answer(self, query: str, user: User, num_chunks: int = 5):
        """
        Stream answer generation (for real-time UI updates)

        Args:
            query: User's question
            user: Current user
            num_chunks: Number of chunks to retrieve

        Yields:
            Dict chunks with type and data
        """
        # First, retrieve chunks
        search_request = SearchRequest(
            query=query,
            size=num_chunks,
            use_hybrid=True,
            boost_personalization=True,
            user_groups=user.groups,
            user_country=user.country,
            user_department=user.department
        )

        try:
            search_results = await self.search_service.search(search_request)
        except Exception as e:
            logger.error(f"RAG streaming: Search failed: {e}")
            yield {
                "type": "error",
                "message": f"Failed to retrieve documents: {str(e)}"
            }
            return

        if not search_results.results:
            yield {
                "type": "error",
                "message": "No relevant documents found"
            }
            return

        # Send sources first
        context_chunks = search_results.results[:num_chunks]
        yield {
            "type": "sources",
            "sources": [
                {
                    "doc_id": chunk.doc_id,
                    "title": chunk.title,
                    "snippet": chunk.snippet[:200] if chunk.snippet else "",
                    "score": chunk.score,
                    "source": chunk.source
                }
                for chunk in context_chunks
            ]
        }

        # Build prompt
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
        try:
            async for token in self.llm_service.stream_generate(prompt, temperature=0.3):
                yield {
                    "type": "token",
                    "token": token
                }
        except Exception as e:
            logger.error(f"RAG streaming: Generation failed: {e}")
            yield {
                "type": "error",
                "message": f"Failed to generate answer: {str(e)}"
            }
            return

        # Send completion
        yield {
            "type": "done"
        }
