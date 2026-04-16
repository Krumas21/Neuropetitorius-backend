"""Background scheduler for maintenance tasks."""

import logging
from datetime import datetime, timedelta

import apscheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.repositories import session_repo
from app.db.session import get_db

logger = logging.getLogger(__name__)


async def delete_expired_sessions_job():
    """Delete sessions that have expired due to inactivity."""
    async for db in get_db():
        try:
            count = await session_repo.delete_expired_sessions(
                db,
                inactive_hours=settings.SESSION_AUTO_EXPIRE_INACTIVE_HOURS,
                never_used_hours=settings.SESSION_AUTO_EXPIRE_NEVER_USED_HOURS,
            )
            if count > 0:
                logger.info(f"Deleted {count} expired sessions")
        except Exception as e:
            logger.error(f"Error deleting expired sessions: {e}")
        break


async def cleanup_embedding_cache_job():
    """Clean up old embedding cache entries."""
    from sqlalchemy import delete, and_

    from app.db.models import EmbeddingCache

    async for db in get_db():
        try:
            cutoff = datetime.utcnow() - timedelta(days=settings.EMBEDDING_CACHE_TTL_DAYS)
            stmt = delete(EmbeddingCache).where(
                and_(
                    EmbeddingCache.last_used_at < cutoff,
                    EmbeddingCache.hit_count < 2,
                )
            )
            result = await db.execute(stmt)
            await db.commit()
            count = result.rowcount
            if count > 0:
                logger.info(f"Cleaned up {count} old embedding cache entries")
        except Exception as e:
            logger.error(f"Error cleaning embedding cache: {e}")
        break


def setup_scheduler(app):
    """Set up background scheduler for maintenance tasks."""
    scheduler = apscheduler.schedulers.asyncio.AsyncIOScheduler()

    scheduler.add_job(
        delete_expired_sessions_job,
        CronTrigger(hour=2, minute=0),
        id="delete_expired_sessions",
        name="Delete expired sessions",
        replace_existing=True,
    )

    scheduler.add_job(
        cleanup_embedding_cache_job,
        CronTrigger(hour=3, minute=0, day_of_week="sunday"),
        id="cleanup_embedding_cache",
        name="Clean up embedding cache",
        replace_existing=True,
    )

    return scheduler
