"""V1 API router."""

from fastapi import APIRouter

from app.api.v1 import content, health, sessions

router = APIRouter(prefix="/v1")

router.include_router(health.router, tags=["health"])
router.include_router(content.router, tags=["content"])
router.include_router(sessions.router, tags=["sessions"])
