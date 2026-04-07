"""API dependencies."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_api_key
from app.core.errors import InvalidApiKeyError, MissingAuthError, PartnerInactiveError
from app.db.repositories.partner_repo import partner_repo
from app.db.session import get_session_maker


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    session_maker = get_session_maker()
    async with session_maker() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db_session)]


class CurrentPartner:
    """Current authenticated partner."""

    def __init__(self, id: str, name: str, slug: str, rate_limit_rpm: int, is_active: bool):
        self.id = id
        self.name = name
        self.slug = slug
        self.rate_limit_rpm = rate_limit_rpm
        self.is_active = is_active


async def get_current_partner(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db_session),
) -> CurrentPartner:
    """Get current partner from Authorization header."""
    if not authorization:
        raise MissingAuthError()

    if not authorization.startswith("Bearer "):
        raise InvalidApiKeyError()

    raw_key = authorization[7:]
    key_hash = hash_api_key(raw_key)

    partner = await partner_repo.get_by_api_key_hash(db, key_hash)

    if not partner:
        raise InvalidApiKeyError()

    if not partner.is_active:
        raise PartnerInactiveError()

    return CurrentPartner(
        id=str(partner.id),
        name=partner.name,
        slug=partner.slug,
        rate_limit_rpm=partner.rate_limit_rpm,
        is_active=partner.is_active,
    )


CurrentPartnerDep = Annotated[CurrentPartner, Depends(get_current_partner)]
