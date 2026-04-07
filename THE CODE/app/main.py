"""FastAPI application entry point."""

from fastapi import FastAPI, Request

from app.api.v1.router import router as v1_router
from app.core import configure_logging
from app.core.errors import NeuroError, neuro_exception_handler
from app.core.rate_limit import limiter

configure_logging()

app = FastAPI(
    title="Neuropetitorius API",
    description="B2B AI tutoring API",
    version="0.1.0",
)

app.state.limiter = limiter


@app.exception_handler(NeuroError)
async def neuro_error_handler(request: Request, exc: NeuroError):
    return await neuro_exception_handler(request, exc)


app.include_router(v1_router)
