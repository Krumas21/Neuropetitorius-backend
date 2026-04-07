"""Session management endpoints."""

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.deps import CurrentPartnerDep, DbSession
from app.core.errors import SessionNotFoundError, TopicNotFoundError
from app.db.repositories import content_repo, message_repo, session_repo

router = APIRouter()


class CreateSessionRequest(BaseModel):
    student_external_id: str = Field(..., max_length=256)
    topic_id: str = Field(..., max_length=256)
    language: str = Field(default="lt", max_length=10)
    metadata: dict = Field(default_factory=dict)


class SessionResponse(BaseModel):
    session_id: uuid.UUID
    topic_id: str
    language: str
    created_at: datetime


class MessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)


class MessageResponse(BaseModel):
    message_id: uuid.UUID
    content: str
    role: str
    created_at: datetime


class SessionDetailResponse(BaseModel):
    session_id: uuid.UUID
    topic_id: str
    student_external_id: str
    language: str
    created_at: datetime
    last_message_at: datetime | None
    messages: list[dict[str, Any]]


@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    request: CreateSessionRequest,
    db: DbSession,
    partner: CurrentPartnerDep,
) -> SessionResponse:
    """Create a new tutoring session."""
    content_item = await content_repo.get_by_topic_id(
        db,
        partner_id=uuid.UUID(partner.id),
        topic_id=request.topic_id,
    )

    if not content_item:
        raise TopicNotFoundError()

    session = await session_repo.create(
        db,
        partner_id=uuid.UUID(partner.id),
        student_external_id=request.student_external_id,
        topic_id=request.topic_id,
        language=request.language,
        metadata=request.metadata,
    )

    return SessionResponse(
        session_id=session.id,
        topic_id=session.topic_id,
        language=session.language,
        created_at=session.created_at,
    )


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: str,
    db: DbSession,
    partner: CurrentPartnerDep,
) -> SessionDetailResponse:
    """Retrieve session metadata and message history."""
    session = await session_repo.get_by_id(
        db,
        partner_id=uuid.UUID(partner.id),
        session_id=uuid.UUID(session_id),
    )

    if not session:
        raise SessionNotFoundError()

    messages = await message_repo.get_by_session(
        db,
        partner_id=uuid.UUID(partner.id),
        session_id=session.id,
        limit=50,
    )

    return SessionDetailResponse(
        session_id=session.id,
        topic_id=session.topic_id,
        student_external_id=session.student_external_id,
        language=session.language,
        created_at=session.created_at,
        last_message_at=session.last_message_at,
        messages=[
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    )


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    db: DbSession,
    partner: CurrentPartnerDep,
) -> dict:
    """End and remove a tutoring session."""
    deleted = await session_repo.delete(
        db,
        partner_id=uuid.UUID(partner.id),
        session_id=uuid.UUID(session_id),
    )

    if not deleted:
        raise SessionNotFoundError()

    return {"message": "Session deleted"}


@router.post("/sessions/{session_id}/messages", response_model=MessageResponse)
async def send_message(
    session_id: str,
    request: MessageRequest,
    db: DbSession,
    partner: CurrentPartnerDep,
) -> MessageResponse:
    """Send a student message and get AI response."""
    from app.services.tutor import tutor_engine

    session = await session_repo.get_by_id(
        db,
        partner_id=uuid.UUID(partner.id),
        session_id=uuid.UUID(session_id),
    )

    if not session:
        raise SessionNotFoundError()

    result = await tutor_engine.process_message(
        db=db,
        partner_id=uuid.UUID(partner.id),
        session_id=session.id,
        student_external_id=session.student_external_id,
        message_content=request.content,
    )

    return MessageResponse(
        message_id=result["message_id"],
        content=result["content"],
        role=result["role"],
        created_at=datetime.fromisoformat(result["created_at"]),
    )
