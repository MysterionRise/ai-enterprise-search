"""
LLM Service for RAG answer generation
Supports: Ollama (local), OpenAI, Anthropic
"""

import logging
import os
from collections.abc import AsyncGenerator

import httpx

logger = logging.getLogger(__name__)


class LLMService:
    """
    Service for interacting with Large Language Models
    Supports multiple providers: Ollama (local), OpenAI, Anthropic
    """

    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "ollama")
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("LLM_MODEL", "llama3.1:8b-instruct-q4_0")
        self.timeout = httpx.Timeout(60.0)  # LLM can be slow
        logger.info(f"LLM Service initialized: provider={self.provider}, model={self.model}")

    async def generate(
        self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7, stream: bool = False
    ) -> str:
        """
        Generate response from LLM

        Args:
            prompt: Input prompt for the LLM
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            stream: Whether to stream response (not used in this method)

        Returns:
            Generated text response
        """
        if self.provider == "ollama":
            return await self._generate_ollama(prompt, max_tokens, temperature, stream)
        elif self.provider == "openai":
            return await self._generate_openai(prompt, max_tokens, temperature, stream)
        elif self.provider == "anthropic":
            return await self._generate_anthropic(prompt, max_tokens, temperature, stream)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    async def _generate_ollama(
        self, prompt: str, max_tokens: int, temperature: float, stream: bool
    ) -> str:
        """Generate using Ollama"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,  # Non-streaming for this method
                        "options": {
                            "num_predict": max_tokens,
                            "temperature": temperature,
                            "top_p": 0.9,
                        },
                    },
                )
                response.raise_for_status()
                result = response.json()
                return result.get("response", "")
        except httpx.TimeoutException:
            logger.error(f"Ollama request timed out after {self.timeout.read}s")
            raise Exception("LLM generation timed out. Please try again.")
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama HTTP error: {e.response.status_code}")
            raise Exception(f"LLM service error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}", exc_info=True)
            raise Exception(f"Failed to generate response: {str(e)}")

    async def stream_generate(
        self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """
        Stream response from LLM token by token

        Args:
            prompt: Input prompt for the LLM
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)

        Yields:
            Individual tokens as they are generated
        """
        if self.provider == "ollama":
            async for token in self._stream_ollama(prompt, max_tokens, temperature):
                yield token
        else:
            # For non-streaming providers, yield the full response
            response = await self.generate(prompt, max_tokens, temperature)
            yield response

    async def _stream_ollama(
        self, prompt: str, max_tokens: int, temperature: float
    ) -> AsyncGenerator[str, None]:
        """Stream response from Ollama"""
        try:
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
                            "top_p": 0.9,
                        },
                    },
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            import json

                            try:
                                data = json.loads(line)
                                if "response" in data:
                                    yield data["response"]
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse streaming response: {line}")
                                continue
        except Exception as e:
            logger.error(f"Ollama streaming failed: {e}", exc_info=True)
            raise Exception(f"Failed to stream response: {str(e)}")

    async def _generate_openai(
        self, prompt: str, max_tokens: int, temperature: float, stream: bool
    ) -> str:
        """Generate using OpenAI API (future implementation)"""
        # TODO: Implement OpenAI integration
        # Will require: pip install openai
        # and OPENAI_API_KEY environment variable
        raise NotImplementedError("OpenAI provider not yet implemented")

    async def _generate_anthropic(
        self, prompt: str, max_tokens: int, temperature: float, stream: bool
    ) -> str:
        """Generate using Anthropic API (future implementation)"""
        # TODO: Implement Anthropic integration
        # Will require: pip install anthropic
        # and ANTHROPIC_API_KEY environment variable
        raise NotImplementedError("Anthropic provider not yet implemented")

    async def health_check(self) -> bool:
        """
        Check if LLM service is available

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            if self.provider == "ollama":
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"{self.base_url}/api/tags")
                    return response.status_code == 200
            else:
                # For other providers, assume healthy if configured
                return True
        except Exception as e:
            logger.error(f"LLM health check failed: {e}")
            return False

    async def get_available_models(self) -> list:
        """
        Get list of available models

        Returns:
            List of model names
        """
        try:
            if self.provider == "ollama":
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"{self.base_url}/api/tags")
                    if response.status_code == 200:
                        data = response.json()
                        return [model["name"] for model in data.get("models", [])]
            return []
        except Exception as e:
            logger.error(f"Failed to get available models: {e}")
            return []
