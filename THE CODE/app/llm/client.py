"""LLM client for Gemini API with retry and circuit breaker."""

import asyncio
import logging
import time
from typing import AsyncGenerator

import tenacity
from google.genai import client, types
from google.api_core.exceptions import GoogleAPIError, ResourceExhausted, ServiceUnavailable

from app.core.config import settings
from app.core.circuit_breaker import gemini_circuit_breaker, CircuitOpenError
from app.core.errors import LlmUnavailableError, LlmTimeoutError, EmbeddingFailedError

logger = logging.getLogger(__name__)

_client = None


def get_llm_client():
    """Get or create LLM client."""
    global _client
    if _client is None:
        _client = client.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def _retry_on_external_error(retry_state):
    """Determine if we should retry on the exception."""
    if retry_state.outcome is None:
        return True
    exc = retry_state.outcome.exception()
    if exc is None:
        return False
    if isinstance(exc, (ResourceExhausted, ServiceUnavailable)):
        return True
    if isinstance(exc, GoogleAPIError) and hasattr(exc, "code"):
        return exc.code >= 500
    return False


class LLMClient:
    """Client for Gemini API operations with resilience patterns."""

    def __init__(self):
        self._client = None
        self.generation_model = settings.GEMINI_GENERATION_MODEL
        self.embedding_model = settings.GEMINI_EMBEDDING_MODEL

    def _get_client(self):
        if self._client is None:
            self._client = get_llm_client()
        return self._client

    @tenacity.retry(
        retry=_retry_on_external_error,
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
        before_sleep=lambda retry_state: logger.warning(f"Gemini API call failed, retrying..."),
    )
    async def _generate_with_retry(
        self, prompt: str, system_instruction: str | None, temperature: float
    ) -> str:
        """Generate text with retry."""
        contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]
        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction,
        )
        return self._get_client().models.generate_content(
            model=self.generation_model,
            contents=contents,
            config=config,
        )

    async def generate_text(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        """Generate text using Gemini with retry and circuit breaker."""
        try:
            result = await asyncio.wait_for(
                self._generate_with_retry(prompt, system_instruction, temperature),
                timeout=settings.GEMINI_TIMEOUT,
            )
            return result.text

        except asyncio.TimeoutError:
            logger.error("Gemini API timeout")
            raise LlmTimeoutError()
        except CircuitOpenError as e:
            logger.error(f"Gemini circuit breaker open: {e}")
            raise LlmUnavailableError()
        except ResourceExhausted:
            logger.error("Gemini API rate limit hit")
            raise LlmUnavailableError()
        except Exception as e:
            logger.exception(f"Gemini generate_text failed: {e}")
            raise LlmUnavailableError()

    async def generate_content_stream(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """Generate text with streaming response."""
        contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]
        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction,
        )

        try:
            for chunk in self._get_client().models.generate_content_stream(
                model=self.generation_model,
                contents=contents,
                config=config,
            ):
                yield chunk.text
        except GoogleAPIError as e:
            logger.exception(f"Gemini streaming failed: {e}")
            raise LlmUnavailableError()

    @tenacity.retry(
        retry=_retry_on_external_error,
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    async def _embed_with_retry(self, text: str) -> list[float]:
        """Get embedding with retry."""
        result = self._get_client().models.embed_content(
            model=self.embedding_model,
            contents=[text],
            config=types.EmbedContentConfig(
                task_type="SEMANTIC_SIMILARITY",
            ),
        )
        return result.embeddings[0].values

    async def get_embedding(self, text: str) -> list[float]:
        """Get embedding vector for text using Gemini Embedding API."""
        try:
            result = await asyncio.wait_for(
                self._embed_with_retry(text),
                timeout=10.0,
            )
            return result

        except asyncio.TimeoutError:
            logger.error("Embedding timeout")
            raise EmbeddingFailedError()
        except CircuitOpenError as e:
            logger.error(f"Gemini embedding circuit breaker open: {e}")
            raise EmbeddingFailedError()
        except Exception as e:
            logger.exception(f"Embedding failed: {e}")
            raise EmbeddingFailedError()

    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Get embedding vectors for multiple texts using Gemini Embedding API.

        Args:
            texts: List of texts to embed (max 100 texts per batch)

        Returns:
            List of embedding vectors
        """
        texts = texts[:100]

        results = []
        for i in range(0, len(texts), 100):
            batch = texts[i : i + 100]
            try:
                result = await asyncio.wait_for(
                    self._embed_batch_with_retry(batch),
                    timeout=30.0,
                )
                results.extend(result)
            except asyncio.TimeoutError:
                logger.error("Batch embedding timeout")
                raise EmbeddingFailedError()
            except Exception as e:
                logger.exception(f"Batch embedding failed: {e}")
                raise EmbeddingFailedError()

        return results

    @tenacity.retry(
        retry=_retry_on_external_error,
        stop=tenacity.stop_after_attempt(3),
        wait=tenacity.wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    async def _embed_batch_with_retry(self, texts: list[str]) -> list[list[float]]:
        """Get embeddings for batch with retry."""
        result = self._get_client().models.embed_content(
            model=self.embedding_model,
            contents=texts,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
            ),
        )
        return [emb.values for emb in result.embeddings]

    async def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        try:
            result = self._get_client().models.count_tokens(
                model=self.generation_model,
                contents=[types.Content(role="user", parts=[types.Part(text=text)])],
            )
            return result.total_tokens
        except Exception as e:
            logger.warning(f"Token count failed: {e}")
            return 0


llm_client = LLMClient()
