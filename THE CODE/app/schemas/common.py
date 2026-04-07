"""Common response schemas."""

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
    request_id: str | None = None


class DataResponse(BaseModel):
    data: dict
    request_id: str | None = None
