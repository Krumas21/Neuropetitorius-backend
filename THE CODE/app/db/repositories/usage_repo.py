"""Usage event repository for data access."""

import uuid
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import select, func

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

    async def get_partner_stats(
        self,
        db,
        partner_id: uuid.UUID,
        days: int = 30,
    ) -> dict:
        """Get usage statistics for a partner."""
        from app.db.models import UsageEvent

        since = datetime.utcnow() - timedelta(days=days)

        result = await db.execute(
            select(
                func.count(UsageEvent.id),
                func.coalesce(func.sum(UsageEvent.prompt_tokens), 0),
                func.coalesce(func.sum(UsageEvent.completion_tokens), 0),
                func.coalesce(func.sum(UsageEvent.duration_ms), 0),
            ).where(
                UsageEvent.partner_id == partner_id,
                UsageEvent.created_at >= since,
            )
        )

        row = result.one()
        return {
            "total_requests": row[0] or 0,
            "total_prompt_tokens": row[1],
            "total_completion_tokens": row[2],
            "total_duration_ms": row[3],
        }


usage_repo = UsageRepository()
