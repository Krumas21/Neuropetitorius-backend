"""Partner repository for data access."""

import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.models import Partner


class PartnerRepository:
    """Repository for partner data operations."""

    async def get_by_id(self, db, partner_id: uuid.UUID) -> "Partner | None":
        """Get partner by ID."""
        from sqlalchemy import select

        from app.db.models import Partner

        result = await db.execute(select(Partner).where(Partner.id == partner_id))
        return result.scalar_one_or_none()  # type: ignore[no-any-return]

    async def get_by_api_key_hash(self, db, api_key_hash: str) -> "Partner | None":
        """Get partner by API key hash."""
        from sqlalchemy import select

        from app.db.models import Partner

        result = await db.execute(select(Partner).where(Partner.api_key_hash == api_key_hash))
        return result.scalar_one_or_none()  # type: ignore[no-any-return]

    async def create(
        self,
        db,
        name: str,
        slug: str,
        api_key_hash: str,
        api_key_prefix: str,
        contact_email: str,
        rate_limit_rpm: int = 1000,
        rate_limit_messages_pm: int = 60,
        allowed_origins: str | None = None,
    ) -> "Partner":
        """Create a new partner."""
        from app.db.models import Partner

        partner = Partner(
            name=name,
            slug=slug,
            api_key_hash=api_key_hash,
            api_key_prefix=api_key_prefix,
            contact_email=contact_email,
            rate_limit_rpm=rate_limit_rpm,
            rate_limit_messages_pm=rate_limit_messages_pm,
            allowed_origins=allowed_origins,
        )
        db.add(partner)
        await db.commit()
        await db.refresh(partner)
        return partner

    async def update_rate_limits(
        self,
        db,
        partner_id: uuid.UUID,
        rate_limit_rpm: int,
        rate_limit_messages_pm: int,
    ) -> "Partner | None":
        """Update partner rate limits."""
        from sqlalchemy import update

        from app.db.models import Partner

        stmt = (
            update(Partner)
            .where(Partner.id == partner_id)
            .values(
                rate_limit_rpm=rate_limit_rpm,
                rate_limit_messages_pm=rate_limit_messages_pm,
            )
        )
        await db.execute(stmt)
        await db.commit()
        return await self.get_by_id(db, partner_id)


partner_repo = PartnerRepository()
