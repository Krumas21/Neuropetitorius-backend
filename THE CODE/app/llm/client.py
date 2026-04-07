"""LLM client for Gemini API."""


from google.genai import client, types

from app.core.config import settings

_client = None


def get_llm_client():
    """Get or create LLM client."""
    global _client
    if _client is None:
        _client = client.Client(api_key=settings.GEMINI_API_KEY)
    return _client


class LLMClient:
    """Client for Gemini API operations."""

    def __init__(self):
        self._client = None
        self.generation_model = settings.GEMINI_GENERATION_MODEL
        self.embedding_model = settings.GEMINI_EMBEDDING_MODEL

    def _get_client(self):
        if self._client is None:
            self._client = get_llm_client()
        return self._client

    def generate_text(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        """Generate text using Gemini."""
        contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]

        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction,
        )

        response = self._get_client().models.generate_content(
            model=self.generation_model,
            contents=contents,
            config=config,
        )

        return response.text

    def generate_content_stream(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float = 0.7,
    ):
        """Generate text with streaming response."""
        contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]

        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction,
        )

        for chunk in self._get_client().models.generate_content_stream(
            model=self.generation_model,
            contents=contents,
            config=config,
        ):
            yield chunk.text

    def get_embedding(self, text: str) -> list[float]:
        """Get embedding vector for text using Gemini Embedding API."""
        result = self._get_client().models.embed_content(
            model=self.embedding_model,
            contents=[text],
            config=types.EmbedContentConfig(
                task_type="SEMANTIC_SIMILARITY",
            ),
        )
        return result.embeddings[0].values

    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        result = self._get_client().models.count_tokens(
            model=self.generation_model,
            contents=[types.Content(role="user", parts=[types.Part(text=text)])],
        )
        return result.total_tokens


llm_client = LLMClient()
