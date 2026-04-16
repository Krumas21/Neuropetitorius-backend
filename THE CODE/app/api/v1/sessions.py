"""Session management endpoints."""

import uuid
import time
import hashlib
from datetime import datetime
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import CurrentPartnerDep, DbSession
from app.core.config import settings
from app.core.errors import SessionNotFoundError, ContentTooLargeError, ContentTooShortError
from app.db.models import EmbeddingCache, SessionChunk
from app.db.repositories import message_repo, session_repo
from app.llm.client import llm_client
from app.services.chunking import chunking_service
from app.services.tutor import tutor_engine

router = APIRouter()


class InlineContent(BaseModel):
    mode: str = Field(default="inline")
    title: str = Field(..., min_length=1, max_length=512)
    subject: str | None = Field(None, max_length=64)
    text: str = Field(..., min_length=1)


class CreateSessionRequest(BaseModel):
    student_external_id: str = Field(..., max_length=256)
    title: str = Field(..., min_length=1, max_length=512)
    language: str = Field(default="lt", max_length=10)
    metadata: dict = Field(default_factory=dict)
    content: InlineContent


class SessionResponse(BaseModel):
    session_id: uuid.UUID
    language: str
    created_at: datetime
    content_fingerprint: str
    chunks_created: int
    embedding_cache_hit: bool
    processing_ms: int


class MessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)


class MessageResponse(BaseModel):
    message_id: uuid.UUID
    content: str
    role: str
    created_at: datetime


class SessionDetailResponse(BaseModel):
    session_id: uuid.UUID
    student_external_id: str
    language: str
    created_at: datetime
    last_message_at: datetime | None
    messages: list[dict[str, Any]]


def normalize_content(text: str) -> str:
    """Normalize content text for consistent fingerprinting."""
    import re

    text = text.strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    import unicodedata

    text = unicodedata.normalize("NFC", text)
    return text


async def get_cached_embeddings(db, content_hash: str) -> list[dict] | None:
    """Check embedding cache for existing embeddings."""
    from sqlalchemy import update

    result = await db.execute(
        select(EmbeddingCache).where(EmbeddingCache.content_hash == content_hash)
    )
    cache_entry = result.scalar_one_or_none()

    if cache_entry:
        stmt = (
            update(EmbeddingCache)
            .where(EmbeddingCache.content_hash == content_hash)
            .values(hit_count=cache_entry.hit_count + 1, last_used_at=datetime.utcnow())
        )
        await db.execute(stmt)
        await db.commit()
        return cache_entry.chunks

    return None


async def store_in_cache(db, content_hash: str, chunks_data: list[dict], total_tokens: int) -> None:
    """Store embeddings in cache."""
    cache_entry = EmbeddingCache(
        content_hash=content_hash,
        chunks=chunks_data,
        total_tokens=total_tokens,
    )
    db.add(cache_entry)
    await db.commit()


@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    request: CreateSessionRequest,
    db: DbSession,
    partner: CurrentPartnerDep,
) -> SessionResponse:
    """Create a new tutoring session with inline content."""
    start_time = time.time()

    content_text = request.content.text
    content_title = request.content.title
    content_subject = request.content.subject

    if len(content_text) > settings.SESSION_CONTENT_MAX_LENGTH:
        raise ContentTooLargeError()

    if len(content_text) < settings.SESSION_CONTENT_MIN_LENGTH:
        raise ContentTooShortError()

    normalized_text = normalize_content(content_text)
    content_hash = hashlib.sha256(normalized_text.encode()).hexdigest()

    caching_hits = await get_cached_embeddings(db, content_hash)
    embedding_cache_hit = caching_hits is not None

    if embedding_cache_hit:
        chunks_data = caching_hits
    else:
        chunks = chunking_service.chunk_text(normalized_text)

        embeddings = llm_client.get_embeddings([c["text"] for c in chunks])

        chunks_data = []
        total_tokens = 0
        for chunk, embedding in zip(chunks, embeddings):
            chunks_data.append(
                {
                    "text": chunk["text"],
                    "embedding": embedding,
                    "token_count": chunk["token_count"],
                    "chunk_index": chunk["chunk_index"],
                }
            )
            total_tokens += chunk["token_count"]

        await store_in_cache(db, content_hash, chunks_data, total_tokens)

    partner_uuid = uuid.UUID(partner.id)

    session = await session_repo.create_with_content(
        db,
        partner_id=partner_uuid,
        student_external_id=request.student_external_id,
        title=request.title,
        language=request.language,
        metadata=request.metadata,
        content_title=content_title,
        content_subject=content_subject,
        content_fingerprint=content_hash[:16],
        content_length=len(content_text),
    )

    session_chunks_data = []
    for chunk_data in chunks_data:
        session_chunks_data.append(
            {
                "id": uuid.uuid4(),
                "partner_id": partner_uuid,
                "session_id": session.id,
                "chunk_index": chunk_data["chunk_index"],
                "text": chunk_data["text"],
                "embedding": chunk_data["embedding"],
                "token_count": chunk_data["token_count"],
            }
        )

    for chunk in session_chunks_data:
        db.add(SessionChunk(**chunk))
    await db.commit()

    processing_ms = int((time.time() - start_time) * 1000)

    return SessionResponse(
        session_id=session.id,
        language=session.language,
        created_at=session.created_at,
        content_fingerprint=content_hash[:16],
        chunks_created=len(chunks_data),
        embedding_cache_hit=embedding_cache_hit,
        processing_ms=processing_ms,
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
    """Send a student message and get AI response (non-streaming)."""
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


@router.post("/sessions/{session_id}/messages/stream")
async def send_message_stream(
    session_id: str,
    request: MessageRequest,
    db: DbSession,
    partner: CurrentPartnerDep,
) -> StreamingResponse:
    """Send a student message and get streaming AI response (SSE)."""
    session = await session_repo.get_by_id(
        db,
        partner_id=uuid.UUID(partner.id),
        session_id=uuid.UUID(session_id),
    )

    if not session:
        raise SessionNotFoundError()

    async def event_stream():
        full_content = ""
        try:
            async for chunk in tutor_engine.process_message_stream(
                db=db,
                partner_id=uuid.UUID(partner.id),
                session_id=session.id,
                student_external_id=session.student_external_id,
                message_content=request.content,
            ):
                full_content += chunk
                yield f"data: {chunk}\n\n"

            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
