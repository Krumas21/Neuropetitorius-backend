"""Session repository for data access."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.models import Session


class SessionRepository:
    """Repository for session data operations."""

    async def create(
        self,
        db,
        partner_id: uuid.UUID,
        student_external_id: str,
        topic_id: str,
        language: str,
        metadata: dict,
    ) -> "Session":
        """Create a new session."""
        from app.db.models import Session

        session = Session(
            partner_id=partner_id,
            student_external_id=student_external_id,
            topic_id=topic_id,
            language=language,
            metadata=metadata,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    async def create_with_content(
        self,
        db,
        partner_id: uuid.UUID,
        student_external_id: str,
        title: str,
        language: str,
        metadata: dict,
        content_title: str,
        content_subject: str | None,
        content_fingerprint: str,
        content_length: int,
    ) -> "Session":
        """Create a new session with content (Mode 1 - Just-in-Time)."""
        from app.db.models import Session

        session = Session(
            partner_id=partner_id,
            student_external_id=student_external_id,
            language=language,
            metadata=metadata,
            content_title=content_title,
            content_subject=content_subject,
            content_fingerprint=content_fingerprint,
            content_length=content_length,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    async def get_by_id(self, db, partner_id: uuid.UUID, session_id: uuid.UUID) -> "Session | None":
        """Get session by ID, filtering by partner_id."""
        from sqlalchemy import select

        from app.db.models import Session

        result = await db.execute(
            select(Session).where(
                Session.id == session_id,
                Session.partner_id == partner_id,
            )
        )
        return result.scalar_one_or_none()

    async def delete(self, db, partner_id: uuid.UUID, session_id: uuid.UUID) -> bool:
        """Delete a session. Returns True if deleted."""
        from sqlalchemy import select

        from app.db.models import Session

        result = await db.execute(
            select(Session).where(
                Session.id == session_id,
                Session.partner_id == partner_id,
            )
        )
        session = result.scalar_one_or_none()

        if session:
            await db.delete(session)
            await db.commit()
            return True
        return False

    async def update_last_message(self, db, session_id: uuid.UUID) -> None:
        """Update the last_message_at timestamp."""
        from sqlalchemy import update

        from app.db.models import Session

        stmt = (
            update(Session)
            .where(Session.id == session_id)
            .values(last_message_at=datetime.utcnow())
        )
        await db.execute(stmt)
        await db.commit()

    async def delete_expired_sessions(self, db, inactive_hours: int, never_used_hours: int) -> int:
        """Delete sessions that have expired due to inactivity. Returns count deleted."""
        from sqlalchemy import delete, and_, or_

        from app.db.models import Session

        inactive_cutoff = datetime.utcnow() - datetime.timedelta(hours=inactive_hours)
        never_used_cutoff = datetime.utcnow() - datetime.timedelta(hours=never_used_hours)

        stmt = delete(Session).where(
            or_(
                and_(
                    Session.last_message_at.isnot(None), Session.last_message_at < inactive_cutoff
                ),
                and_(Session.last_message_at.is_(None), Session.created_at < never_used_cutoff),
            )
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.rowcount

    async def search_session_chunks(
        self,
        db,
        partner_id: uuid.UUID,
        session_id: uuid.UUID,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list:
        """Search chunks by vector similarity within a session."""
        from sqlalchemy import select, text

        from app.db.models import SessionChunk

        query_embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

        result = await db.execute(
            text("""
                SELECT id, session_id, chunk_index, text, token_count,
                       embedding <=> cast(:query_embedding as vector) as distance
                FROM session_chunks
                WHERE session_id = :session_id
                  AND partner_id = :partner_id
                ORDER BY embedding <=> cast(:query_embedding as vector)
                LIMIT :top_k
            """),
            {
                "query_embedding": query_embedding_str,
                "session_id": str(session_id),
                "partner_id": str(partner_id),
                "top_k": top_k,
            },
        )

        rows = result.fetchall()
        return [
            {
                "id": row[0],
                "session_id": row[1],
                "chunk_index": row[2],
                "text": row[3],
                "token_count": row[4],
                "distance": row[5],
            }
            for row in rows
        ]


session_repo = SessionRepository()
