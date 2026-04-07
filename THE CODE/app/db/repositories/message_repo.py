"""Message repository for data access."""

import json
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.models import Message


class MessageRepository:
    """Repository for message data operations."""

    async def create(
        self,
        db,
        partner_id: uuid.UUID,
        session_id: uuid.UUID,
        role: str,
        content: str,
        retrieved_chunk_ids: list[str] | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
    ) -> "Message":
        """Create a new message."""
        from app.db.models import Message

        chunk_ids_str = None
        if retrieved_chunk_ids:
            chunk_ids_str = json.dumps(retrieved_chunk_ids)

        message = Message(
            partner_id=partner_id,
            session_id=session_id,
            role=role,
            content=content,
            retrieved_chunk_ids=chunk_ids_str,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message

    async def get_by_session(
        self,
        db,
        partner_id: uuid.UUID,
        session_id: uuid.UUID,
        limit: int = 50,
        before_id: uuid.UUID | None = None,
    ) -> list["Message"]:
        """Get messages for a session, newest first."""
        from sqlalchemy import and_, select

        from app.db.models import Message

        query = select(Message).where(
            and_(
                Message.partner_id == partner_id,
                Message.session_id == session_id,
            )
        )

        if before_id:
            before_msg = await db.get(Message, before_id)
            if before_msg:
                query = query.where(Message.created_at < before_msg.created_at)

        query = query.order_by(Message.created_at.desc()).limit(limit)

        result = await db.execute(query)
        messages = result.scalars().all()
        return list(reversed(messages))

    async def get_recent(
        self,
        db,
        session_id: uuid.UUID,
        limit: int = 10,
    ) -> list["Message"]:
        """Get recent messages for context."""
        from sqlalchemy import select

        from app.db.models import Message

        result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        return list(reversed(messages))


message_repo = MessageRepository()
