"""Content repository for data access."""

import uuid
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.db.models import ContentItem


class ChunkResult:
    """Result from a chunk search."""

    def __init__(
        self,
        id: uuid.UUID,
        content_item_id: uuid.UUID,
        text: str,
        chunk_index: int,
        distance: float,
        content_item_title: str | None = None,
    ):
        self.id = id
        self.content_item_id = content_item_id
        self.text = text
        self.chunk_index = chunk_index
        self.distance = distance
        self.content_item_title = content_item_title


class ContentRepository:
    """Repository for content data operations."""

    async def get_by_topic_id(
        self, db, partner_id: uuid.UUID, topic_id: str
    ) -> "ContentItem | None":
        """Get content item by topic_id for a partner."""
        from sqlalchemy import select

        from app.db.models import ContentItem

        result = await db.execute(
            select(ContentItem).where(
                ContentItem.partner_id == partner_id,
                ContentItem.topic_id == topic_id,
            )
        )
        return result.scalar_one_or_none()  # type: ignore[no-any-return]

    async def upsert(
        self,
        db,
        partner_id: uuid.UUID,
        topic_id: str,
        title: str,
        subject: str | None,
        language: str,
        raw_content: str,
        content_hash: str,
    ) -> tuple["ContentItem", bool]:
        """Insert or update content item. Returns (item, is_new)."""
        from sqlalchemy import select

        from app.db.models import ContentItem

        existing = await db.execute(
            select(ContentItem).where(
                ContentItem.partner_id == partner_id,
                ContentItem.topic_id == topic_id,
            )
        )
        item = existing.scalar_one_or_none()

        if item:
            is_new = item.content_hash != content_hash
            item.title = title
            item.subject = subject
            item.language = language
            item.raw_content = raw_content
            item.content_hash = content_hash
            await db.commit()
            await db.refresh(item)
            return item, is_new

        item = ContentItem(
            partner_id=partner_id,
            topic_id=topic_id,
            title=title,
            subject=subject,
            language=language,
            raw_content=raw_content,
            content_hash=content_hash,
        )
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return item, True

    async def delete(self, db, partner_id: uuid.UUID, topic_id: str) -> bool:
        """Delete content item by topic_id. Returns True if deleted."""
        from sqlalchemy import select

        from app.db.models import ContentItem

        result = await db.execute(
            select(ContentItem).where(
                ContentItem.partner_id == partner_id,
                ContentItem.topic_id == topic_id,
            )
        )
        item = result.scalar_one_or_none()

        if item:
            await db.delete(item)
            await db.commit()
            return True
        return False

    async def insert_chunks(self, db, chunks: list[dict[str, Any]]) -> None:
        """Insert multiple content chunks."""
        from sqlalchemy import insert

        from app.db.models import ContentChunk

        await db.execute(insert(ContentChunk), chunks)
        await db.commit()

    async def delete_chunks_by_content_item(self, db, content_item_id: uuid.UUID) -> int:
        """Delete all chunks for a content item. Returns count deleted."""
        from sqlalchemy import select

        from app.db.models import ContentChunk

        result = await db.execute(
            select(ContentChunk).where(ContentChunk.content_item_id == content_item_id)
        )
        chunks = result.scalars().all()
        count = len(chunks)

        for chunk in chunks:
            await db.delete(chunk)
        await db.commit()
        return count

    async def search_chunks(
        self,
        db,
        partner_id: uuid.UUID,
        topic_id: str,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[ChunkResult]:
        """Search chunks by vector similarity within a topic.

        Note: Uses basic retrieval for now - returns first N chunks.
        """
        from sqlalchemy import select

        from app.db.models import ContentChunk, ContentItem

        result = await db.execute(
            select(ContentChunk, ContentItem.title)
            .join(ContentItem, ContentChunk.content_item_id == ContentItem.id)
            .where(
                ContentItem.partner_id == partner_id,
                ContentItem.topic_id == topic_id,
            )
            .limit(top_k)
        )

        rows = result.all()
        results = []
        for row in rows:
            chunk = row[0]
            results.append(
                ChunkResult(
                    id=chunk.id,
                    content_item_id=chunk.content_item_id,
                    text=chunk.text,
                    chunk_index=chunk.chunk_index,
                    distance=0.0,
                    content_item_title=row[1],
                )
            )
        return results

    async def get_content_item_title(self, db, content_item_id: uuid.UUID) -> str | None:
        """Get title of a content item."""
        from sqlalchemy import select

        from app.db.models import ContentItem

        result = await db.execute(
            select(ContentItem.title).where(ContentItem.id == content_item_id)
        )
        return result.scalar_one_or_none()  # type: ignore[no-any-return]


content_repo = ContentRepository()
