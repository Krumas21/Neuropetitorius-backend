"""Health check endpoint."""

import time
from dataclasses import dataclass

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.core.config import settings

router = APIRouter()

_start_time = time.time()


@dataclass
class HealthCheckResult:
    status: str
    latency_ms: int


async def check_database(db: AsyncSession) -> HealthCheckResult:
    """Check database connectivity."""
    start = time.perf_counter()
    try:
        await db.execute(text("SELECT 1"))
        latency = int((time.perf_counter() - start) * 1000)
        return HealthCheckResult(status="ok", latency_ms=latency)
    except Exception as e:
        return HealthCheckResult(status=f"error: {str(e)[:50]}", latency_ms=-1)


async def check_redis() -> HealthCheckResult:
    """Check Redis connectivity."""
    import redis.asyncio as redis
    from app.core.config import settings

    start = time.perf_counter()
    try:
        r = redis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.ping()
        await r.close()
        latency = int((time.perf_counter() - start) * 1000)
        return HealthCheckResult(status="ok", latency_ms=latency)
    except Exception as e:
        return HealthCheckResult(status=f"error: {str(e)[:50]}", latency_ms=-1)


async def check_gemini() -> HealthCheckResult:
    """Check Gemini API connectivity with simple embedding."""
    from app.llm.client import llm_client

    start = time.perf_counter()
    try:
        import asyncio

        result = await asyncio.wait_for(llm_client.get_embedding("health check"), timeout=10.0)
        latency = int((time.perf_counter() - start) * 1000)
        if result and len(result) > 0:
            return HealthCheckResult(status="ok", latency_ms=latency)
        return HealthCheckResult(status="error: empty response", latency_ms=-1)
    except asyncio.TimeoutError:
        return HealthCheckResult(status="error: timeout", latency_ms=-1)
    except Exception as e:
        return HealthCheckResult(status=f"error: {str(e)[:50]}", latency_ms=-1)


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db_session)) -> dict:
    """Liveness check with real dependency checks."""
    import asyncio

    db_check = await check_database(db)

    try:
        redis_check = await check_redis()
    except Exception:
        redis_check = HealthCheckResult(status="not configured", latency_ms=-1)

    all_ok = db_check.status == "ok"
    overall_status = "ok" if all_ok else "degraded"

    return {
        "status": overall_status,
        "version": "0.1.3",
        "git_sha": "local",
        "uptime_seconds": int(time.time() - _start_time),
        "checks": {
            "database": {"status": db_check.status, "latency_ms": db_check.latency_ms},
            "redis": {"status": redis_check.status, "latency_ms": redis_check.latency_ms},
        },
    }


@router.get("/health/live")
async def liveness() -> dict:
    """Simple liveness probe - just check if app is running."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(db: AsyncSession = Depends(get_db_session)) -> dict:
    """Readiness probe - check if can serve traffic."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        return {"status": "not ready", "reason": "database unavailable"}
