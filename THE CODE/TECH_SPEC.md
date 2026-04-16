# TECH_SPEC.md

This file contains the exact contracts the agent must implement. Do not deviate. If a contract needs to change, propose the change first.

---

## Mode 1: Just-In-Time Content Delivery

This document describes Mode 1 architecture, where partners send lesson content inline with each session creation request. Content exists only for the lifetime of the session.

---

## Tech Stack (locked in for v0.1)

- **Language:** Python 3.12+
- **Web framework:** FastAPI 0.115+
- **Server:** Uvicorn (production: with `--workers 2`)
- **Database:** PostgreSQL 16 + pgvector 0.7+
- **ORM:** SQLAlchemy 2.0+ (async)
- **Migrations:** Alembic
- **DB driver:** asyncpg
- **Validation:** Pydantic 2.x
- **LLM SDK:** `google-genai` (the new unified Gemini SDK)
- **HTTP retries:** tenacity
- **Rate limiting:** slowapi
- **Logging:** structlog
- **Testing:** pytest + pytest-asyncio + httpx
- **Linting:** ruff (replaces flake8 + black)
- **Type checking:** mypy
- **Package management:** uv (faster than pip)
- **Containerization:** Docker + Docker Compose
- **Background jobs:** APScheduler

---

## Key Architectural Differences from Mode 2

| Aspect | Mode 2 (Pre-Ingestion) | Mode 1 (Just-In-Time) |
|--------|------------------------|-----------------------|
| Content upload | Separate `/v1/content/ingest` call | Inline with session create |
| Content storage | Persistent `content_items` table | Session-scoped `session_chunks` |
| Content lifetime | Until explicitly deleted | Until session expires |
| Session creation | ~50ms | ~1.5s (first use), ~50ms (cached) |
| Embedding | At ingest time | At session creation |
| Cache | None | `embedding_cache` shareable across sessions |

---

## Project Directory Structure

```
neuro-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app entry point
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py                # FastAPI dependencies (auth, db)
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py         # v1 router
│   │       ├── sessions.py      # Session endpoints (no content.py)
│   │       ├── health.py
│   │       └── admin.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── tutor.py             # Tutor Engine
│   │   ├── chunking.py         # Text chunking
│   │   ├── file_processor.py  # File extraction
│   │   └── scheduler.py       # Background jobs
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py             # Declarative base
│   │   ├── session.py         # Async engine + session factory
│   │   ├── models.py          # SQLAlchemy ORM models
│   │   └── repositories/
│   │       ├── __init__.py
│   │       ├── partner_repo.py
│   │       ├── session_repo.py
│   │       ├── message_repo.py
│   │       └── usage_repo.py
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py          # Gemini client (generation + embeddings)
│   │   └── prompts.py        # System prompts
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py         # Pydantic Settings
│   │   ├── auth.py         # API key validation
│   │   ├── rate_limit.py
│   │   ├── logging.py      # structlog setup
│   │   └── errors.py      # Custom exceptions + handlers
│   │
│   └── schemas/
│       ├── __init__.py
│       └── common.py     # Shared response types
│
├── alembic/
│   ├── versions/         # Migration files
│   ├── env.py
│   └── script.py.mako
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_sessions.py
│   └── test_tutor_e2e.py
│
├── .env.example
├── .gitignore
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── ruff.toml
```

---

## Database Schema

### Extension setup (in first migration)

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

### Tables

**partners**
```sql
CREATE TABLE partners (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    api_key_hash TEXT UNIQUE NOT NULL,
    api_key_prefix TEXT NOT NULL,
    contact_email TEXT NOT NULL,
    rate_limit_rpm INTEGER NOT NULL DEFAULT 1000,
    rate_limit_messages_pm INTEGER NOT NULL DEFAULT 100,
    allowed_origins TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_partners_api_key_hash ON partners(api_key_hash);
```

**session_chunks** (session-scoped, auto-cleanup on session delete)
```sql
CREATE TABLE session_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    text TEXT NOT NULL,
    embedding vector(768) NOT NULL,
    token_count INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_session_chunks_session ON session_chunks(session_id);
CREATE INDEX idx_session_chunks_partner ON session_chunks(partner_id);

CREATE INDEX idx_session_chunks_embedding ON session_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

**embedding_cache** (shared across sessions)
```sql
CREATE TABLE embedding_cache (
    id BIGSERIAL PRIMARY KEY,
    content_hash TEXT NOT NULL UNIQUE,
    chunks JSONB NOT NULL,
    total_tokens INTEGER NOT NULL,
    hit_count INTEGER NOT NULL DEFAULT 1,
    first_cached_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_embedding_cache_last_used ON embedding_cache(last_used_at);
```

**sessions** (content now inline)
```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
    student_external_id TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'lt',
    metadata JSONB NOT NULL DEFAULT '{}',
    content_title TEXT,
    content_subject TEXT,
    content_fingerprint TEXT,
    content_length INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_message_at TIMESTAMPTZ
);

CREATE INDEX idx_sessions_partner ON sessions(partner_id);
CREATE INDEX idx_sessions_partner_student ON sessions(partner_id, student_external_id);
```

**messages**
```sql
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('student', 'tutor', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    retrieved_chunk_ids TEXT,
    prompt_tokens INTEGER,
    completion_tokens INTEGER
);

CREATE INDEX idx_messages_session ON messages(session_id, created_at);
CREATE INDEX idx_messages_partner ON messages(partner_id);
```

**usage_events**
```sql
CREATE TABLE usage_events (
    id BIGSERIAL PRIMARY KEY,
    partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    student_external_id TEXT,
    session_id UUID,
    model_name TEXT NOT NULL,
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    duration_ms INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_usage_partner_time ON usage_events(partner_id, created_at);
```

---

## API Specification

All endpoints prefixed with `/v1`. All requests require `Authorization: Bearer <api_key>` header.

### POST /v1/sessions (Mode 1 - Just-In-Time Content)

Create a new tutoring session with inline content.

**Request:**
```json
{
  "student_external_id": "student-12345",
  "title": "Kvadratinės lygtys — praktika",
  "language": "lt",
  "metadata": {
    "grade_level": 9,
    "curriculum": "BUP-2025"
  },
  "content": {
    "mode": "inline",
    "title": "Kvadratinės lygtys",
    "subject": "mathematics",
    "text": "# Kvadratinės lygtys\n\nKvadratinė lygtis yra..."
  }
}
```

**Validation:**
- `student_external_id`: required, 1–256 chars
- `title`: required, 1–512 chars
- `language`: required, ISO 639-1 (must be "lt" or "en")
- `content.mode`: required, must be "inline"
- `content.title`: required, 1–512 chars
- `content.subject`: optional, max 64 chars
- `content.text`: required, 50–100,000 chars

**Response (201):**
```json
{
  "data": {
    "session_id": "uuid-here",
    "language": "lt",
    "created_at": "2026-04-15T10:30:00Z",
    "content_fingerprint": "sha256-first-16",
    "chunks_created": 12,
    "embedding_cache_hit": false,
    "processing_ms": 1340
  }
}
```

**Behavior:**
1. Validate + normalize content (strip whitespace, collapse newlines)
2. Compute content_hash = sha256(normalized_text)
3. Check embedding_cache:
   - HIT: load cached chunks (~50ms)
   - MISS: chunk + embed via Gemini (~1.5s), store in cache
4. Insert session row
5. Insert session_chunks linked to session_id
6. Return session details

---

### POST /v1/sessions/{session_id}/messages

Send a student message and get streaming AI response.

**Path params:** session_id

**Request:**
```json
{
  "content": "Kaip spręsti x² - 4 = 0?"
}
```

**Response:** Server-Sent Events stream

---

### GET /v1/sessions/{session_id}

Retrieve session metadata and message history.

---

### DELETE /v1/sessions/{session_id}

End and remove a tutoring session. Cascades to delete session_chunks and messages.

---

## Content Lifecycle in Mode 1

1. **Session Creation** - Partner sends content inline
2. **Embedding** - Content is chunked and embedded (or loaded from cache)
3. **Session Active** - Student can chat with AI grounded in content
4. **Session Expiration** - After 24 hours of inactivity, session auto-deletes
5. **Cleanup** - All session_chunks and messages are cascade-deleted
6. **Cache Persistence** - Embedding cache retains data for 30 days

### Auto-Expiration CRON

- **Sessions without activity for 24 hours** → auto-delete
- **Sessions never messaged for 2 hours** → auto-delete
- Runs nightly at 2:00 AM UTC

### Embedding Cache Cleanup CRON

- **Cache entries** where last_used_at > 30 days AND hit_count < 2 → purge
- Runs weekly on Sundays at 3:00 AM UTC

---

## Error Codes

| Code | HTTP | Meaning |
|---|---|---|
| `CONTENT_TOO_LARGE` | 400 | Content exceeds 100,000 chars |
| `CONTENT_TOO_SHORT` | 400 | Content under 50 chars |
| `SESSION_NOT_FOUND` | 404 | session_id doesn't exist |
| `RATE_LIMITED` | 429 | Partner rate limit exceeded |
| `VALIDATION_ERROR` | 422 | Pydantic validation failed |
| `MISSING_AUTH` | 401 | No Authorization header |
| `INVALID_API_KEY` | 401 | API key not recognized |
| `PARTNER_INACTIVE` | 401 | Partner account disabled |
| `LLM_UNAVAILABLE` | 503 | Gemini API failed |
| `EMBEDDING_FAILED` | 503 | Embedding API failed |

---

## Configuration Settings

```python
# Session content limits
SESSION_CONTENT_MAX_LENGTH = 100000      # chars per session
SESSION_CONTENT_MIN_LENGTH = 50            # chars - anything shorter is a bug

# Auto-expiration
SESSION_AUTO_EXPIRE_INACTIVE_HOURS = 24
SESSION_AUTO_EXPIRE_NEVER_USED_HOURS = 2

# Embedding cache
EMBEDDING_CACHE_TTL_DAYS = 30
EMBEDDING_CACHE_MAX_ROWS = 100000
```

---

## Observability

Per-session creation metrics:
- `session.create.cache_hit` (boolean)
- `session.create.content_length_chars`
- `session.create.chunks_produced`
- `session.create.embedding_ms` (only on cache miss)
- `session.create.total_ms`
- `session.create.partner_id`