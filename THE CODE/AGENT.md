# AGENT.md

You are building the **Neuropetitorius AI Tutor Backend MVP v0.1** — a B2B API service that provides AI-powered tutoring functionality to educational platforms (e.g. Edukamentas, Eduka) as a drop-in service. Partners upload their lesson content; we provide grounded conversational tutoring on top of it.

This file is your constitution. Read it before every significant task. The other files (`PROJECT.md`, `ARCHITECTURE.md`, `TECH_SPEC.md`, `PROMPTS.md`, `TASKS.md`) provide depth.

---

## Mission

Build a small, reliable, production-quality MVP. Three endpoints. One job: answer student questions using ONLY the partner's uploaded content. Nothing else matters in v0.1.

**Success criteria for MVP v0.1:**
1. A partner can upload a lesson via API
2. A student can chat with the AI about that lesson
3. The AI's response is grounded in the actual lesson content (not Gemini's general knowledge)
4. Conversation history is persisted per session
5. The whole thing runs on a single small server in EU region

That's it. No memory consolidation, no quizzes, no analytics, no knowledge graphs. Resist scope creep ruthlessly.

---

## Core Principles

**1. Reliability over cleverness.**
A boring API that works 99% of the time beats a brilliant API that works 70%. Choose proven patterns. Use battle-tested libraries. Don't invent.

**2. Grounding is non-negotiable.**
Every AI response must be traceable to ingested content. If the retrieved chunks don't contain the answer, the AI must say "I don't have that information in your lesson — let me check with your teacher" and stop. Hallucination is worse than not answering.

**3. Multi-tenant from day one.**
Every database row carries a `partner_id`. Every API call is authenticated as a partner. No exceptions. We will sell to multiple platforms; data isolation is critical.

**4. EU data residency.**
All compute, all storage, all LLM calls happen in the EU region. Use Gemini API with EU region endpoint. Host on Hetzner Cloud (Falkenstein/Helsinki) or similar. This is a hard sales requirement for school partners.

**5. Cost-conscious.**
Use Gemini Flash, not Pro. Cache embeddings. Cache common queries. Track token usage per partner from day one — it's how we'll bill them later.

**6. Lithuanian + English from day one.**
The MVP must work in both languages. Gemini handles Lithuanian well but test it. The system prompts in PROMPTS.md include language detection.

---

## What You Are Building (and What You Are Not)

### YES — Build these in MVP v0.1:
- Content ingestion endpoint (text/markdown only, no PDFs yet)
- Embedding pipeline (Gemini embeddings → pgvector)
- Tutor chat endpoint with SSE streaming
- Session/message persistence
- Partner API key authentication
- Per-partner rate limiting
- Token usage tracking
- Basic health check endpoint
- Database migrations
- Docker setup for deployment

### NO — Do NOT build these in v0.1:
- Persistent student memory (just session history)
- Knowledge graph
- Misconception tracking
- Quiz generation
- Flashcard generation
- Adaptive difficulty
- Webhooks
- Analytics dashboard
- Embeddable widget
- White-label theming
- Multiple LLM providers (Gemini only)
- PDF parsing (text only)
- Re-ranking models
- Complex chunking strategies (simple recursive splitter is fine)
- User-facing UI (this is an API service)

If you find yourself wanting to add something not on the YES list, **stop and ask**. Scope creep is the #1 risk.

---

## Working Style

- **Read all docs in `/docs` before starting any task.** Especially `TECH_SPEC.md` for schemas and `PROMPTS.md` for LLM prompts.
- **Never invent API contracts.** They're defined in `TECH_SPEC.md`. If you need to change one, propose the change first.
- **Write tests as you go.** Pytest. At minimum: one test per endpoint covering happy path + auth failure + validation error. Don't aim for 100% coverage; aim for confidence.
- **Commit small, commit often.** Each commit should be one logical change with a clear message.
- **No silent failures.** Every error path must log structured error data and return a meaningful HTTP status.
- **No magic numbers.** Constants go in `app/config.py`.
- **No raw SQL strings scattered through code.** Use SQLAlchemy ORM or a single `app/db/queries.py` file.
- **Type hints everywhere.** This is Python 3.12+. Use them.
- **Async everywhere.** FastAPI is async. The Gemini client supports async. Don't mix sync and async.

---

## When You Get Stuck

Ask in this order:
1. Check `PROJECT.md` for the why
2. Check `ARCHITECTURE.md` for the how
3. Check `TECH_SPEC.md` for the exact contract
4. Check `PROMPTS.md` for LLM-related questions
5. Check `TASKS.md` to see if it's a future milestone (not your problem yet)
6. Then ask the user

---

## Hard Constraints

- **Never** put API keys, partner secrets, or student data in logs
- **Never** call the Gemini API without retry + timeout (use tenacity)
- **Never** return Gemini errors directly to the client (translate to clean HTTP errors)
- **Never** trust partner-supplied IDs without verifying ownership (e.g. session_id must belong to this partner_id)
- **Never** load entire lesson content into the LLM context — always retrieve top-K chunks via vector search
- **Never** skip the migration step when changing the database schema
- **Always** use parameterized queries (we use SQLAlchemy, this is automatic — but never f-string SQL)
- **Always** validate request bodies with Pydantic
- **Always** include the partner_id in every database query as a WHERE clause (row-level isolation)

---

## Definition of Done for MVP v0.1

Before we call MVP v0.1 complete, all of these must be true:

- [ ] All endpoints in `TECH_SPEC.md` are implemented and tested
- [ ] Database migrations run cleanly from a fresh Postgres instance
- [ ] Docker Compose spins up the whole stack in one command
- [ ] A README.md shows how to run locally and how to call each endpoint with curl
- [ ] At least one end-to-end test exists: ingest content → start session → send message → verify grounded response
- [ ] Token usage is tracked per partner per request
- [ ] Rate limiting works (returns 429 when exceeded)
- [ ] Authentication works (returns 401 when missing/invalid API key)
- [ ] Logs are structured JSON (not plain text)
- [ ] No secrets in the repo (use `.env`, provide `.env.example`)
- [ ] Deployed to a staging server in EU and tested with a real Gemini API call