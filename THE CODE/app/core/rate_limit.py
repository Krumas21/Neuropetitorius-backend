"""Rate limiting using slowapi."""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

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


limiter = Limiter(
    key_func=get_rate_limit_key,
    storage_uri="memory://",
    default_limits=[f"{settings.RATE_LIMIT_RPM}/minute"],
)


def get_rate_limit_per_partner(partner_id: str) -> list[str]:
    """Get rate limit for a specific partner."""
    return [f"{settings.RATE_LIMIT_RPM}/minute"]
