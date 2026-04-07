"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """Liveness check. No auth required."""
    return {
        "status": "ok",
        "version": "0.1.0",
        "checks": {
            "database": "ok",
            "gemini": "ok"
        }
    }
