"""Admin API endpoints for partner management."""

import secrets
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field

from app.core.auth import hash_api_key
from app.core.config import settings
from app.db.repositories import partner_repo, usage_repo
from app.db.models import UsageEvent
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/admin", tags=["admin"])


def verify_admin_key(x_admin_key: str | None = Header(default=None)) -> bool:
    """Verify admin API key."""
    if not x_admin_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Admin-Key header required",
        )
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin key",
        )
    return True


class CreatePartnerRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100)
    contact_email: EmailStr
    rate_limit_rpm: int = Field(default=1000, ge=10, le=10000)
    rate_limit_messages_pm: int = Field(default=60, ge=10, le=1000)
    allowed_origins: list[str] | None = None


class PartnerResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    api_key_prefix: str
    contact_email: str
    rate_limit_rpm: int
    rate_limit_messages_pm: int
    allowed_origins: list[str] | None
    is_active: bool
    created_at: datetime


class UpdatePartnerRequest(BaseModel):
    name: str | None = None
    rate_limit_rpm: int | None = None
    rate_limit_messages_pm: int | None = None
    allowed_origins: list[str] | None = None
    is_active: bool | None = None


class UsageStatsResponse(BaseModel):
    partner_id: uuid.UUID
    total_requests: int
    total_prompt_tokens: int
    total_completion_tokens: int
    total_duration_ms: int
    period_days: int


def _generate_api_key() -> tuple[str, str]:
    """Generate a new API key and its prefix."""
    raw_key = f"npk_{secrets.token_urlsafe(32)}"
    prefix = raw_key[:20]
    return raw_key, prefix


@router.post("/partners")
async def create_partner(
    request: CreatePartnerRequest,
    _: bool = Depends(verify_admin_key),
    db: AsyncSession = None,
) -> dict:
    """Create a new partner. Returns raw API key ONCE - store it securely."""
    from app.api.deps import get_db_session

    async for session in get_db_session():
        raw_key, prefix = _generate_api_key()
        key_hash = hash_api_key(raw_key)

        partner = await partner_repo.create(
            session,
            name=request.name,
            slug=request.slug,
            api_key_hash=key_hash,
            api_key_prefix=prefix,
            contact_email=request.contact_email,
            rate_limit_rpm=request.rate_limit_rpm,
            rate_limit_messages_pm=request.rate_limit_messages_pm,
            allowed_origins=",".join(request.allowed_origins) if request.allowed_origins else None,
        )

        await session.commit()

        return {
            "partner_id": str(partner.id),
            "api_key": raw_key,
            "message": "Store this API key securely - it will not be shown again",
        }


@router.get("/partners/{partner_id}")
async def get_partner(
    partner_id: str,
    _: bool = Depends(verify_admin_key),
    db: AsyncSession = None,
) -> PartnerResponse:
    """Get partner details."""
    from app.api.deps import get_db_session

    async for session in get_db_session():
        partner = await partner_repo.get_by_id(session, uuid.UUID(partner_id))
        if not partner:
            raise HTTPException(status_code=404, detail="Partner not found")

        return PartnerResponse(
            id=partner.id,
            name=partner.name,
            slug=partner.slug,
            api_key_prefix=partner.api_key_prefix,
            contact_email=partner.contact_email,
            rate_limit_rpm=partner.rate_limit_rpm,
            rate_limit_messages_pm=partner.rate_limit_messages_pm,
            allowed_origins=partner.allowed_origins.split(",") if partner.allowed_origins else None,
            is_active=partner.is_active,
            created_at=partner.created_at,
        )


@router.patch("/partners/{partner_id}")
async def update_partner(
    partner_id: str,
    request: UpdatePartnerRequest,
    _: bool = Depends(verify_admin_key),
) -> PartnerResponse:
    """Update partner settings."""
    from app.api.deps import get_db_session

    async for session in get_db_session():
        partner = await partner_repo.get_by_id(session, uuid.UUID(partner_id))
        if not partner:
            raise HTTPException(status_code=404, detail="Partner not found")

        if request.name is not None:
            partner.name = request.name
        if request.rate_limit_rpm is not None:
            partner.rate_limit_rpm = request.rate_limit_rpm
        if request.rate_limit_messages_pm is not None:
            partner.rate_limit_messages_pm = request.rate_limit_messages_pm
        if request.allowed_origins is not None:
            partner.allowed_origins = (
                ",".join(request.allowed_origins) if request.allowed_origins else None
            )
        if request.is_active is not None:
            partner.is_active = request.is_active

        await session.commit()

        return PartnerResponse(
            id=partner.id,
            name=partner.name,
            slug=partner.slug,
            api_key_prefix=partner.api_key_prefix,
            contact_email=partner.contact_email,
            rate_limit_rpm=partner.rate_limit_rpm,
            rate_limit_messages_pm=partner.rate_limit_messages_pm,
            allowed_origins=partner.allowed_origins.split(",") if partner.allowed_origins else None,
            is_active=partner.is_active,
            created_at=partner.created_at,
        )


@router.delete("/partners/{partner_id}")
async def deactivate_partner(
    partner_id: str,
    _: bool = Depends(verify_admin_key),
) -> dict:
    """Deactivate a partner (soft delete)."""
    from app.api.deps import get_db_session

    async for session in get_db_session():
        partner = await partner_repo.get_by_id(session, uuid.UUID(partner_id))
        if not partner:
            raise HTTPException(status_code=404, detail="Partner not found")

        partner.is_active = False
        await session.commit()

        return {"message": "Partner deactivated"}


@router.get("/partners/{partner_id}/usage")
async def get_partner_usage(
    partner_id: str,
    days: int = Query(default=30, ge=1, le=365),
    _: bool = Depends(verify_admin_key),
) -> UsageStatsResponse:
    """Get usage statistics for a partner."""
    from app.api.deps import get_db_session
    from datetime import timedelta

    async for session in get_db_session():
        partner = await partner_repo.get_by_id(session, uuid.UUID(partner_id))
        if not partner:
            raise HTTPException(status_code=404, detail="Partner not found")

        from datetime import datetime

        since = datetime.utcnow() - timedelta(days=days)

        result = await session.execute(
            select(
                func.count(UsageEvent.id),
                func.coalesce(func.sum(UsageEvent.prompt_tokens), 0),
                func.coalesce(func.sum(UsageEvent.completion_tokens), 0),
                func.coalesce(func.sum(UsageEvent.duration_ms), 0),
            ).where(
                UsageEvent.partner_id == uuid.UUID(partner_id),
                UsageEvent.created_at >= since,
            )
        )

        row = result.one()

        return UsageStatsResponse(
            partner_id=partner.id,
            total_requests=row[0] or 0,
            total_prompt_tokens=row[1],
            total_completion_tokens=row[2],
            total_duration_ms=row[3],
            period_days=days,
        )


@router.get("/metrics")
async def get_metrics(
    _: bool = Depends(verify_admin_key),
) -> dict:
    """Get system metrics for monitoring."""
    from datetime import datetime, timedelta
    from app.api.deps import get_db_session

    async for session in get_db_session():
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)

        result = await session.execute(
            select(
                func.count(UsageEvent.id),
                func.coalesce(func.sum(UsageEvent.prompt_tokens), 0),
                func.coalesce(func.sum(UsageEvent.completion_tokens), 0),
                func.coalesce(func.avg(UsageEvent.duration_ms), 0),
            ).where(UsageEvent.created_at >= one_hour_ago)
        )

        row = result.one()

        return {
            "last_hour": {
                "total_requests": row[0] or 0,
                "prompt_tokens": row[1],
                "completion_tokens": row[2],
                "avg_duration_ms": int(row[3] or 0),
            }
        }
