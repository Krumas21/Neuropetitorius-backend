"""V1 API router."""

from fastapi import APIRouter

from app.api.v1 import health, sessions, admin

router = APIRouter(prefix="/v1")

router.include_router(health.router, tags=["health"])
router.include_router(sessions.router, tags=["sessions"])
router.include_router(admin.router, tags=["admin"])
