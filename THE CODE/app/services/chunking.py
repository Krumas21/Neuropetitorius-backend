"""Text chunking service."""

from typing import Any

from app.core.config import settings


class ChunkingService:
    """Service for splitting content into chunks."""

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP

    def chunk_text(self, text: str) -> list[dict[str, Any]]:
        """Split text into overlapping chunks with token estimation."""
        if not text or not text.strip():
            return []

        text = text.strip()
        chunks = []
        start = 0
        index = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end]

            chunk_text = self._clean_chunk(chunk_text, start, len(text))

            if chunk_text.strip():
                chunks.append(
                    {
                        "text": chunk_text.strip(),
                        "chunk_index": index,
                        "token_count": self._estimate_tokens(chunk_text),
                    }
                )
                index += 1

            start += self.chunk_size - self.chunk_overlap
            if start >= len(text):
                break

        return chunks

    def _clean_chunk(self, chunk: str, start: int, total: int) -> str:
        """Clean up chunk boundaries."""
        if start == 0:
            return chunk

        if start + self.chunk_size >= total:
            return chunk

        sentence_end = max(
            chunk.rfind(". "),
            chunk.rfind("! "),
            chunk.rfind("? "),
            chunk.rfind(".\n"),
        )

        if sentence_end > self.chunk_size // 2:
            return chunk[: sentence_end + 1]

        return chunk

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (chars / 4)."""
        return len(text) // 4


chunking_service = ChunkingService()
