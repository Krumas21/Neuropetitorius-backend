"""Content ingestion endpoint."""

import hashlib
import uuid

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel, Field

from app.api.deps import CurrentPartnerDep, DbSession
from app.db.repositories import content_repo
from app.llm.client import llm_client
from app.services.chunking import chunking_service
from app.services.file_processor import file_processor

router = APIRouter()


class IngestContentRequest(BaseModel):
    topic_id: str = Field(..., max_length=256)
    title: str = Field(..., max_length=512)
    subject: str | None = Field(None, max_length=64)
    language: str = Field(default="lt", max_length=10)


class IngestContentResponse(BaseModel):
    topic_id: str
    content_item_id: uuid.UUID
    chunks_created: int
    tokens_embedded: int
    content_changed: bool
    file_processed: str | None = None


@router.post("/content/ingest", response_model=IngestContentResponse)
async def ingest_content(
    db: DbSession,
    partner: CurrentPartnerDep,
    topic_id: str = Form(..., max_length=256),
    title: str = Form(..., max_length=512),
    class_id: str | None = Form(None, max_length=64),
    class_name: str | None = Form(None, max_length=128),
    subject: str | None = Form(None, max_length=64),
    chapter: str | None = Form(None, max_length=256),
    language: str = Form(default="lt", max_length=10),
    content: str | None = Form(None, min_length=10, max_length=500000),
    file: UploadFile | None = File(None),
) -> IngestContentResponse:
    """Upload or update lesson content for a topic.

    Accepts either:
    - Plain text content in 'content' field
    - File upload in 'file' field (PDF, DOCX, XLSX, TXT, images)
    - Both (file content will be used in addition to text content)
    """
    file_processed = None

    # Handle file upload
    if file:
        file_content = await file.read()
        extracted_text = file_processor.extract_text(file_content, file.filename or "unknown")
        file_processed = file.filename

        # If both content and file provided, concatenate them
        if content:
            content = f"{content}\n\n--- File: {file.filename} ---\n{extracted_text}"
        else:
            content = extracted_text

    # Ensure we have content to process
    if not content or not content.strip():
        raise ValueError("Either 'content' or 'file' is required")

    content_hash = hashlib.sha256(content.encode()).hexdigest()

    content_item, is_new = await content_repo.upsert(
        db,
        partner_id=uuid.UUID(partner.id),
        topic_id=topic_id,
        title=title,
        class_id=class_id,
        class_name=class_name,
        subject=subject,
        chapter=chapter,
        language=language,
        raw_content=content,
        content_hash=content_hash,
    )

    if not is_new and content_item.content_hash == content_hash:
        return IngestContentResponse(
            topic_id=topic_id,
            content_item_id=content_item.id,
            chunks_created=0,
            tokens_embedded=0,
            content_changed=False,
            file_processed=file_processed,
        )

    await content_repo.delete_chunks_by_content_item(db, content_item.id)

    chunks = chunking_service.chunk_text(content)

    chunks_data = []
    total_tokens = 0

    for chunk in chunks:
        embedding = llm_client.get_embedding(chunk["text"])

        embedding_str = "[" + ",".join(map(str, embedding)) + "]"

        chunks_data.append(
            {
                "id": uuid.uuid4(),
                "partner_id": uuid.UUID(partner.id),
                "content_item_id": content_item.id,
                "chunk_index": chunk["chunk_index"],
                "text": chunk["text"],
                "embedding": embedding_str,
                "token_count": chunk["token_count"],
            }
        )
        total_tokens += chunk["token_count"]

    await content_repo.insert_chunks(db, chunks_data)

    return IngestContentResponse(
        topic_id=topic_id,
        content_item_id=content_item.id,
        chunks_created=len(chunks),
        tokens_embedded=total_tokens,
        content_changed=True,
        file_processed=file_processed,
    )


@router.delete("/content/{topic_id}")
async def delete_content(
    topic_id: str,
    db: DbSession,
    partner: CurrentPartnerDep,
) -> dict:
    """Remove lesson content for a topic."""
    deleted = await content_repo.delete(
        db,
        partner_id=uuid.UUID(partner.id),
        topic_id=topic_id,
    )

    if not deleted:
        return {"message": "Content not found"}

    return {"message": "Content deleted"}


@router.get("/content")
async def list_content(
    db: DbSession,
    partner: CurrentPartnerDep,
    class_id: str | None = None,
    class_name: str | None = None,
    subject: str | None = None,
    chapter: str | None = None,
    topic_id: str | None = None,
    limit: int = 50,
) -> dict:
    """List content with optional filters."""
    items = await content_repo.list_by_partner(
        db,
        partner_id=uuid.UUID(partner.id),
        class_id=class_id,
        class_name=class_name,
        subject=subject,
        chapter=chapter,
        topic_id=topic_id,
        limit=limit,
    )
    return {
        "content_items": [
            {
                "topic_id": item.topic_id,
                "title": item.title,
                "class_id": item.class_id,
                "class_name": item.class_name,
                "subject": item.subject,
                "chapter": item.chapter,
                "language": item.language,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ]
    }
