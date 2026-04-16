"""Rate limiting using slowapi with Redis backend."""

import os
from functools import lru_cache
from typing import Callable

from fastapi import Request
from slowapi import Limiter
from slowapi._utils import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request as StarletteRequest
from starlette.responses import JSONResponse

from app.core.config import settings


def get_rate_limit_key(request: Request, prefix: str = "") -> str:
    """Get rate limit key from request.

    Uses the API key from Authorization header if available,
    otherwise falls back to IP address.
    """
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        api_key = auth_header[7:]
        return f"{prefix}{api_key[:16]}" if prefix else api_key[:16]
    return get_remote_address(request)


@lru_cache(maxsize=1)
def _get_storage_uri() -> str:
    """Get Redis storage URI for rate limiting."""
    redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    return redis_url


def _create_limiter() -> Limiter:
    """Create limiter with Redis backend."""
    return Limiter(
        key_func=get_rate_limit_key,
        storage_uri=_get_storage_uri(),
        default_limits=[f"{settings.RATE_LIMIT_RPM}/minute"],
    )


limiter = _create_limiter()


def get_rate_limit_per_partner(partner_id: str) -> list[str]:
    """Get rate limit for a specific partner."""
    return [f"{settings.RATE_LIMIT_RPM}/minute"]


def get_rate_limit_per_endpoint(endpoint: str) -> list[str]:
    """Get rate limit for specific endpoint type."""
    limits = {
        "GET": [f"{settings.RATE_LIMIT_RPM}/minute"],
        "POST": [f"{settings.RATE_LIMIT_MESSAGES_PM}/minute"],
    }
    return limits.get(endpoint, [f"{settings.RATE_LIMIT_RPM}/minute"])


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Custom rate limit exceeded handler."""
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "RATE_LIMITED",
                "message": "Rate limit exceeded",
                "details": {
                    "retry_after": exc.detail,
                },
            }
        },
        headers={
            "X-RateLimit-Limit": str(exc.limit),
            "X-RateLimit-Remaining": "0",
            "Retry-After": str(exc.detail),
        },
    )
