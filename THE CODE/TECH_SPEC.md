# TECH_SPEC.md

This file contains the exact contracts the agent must implement. Do not deviate. If a contract needs to change, propose the change first.

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

---

## Project Directory Structure

```
neuro-backend/
├── docs/                          # The docs you are reading
│   ├── AGENT.md
│   ├── PROJECT.md
│   ├── ARCHITECTURE.md
│   ├── TECH_SPEC.md               # THIS FILE
│   ├── PROMPTS.md
│   └── TASKS.md
│
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app entry point
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py                # FastAPI dependencies (auth, db, services)
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py          # v1 router aggregating all endpoints
│   │       ├── content.py
│   │       ├── sessions.py
│   │       └── health.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── content_service.py
│   │   ├── session_service.py
│   │   └── tutor_service.py
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py                # Declarative base
│   │   ├── session.py             # Async engine + session factory
│   │   ├── models.py              # SQLAlchemy ORM models
│   │   └── repositories/
│   │       ├── __init__.py
│   │       ├── partner_repo.py
│   │       ├── content_repo.py
│   │       ├── session_repo.py
│   │       └── usage_repo.py
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── gemini_client.py       # Gemini generation wrapper
│   │   ├── embedding_client.py    # Gemini embeddings wrapper
│   │   └── prompts.py             # System prompts
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py              # Pydantic Settings
│   │   ├── auth.py                # API key validation
│   │   ├── rate_limit.py
│   │   ├── logging.py             # structlog setup
│   │   ├── errors.py              # Custom exceptions + handlers
│   │   └── chunking.py            # Text chunking utilities
│   │
│   └── schemas/
│       ├── __init__.py
│       ├── common.py              # Shared response types
│       ├── content.py             # Content request/response schemas
│       └── session.py             # Session request/response schemas
│
├── alembic/
│   ├── versions/                  # Migration files
│   ├── env.py
│   └── script.py.mako
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Pytest fixtures
│   ├── test_health.py
│   ├── test_content_ingest.py
│   ├── test_sessions.py
│   ├── test_tutor_e2e.py          # End-to-end test (mocks Gemini)
│   └── test_auth.py
│
├── scripts/
│   ├── seed_test_partner.py       # Create a test partner with API key
│   └── load_sample_content.py     # Upload sample lessons for dev
│
├── .env.example
├── .gitignore
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml                 # Dependencies via uv
├── README.md
└── ruff.toml                       # Linter config
```

---

## Database Schema

### Extension setup (in first migration)

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- for gen_random_uuid()
```

### Tables

**partners**
```sql
CREATE TABLE partners (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    api_key_hash TEXT UNIQUE NOT NULL,         -- SHA-256 of the actual key
    api_key_prefix TEXT NOT NULL,              -- first 8 chars for display ("npk_abc1...")
    contact_email TEXT NOT NULL,
    rate_limit_rpm INTEGER NOT NULL DEFAULT 1000,
    rate_limit_messages_pm INTEGER NOT NULL DEFAULT 100,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_partners_api_key_hash ON partners(api_key_hash);
```

**content_items** (one per topic per partner)
```sql
CREATE TABLE content_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
    topic_id TEXT NOT NULL,                    -- partner-supplied stable ID
    title TEXT NOT NULL,
    subject TEXT,                              -- "mathematics", "physics", etc.
    language TEXT NOT NULL DEFAULT 'lt',       -- ISO 639-1
    raw_content TEXT NOT NULL,                 -- original markdown/text
    content_hash TEXT NOT NULL,                -- SHA-256, used to detect changes
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (partner_id, topic_id)
);

CREATE INDEX idx_content_items_partner ON content_items(partner_id);
```

**content_chunks** (chunked + embedded)
```sql
CREATE TABLE content_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
    content_item_id UUID NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,              -- order within parent item
    text TEXT NOT NULL,
    embedding vector(768) NOT NULL,            -- Gemini text-embedding-004 = 768 dims
    token_count INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_content_chunks_item ON content_chunks(content_item_id);
CREATE INDEX idx_content_chunks_partner ON content_chunks(partner_id);

-- HNSW index for fast vector search
CREATE INDEX idx_content_chunks_embedding ON content_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

**sessions**
```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
    student_external_id TEXT NOT NULL,         -- partner-supplied student ID, opaque to us
    topic_id TEXT NOT NULL,                    -- references content_items.topic_id
    language TEXT NOT NULL DEFAULT 'lt',
    metadata JSONB NOT NULL DEFAULT '{}',      -- partner can attach arbitrary context
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

    -- For tutor messages, track what was used to generate them
    retrieved_chunk_ids UUID[],                -- which chunks were in context
    prompt_tokens INTEGER,
    completion_tokens INTEGER
);

CREATE INDEX idx_messages_session ON messages(session_id, created_at);
CREATE INDEX idx_messages_partner ON messages(partner_id);
```

**usage_events** (for billing telemetry)
```sql
CREATE TABLE usage_events (
    id BIGSERIAL PRIMARY KEY,
    partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,                  -- "chat_message", "embed_query", "embed_ingest"
    student_external_id TEXT,                  -- nullable for non-chat events
    session_id UUID,                           -- nullable
    model_name TEXT NOT NULL,                  -- "gemini-2.0-flash", "text-embedding-004"
    prompt_tokens INTEGER NOT NULL DEFAULT 0,
    completion_tokens INTEGER NOT NULL DEFAULT 0,
    duration_ms INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_usage_partner_time ON usage_events(partner_id, created_at);
```

---

## API Specification

All endpoints prefixed with `/v1`. All requests and responses are JSON unless noted. All endpoints require `Authorization: Bearer <api_key>` header.

### Common Response Envelope

**Success:**
```json
{
  "data": { ... },
  "request_id": "req_abc123"
}
```

**Error:**
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Human-readable error description",
    "details": { ... }
  },
  "request_id": "req_abc123"
}
```

### Standard HTTP Status Codes Used

- `200 OK` — successful GET/POST
- `201 Created` — resource created
- `202 Accepted` — async operation queued
- `400 Bad Request` — invalid input
- `401 Unauthorized` — missing/invalid API key
- `403 Forbidden` — valid auth but accessing another partner's resource
- `404 Not Found` — resource doesn't exist
- `422 Unprocessable Entity` — validation failed
- `429 Too Many Requests` — rate limit exceeded
- `500 Internal Server Error` — unexpected error
- `503 Service Unavailable` — Gemini API failure after retries

---

### POST /v1/content/ingest

Upload or update lesson content for a topic.

**Request:**
```json
{
  "topic_id": "math-grade-9-quadratics",
  "title": "Quadratic Equations",
  "subject": "mathematics",
  "language": "lt",
  "content": "# Kvadratinės lygtys\n\nKvadratinė lygtis yra ..."
}
```

**Validation:**
- `topic_id`: required, 1–256 chars, alphanumeric + dash + underscore
- `title`: required, 1–512 chars
- `subject`: optional, max 64 chars
- `language`: required, ISO 639-1 (must be "lt" or "en" in MVP)
- `content`: required, 1–100000 chars

**Behavior:**
- Idempotent: if `(partner_id, topic_id)` already exists, replace content + chunks
- Skip re-embedding if `content_hash` matches existing (no change)
- Synchronous: chunks and embeddings completed before response returns

**Response (201):**
```json
{
  "data": {
    "topic_id": "math-grade-9-quadratics",
    "content_item_id": "uuid-here",
    "chunks_created": 47,
    "tokens_embedded": 12840,
    "content_changed": true
  },
  "request_id": "req_abc123"
}
```

---

### DELETE /v1/content/{topic_id}

Remove lesson content for a topic.

**Path params:** `topic_id`

**Response (204):** No body

---

### POST /v1/sessions

Create a new tutoring session.

**Request:**
```json
{
  "student_external_id": "student-12345",
  "topic_id": "math-grade-9-quadratics",
  "language": "lt",
  "metadata": {
    "student_grade_level": 9,
    "previous_topic_completed": "math-grade-9-linear"
  }
}
```

**Validation:**
- `student_external_id`: required, 1–256 chars
- `topic_id`: required, must exist for this partner
- `language`: optional, defaults to content_item.language
- `metadata`: optional JSONB, max 4KB

**Behavior:**
- Verifies the topic_id exists for this partner
- Creates a new session row
- Does NOT call the LLM yet
- Returns the session_id; partner uses it to send messages

**Response (201):**
```json
{
  "data": {
    "session_id": "uuid-here",
    "topic_id": "math-grade-9-quadratics",
    "language": "lt",
    "created_at": "2026-04-07T10:30:00Z"
  },
  "request_id": "req_abc123"
}
```

---

### POST /v1/sessions/{session_id}/messages

Send a student message and stream the AI response.

**Path params:** `session_id`

**Request:**
```json
{
  "content": "Why does x² - 4 factor to (x-2)(x+2)?"
}
```

**Validation:**
- `content`: required, 1–4000 chars
- session_id must exist AND belong to this partner

**Response:** Server-Sent Events stream (`Content-Type: text/event-stream`)

Each event is one of:

```
event: token
data: {"text": "Great"}

event: token
data: {"text": " question"}

event: token
data: {"text": "!"}

event: done
data: {"message_id": "uuid-here", "prompt_tokens": 1230, "completion_tokens": 145}
```

Or on error:
```
event: error
data: {"code": "LLM_UNAVAILABLE", "message": "Tutor temporarily unavailable, please try again"}
```

**Behavior:**
1. Validates session ownership
2. Saves student message to DB immediately
3. Embeds student message
4. Vector search top-K chunks for this topic
5. If best similarity below threshold → return "no relevant content" message, do NOT call LLM
6. Otherwise: call Gemini Flash with grounded prompt + history
7. Stream tokens as SSE
8. On stream complete: save full assistant message + log usage event
9. On any failure: return error event, do not save partial message

---

### GET /v1/sessions/{session_id}

Retrieve session metadata and message history.

**Path params:** `session_id`

**Query params:**
- `limit`: optional, default 50, max 200 (number of messages)
- `before_id`: optional, for pagination

**Response (200):**
```json
{
  "data": {
    "session_id": "uuid-here",
    "topic_id": "math-grade-9-quadratics",
    "student_external_id": "student-12345",
    "language": "lt",
    "created_at": "2026-04-07T10:30:00Z",
    "last_message_at": "2026-04-07T10:42:00Z",
    "messages": [
      {
        "id": "msg-uuid-1",
        "role": "student",
        "content": "Why does x² - 4 factor to (x-2)(x+2)?",
        "created_at": "2026-04-07T10:32:00Z"
      },
      {
        "id": "msg-uuid-2",
        "role": "tutor",
        "content": "Great question! Let's think about it together...",
        "created_at": "2026-04-07T10:32:08Z"
      }
    ]
  },
  "request_id": "req_abc123"
}
```

---

### DELETE /v1/sessions/{session_id}

End and remove a tutoring session.

**Response (204):** No body

---

### GET /v1/health

Liveness check. No auth required.

**Response (200):**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "checks": {
    "database": "ok",
    "gemini": "ok"
  }
}
```

---

## Error Codes

Internal error codes used in error responses:

| Code | HTTP | Meaning |
|---|---|---|
| `INVALID_REQUEST` | 400 | Request body malformed |
| `VALIDATION_ERROR` | 422 | Pydantic validation failed |
| `MISSING_AUTH` | 401 | No Authorization header |
| `INVALID_API_KEY` | 401 | API key not recognized |
| `PARTNER_INACTIVE` | 401 | Partner account disabled |
| `FORBIDDEN_RESOURCE` | 403 | Resource belongs to another partner |
| `RESOURCE_NOT_FOUND` | 404 | Resource doesn't exist |
| `RATE_LIMITED` | 429 | Partner rate limit exceeded |
| `CONTENT_TOO_LARGE` | 400 | Content exceeds max size |
| `TOPIC_NOT_FOUND` | 404 | topic_id doesn't exist for this partner |
| `SESSION_NOT_FOUND` | 404 | session_id doesn't exist |
| `LLM_UNAVAILABLE` | 503 | Gemini API failed after retries |
| `LLM_TIMEOUT` | 503 | Gemini request timed out |
| `EMBEDDING_FAILED` | 503 | Embedding API failed |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

---

## Constants

These should live in `app/core/config.py` as Settings (env-overridable).

```python
# RAG / retrieval
EMBEDDING_DIMENSIONS = 768               # Gemini text-embedding-004
CHUNK_SIZE = 800                         # characters
CHUNK_OVERLAP = 150                      # characters
RETRIEVAL_TOP_K = 5
SIMILARITY_THRESHOLD = 0.65              # cosine distance, lower = more similar
                                          # if best result > this → no answer

# LLM
LLM_MODEL = "gemini-2.0-flash"
LLM_MAX_OUTPUT_TOKENS = 1024
LLM_TEMPERATURE = 0.3                    # low for consistency
LLM_TIMEOUT_SECONDS = 30
LLM_MAX_RETRIES = 3

# Conversation
MAX_HISTORY_MESSAGES = 10                # last N messages included as context

# Content limits
MAX_CONTENT_LENGTH = 100000              # characters per ingest
MAX_MESSAGE_LENGTH = 4000                # characters per student message
MAX_METADATA_BYTES = 4096

# Rate limits (default per partner, overridable in DB)
DEFAULT_RATE_LIMIT_RPM = 1000
DEFAULT_RATE_LIMIT_MESSAGES_PM = 100
DEFAULT_RATE_LIMIT_INGEST_PM = 10
```

---

## Dockerfile

```dockerfile
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

---

## docker-compose.yml

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: neuro
      POSTGRES_PASSWORD: neuro_dev_password
      POSTGRES_DB: neuro
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U neuro"]
      interval: 5s
      timeout: 3s
      retries: 5

  api:
    build: .
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      ENV: development
      DATABASE_URL: postgresql+asyncpg://neuro:neuro_dev_password@postgres:5432/neuro
      GEMINI_API_KEY: ${GEMINI_API_KEY}
      GEMINI_GENERATION_MODEL: gemini-2.0-flash
      GEMINI_EMBEDDING_MODEL: text-embedding-004
      LOG_LEVEL: DEBUG
    ports:
      - "8000:8000"
    command: >
      sh -c "uv run alembic upgrade head &&
             uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
    volumes:
      - ./app:/app/app
      - ./alembic:/app/alembic

volumes:
  pgdata:
```

---

## pyproject.toml (key dependencies)

```toml
[project]
name = "neuro-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115.0",
  "uvicorn[standard]>=0.32.0",
  "sqlalchemy[asyncio]>=2.0.36",
  "asyncpg>=0.30.0",
  "alembic>=1.14.0",
  "pgvector>=0.3.6",
  "pydantic>=2.10.0",
  "pydantic-settings>=2.6.0",
  "google-genai>=0.3.0",
  "tenacity>=9.0.0",
  "slowapi>=0.1.9",
  "structlog>=24.4.0",
  "python-multipart>=0.0.17",
  "httpx>=0.28.0",
]

[dependency-groups]
dev = [
  "pytest>=8.3.0",
  "pytest-asyncio>=0.24.0",
  "pytest-cov>=6.0.0",
  "ruff>=0.8.0",
  "mypy>=1.13.0",
  "httpx>=0.28.0",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```