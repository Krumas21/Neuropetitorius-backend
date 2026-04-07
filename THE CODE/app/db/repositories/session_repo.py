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
        return result.scalar_one_or_none()  # type: ignore[no-any-return]

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


session_repo = SessionRepository()
