"""Usage event repository for data access."""

import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.models import UsageEvent


class UsageRepository:
    """Repository for usage event data operations."""

    async def log_event(
        self,
        db,
        partner_id: uuid.UUID,
        event_type: str,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        duration_ms: int,
        student_external_id: str | None = None,
        session_id: uuid.UUID | None = None,
    ) -> "UsageEvent":
        """Log a usage event."""
        from app.db.models import UsageEvent

        event = UsageEvent(
            partner_id=partner_id,
            event_type=event_type,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            duration_ms=duration_ms,
            student_external_id=student_external_id,
            session_id=session_id,
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return event


usage_repo = UsageRepository()
