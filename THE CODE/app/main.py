"""FastAPI application entry point."""

import logging
import time
import uuid
from contextlib import asynccontextmanager

import sentry_sdk
from sentry_sdk import Hub
from fastapi import FastAPI, Request
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from app.api.v1.router import router as v1_router
from app.core import configure_logging
from app.core.config import settings
from app.core.errors import NeuroError, neuro_exception_handler
from app.core.rate_limit import limiter, rate_limit_exceeded_handler
from app.services.scheduler import setup_scheduler
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)


def setup_sentry():
    """Initialize Sentry for error tracking."""
    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENV,
            integrations=[
                FastApiIntegration(),
                LoggingIntegration(
                    level=settings.LOG_LEVEL,
                    event_level="WARNING",
                ),
            ],
            traces_sample_rate=0.1,
            send_default_pii=False,
            before_send=lambda event, hint: event if settings.ENV == "production" else None,
        )
        return True
    return False


sentry_initialized = setup_sentry()
configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    startup_time = time.time()
    app.state.startup_time = startup_time
    app.state.git_sha = settings.ENV[:7] if len(settings.ENV) > 7 else settings.ENV

    if settings.ENV == "production":
        scheduler = setup_scheduler(app)
        scheduler.start()
        app.state.scheduler = scheduler
        logger.info("Started background scheduler")

    yield

    if hasattr(app.state, "scheduler"):
        app.state.scheduler.shutdown()

    if Hub.current_client:
        pass


app = FastAPI(
    title="Neuropetitorius API",
    description="B2B AI tutoring API",
    version="0.1.3",
    lifespan=lifespan,
)

app.state.limiter = limiter


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID to all requests for tracing."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(NeuroError)
async def neuro_error_handler(request: Request, exc: NeuroError):
    return await neuro_exception_handler(request, exc)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return await rate_limit_exceeded_handler(request, exc)


app.include_router(v1_router)
