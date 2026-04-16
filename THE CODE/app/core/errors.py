"""Custom exceptions and error handlers."""

from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.schemas.common import ErrorDetail, ErrorResponse


class NeuroError(Exception):
    """Base exception for Neuropetitorius."""

    def __init__(self, code: str, message: str, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


class MissingAuthError(NeuroError):
    def __init__(self):
        super().__init__(
            code="MISSING_AUTH",
            message="Authorization header is required",
        )


class InvalidApiKeyError(NeuroError):
    def __init__(self):
        super().__init__(
            code="INVALID_API_KEY",
            message="The provided API key is not valid",
        )


class PartnerInactiveError(NeuroError):
    def __init__(self):
        super().__init__(
            code="PARTNER_INACTIVE",
            message="Partner account is inactive",
        )


class ForbiddenResourceError(NeuroError):
    def __init__(self):
        super().__init__(
            code="FORBIDDEN_RESOURCE",
            message="You do not have access to this resource",
        )


class ResourceNotFoundError(NeuroError):
    def __init__(self, resource_type: str = "Resource"):
        super().__init__(
            code="RESOURCE_NOT_FOUND",
            message=f"{resource_type} not found",
        )


class RateLimitedError(NeuroError):
    def __init__(self, retry_after: int | None = None):
        super().__init__(
            code="RATE_LIMITED",
            message="Rate limit exceeded",
            details={"retry_after": retry_after} if retry_after else None,
        )


class ValidationError(NeuroError):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            details=details,
        )


class ContentTooLargeError(NeuroError):
    def __init__(self):
        super().__init__(
            code="CONTENT_TOO_LARGE",
            message="Content exceeds maximum allowed size",
        )


class ContentTooShortError(NeuroError):
    def __init__(self):
        super().__init__(
            code="CONTENT_TOO_SHORT",
            message="Content is too short to be a valid lesson",
        )


class TopicNotFoundError(NeuroError):
    def __init__(self):
        super().__init__(
            code="TOPIC_NOT_FOUND",
            message="Topic does not exist for this partner",
        )


class SessionNotFoundError(NeuroError):
    def __init__(self):
        super().__init__(
            code="SESSION_NOT_FOUND",
            message="Session not found",
        )


class LlmUnavailableError(NeuroError):
    def __init__(self):
        super().__init__(
            code="LLM_UNAVAILABLE",
            message="Tutor temporarily unavailable, please try again",
        )


class LlmTimeoutError(NeuroError):
    def __init__(self):
        super().__init__(
            code="LLM_TIMEOUT",
            message="Tutor request timed out",
        )


class EmbeddingFailedError(NeuroError):
    def __init__(self):
        super().__init__(
            code="EMBEDDING_FAILED",
            message="Failed to process request",
        )


async def neuro_exception_handler(request: Request, exc: NeuroError) -> JSONResponse:
    """Handle NeuroError and return proper JSON error response."""
    status_code = _get_status_code(exc.code)
    error_detail = ErrorDetail(
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(error=error_detail).model_dump(),
    )


def _get_status_code(code: str) -> int:
    """Map error code to HTTP status code."""
    mapping = {
        "MISSING_AUTH": status.HTTP_401_UNAUTHORIZED,
        "INVALID_API_KEY": status.HTTP_401_UNAUTHORIZED,
        "PARTNER_INACTIVE": status.HTTP_401_UNAUTHORIZED,
        "FORBIDDEN_RESOURCE": status.HTTP_403_FORBIDDEN,
        "RESOURCE_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "RATE_LIMITED": status.HTTP_429_TOO_MANY_REQUESTS,
        "VALIDATION_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "CONTENT_TOO_LARGE": status.HTTP_400_BAD_REQUEST,
        "CONTENT_TOO_SHORT": status.HTTP_400_BAD_REQUEST,
        "TOPIC_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "SESSION_NOT_FOUND": status.HTTP_404_NOT_FOUND,
        "LLM_UNAVAILABLE": status.HTTP_503_SERVICE_UNAVAILABLE,
        "LLM_TIMEOUT": status.HTTP_503_SERVICE_UNAVAILABLE,
        "EMBEDDING_FAILED": status.HTTP_503_SERVICE_UNAVAILABLE,
        "INVALID_REQUEST": status.HTTP_400_BAD_REQUEST,
        "INTERNAL_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
    }
    return mapping.get(code, status.HTTP_500_INTERNAL_SERVER_ERROR)
