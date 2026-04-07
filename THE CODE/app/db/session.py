"""Database session management."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


def init_db() -> None:
    """Initialize the database engine and session factory."""
    global _engine, _session_maker
    _engine = create_async_engine(
        settings.DATABASE_URL,
        echo=settings.ENV == "development",
        pool_pre_ping=True,
    )
    _session_maker = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    """Get or create the session maker."""
    global _session_maker
    if _session_maker is None:
        init_db()
    return _session_maker  # type: ignore[return-value]


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session for dependency injection."""
    session_maker = get_session_maker()
    async with session_maker() as session:
        yield session


async def get_db() -> AsyncSession:
    """Get database session."""
    session_maker = get_session_maker()
    async with session_maker() as session:
        return session
