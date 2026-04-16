"""Tutor Engine - Core AI tutoring logic."""

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime

from app.core.config import settings
from app.db.repositories import message_repo, session_repo, usage_repo
from app.llm.client import llm_client
from app.llm.prompts import get_system_prompt


class TutorEngine:
    """Core tutoring engine with RAG and streaming."""

    async def process_message(
        self,
        db,
        partner_id: uuid.UUID,
        session_id: uuid.UUID,
        student_external_id: str,
        message_content: str,
    ) -> dict:
        """Process a student message and return AI response."""
        start_time = datetime.utcnow()

        session = await session_repo.get_by_id(db, partner_id, session_id)
        if not session:
            raise ValueError("Session not found")

        query_embedding = await llm_client.get_embedding(message_content)

        chunks = await session_repo.search_session_chunks(
            db,
            partner_id=partner_id,
            session_id=session_id,
            query_embedding=query_embedding,
            top_k=settings.RETRIEVAL_TOP_K,
        )

        context = self._build_context(chunks)
        system_prompt = get_system_prompt(language=session.language, lesson_context=context)
        prompt = self._build_prompt(context, message_content)

        response_text = await llm_client.generate_text(
            prompt=prompt,
            system_instruction=system_prompt,
            temperature=0.7,
        )

        _message = await message_repo.create(
            db,
            partner_id=partner_id,
            session_id=session_id,
            role="student",
            content=message_content,
            retrieved_chunk_ids=[str(c["id"]) for c in chunks],
        )

        tutor_message = await message_repo.create(
            db,
            partner_id=partner_id,
            session_id=session_id,
            role="tutor",
            content=response_text,
            prompt_tokens=await llm_client.count_tokens(prompt),
            completion_tokens=await llm_client.count_tokens(response_text),
        )

        await session_repo.update_last_message(db, session_id)

        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        await usage_repo.log_event(
            db,
            partner_id=partner_id,
            event_type="chat_message",
            model_name=settings.GEMINI_GENERATION_MODEL,
            prompt_tokens=tutor_message.prompt_tokens or 0,
            completion_tokens=tutor_message.completion_tokens or 0,
            duration_ms=duration_ms,
            student_external_id=student_external_id,
            session_id=session_id,
        )

        return {
            "message_id": tutor_message.id,
            "content": response_text,
            "role": "tutor",
            "created_at": tutor_message.created_at.isoformat(),
        }

    async def process_message_stream(
        self,
        db,
        partner_id: uuid.UUID,
        session_id: uuid.UUID,
        student_external_id: str,
        message_content: str,
    ) -> AsyncGenerator[str, None]:
        """Process a student message with streaming response."""
        start_time = datetime.utcnow()

        session = await session_repo.get_by_id(db, partner_id, session_id)
        if not session:
            raise ValueError("Session not found")

        query_embedding = await llm_client.get_embedding(message_content)

        chunks = await session_repo.search_session_chunks(
            db,
            partner_id=partner_id,
            session_id=session_id,
            query_embedding=query_embedding,
            top_k=settings.RETRIEVAL_TOP_K,
        )

        context = self._build_context(chunks)
        system_prompt = get_system_prompt(language=session.language, lesson_context=context)
        prompt = self._build_prompt(context, message_content)

        _message = await message_repo.create(
            db,
            partner_id=partner_id,
            session_id=session_id,
            role="student",
            content=message_content,
            retrieved_chunk_ids=[str(c["id"]) for c in chunks],
        )

        full_response = ""
        async for chunk in self._stream_response(prompt, system_prompt):
            full_response += chunk
            yield chunk

        tutor_message = await message_repo.create(
            db,
            partner_id=partner_id,
            session_id=session_id,
            role="tutor",
            content=full_response,
            prompt_tokens=await llm_client.count_tokens(prompt),
            completion_tokens=await llm_client.count_tokens(full_response),
        )

        await session_repo.update_last_message(db, session_id)

        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        await usage_repo.log_event(
            db,
            partner_id=partner_id,
            event_type="chat_message",
            model_name=settings.GEMINI_GENERATION_MODEL,
            prompt_tokens=tutor_message.prompt_tokens or 0,
            completion_tokens=tutor_message.completion_tokens or 0,
            duration_ms=duration_ms,
            student_external_id=student_external_id,
            session_id=session_id,
        )

    def _build_context(self, chunks: list) -> str:
        """Build context string from retrieved chunks."""
        if not chunks:
            return "No relevant content found."

        context_parts = ["Relevant lesson content:\n"]
        for i, chunk in enumerate(chunks, 1):
            context_parts.append(f"\n--- Section {i} ---\n{chunk['text']}")

        return "\n".join(context_parts)

    def _build_prompt(self, context: str, question: str) -> str:
        """Build the full prompt with context and question."""
        return f"""{context}

---

Student question: {question}

Your response:"""

    async def _stream_response(self, prompt: str, system_prompt: str) -> AsyncGenerator[str, None]:
        """Stream response from LLM."""
        async for chunk in llm_client.generate_content_stream(
            prompt=prompt,
            system_instruction=system_prompt,
            temperature=0.7,
        ):
            yield chunk


tutor_engine = TutorEngine()
