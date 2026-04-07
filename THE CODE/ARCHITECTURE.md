# ARCHITECTURE.md

## High-Level System View

```
                    ┌──────────────────────────────────────┐
                    │         PARTNER PLATFORM             │
                    │  (Edukamentas, Eduka, etc.)          │
                    │                                      │
                    │   Their frontend / their backend     │
                    └──────────────┬───────────────────────┘
                                   │ HTTPS + API Key
                                   │
                    ┌──────────────▼───────────────────────┐
                    │    NEUROPETITORIUS API (FastAPI)     │
                    │                                      │
                    │   ┌─────────────────────────────┐    │
                    │   │  Auth Middleware            │    │
                    │   │  (API key → partner_id)     │    │
                    │   └──────────┬──────────────────┘    │
                    │              │                       │
                    │   ┌──────────▼──────────────────┐    │
                    │   │  Rate Limiter (per partner) │    │
                    │   └──────────┬──────────────────┘    │
                    │              │                       │
                    │   ┌──────────▼──────────────────┐    │
                    │   │  Route Handlers             │    │
                    │   │  /content/ingest            │    │
                    │   │  /sessions                  │    │
                    │   │  /sessions/{id}/messages    │    │
                    │   └──────────┬──────────────────┘    │
                    │              │                       │
                    │   ┌──────────▼──────────────────┐    │
                    │   │  Service Layer              │    │
                    │   │  - ContentService           │    │
                    │   │  - SessionService           │    │
                    │   │  - TutorService (LLM logic) │    │
                    │   └──────────┬──────────────────┘    │
                    │              │                       │
                    └──────────────┼───────────────────────┘
                                   │
                ┌──────────────────┼──────────────────┐
                │                  │                  │
        ┌───────▼──────┐   ┌──────▼──────┐   ┌──────▼──────────┐
        │  PostgreSQL  │   │  Gemini API │   │  Gemini Embed   │
        │  + pgvector  │   │  (Flash)    │   │  API            │
        │              │   │  EU region  │   │  EU region      │
        │  - partners  │   │             │   │                 │
        │  - content   │   └─────────────┘   └─────────────────┘
        │  - chunks    │
        │    (vector)  │
        │  - sessions  │
        │  - messages  │
        │  - usage     │
        └──────────────┘
```

---

## Component Breakdown

### 1. FastAPI Application Layer

**Why FastAPI:**
- Native async support (we'll be doing a lot of streaming)
- Pydantic for free request validation
- Auto-generated OpenAPI docs (which becomes our partner-facing API documentation)
- Best-in-class developer experience for Python APIs
- SSE streaming is well-supported

**Structure:** Standard Clean Architecture with three layers:

```
app/
├── api/              # Route handlers (thin — only HTTP concerns)
│   ├── v1/
│   │   ├── content.py
│   │   ├── sessions.py
│   │   └── health.py
│   └── deps.py       # Dependency injection (auth, db, services)
│
├── services/         # Business logic (the actual work)
│   ├── content_service.py
│   ├── session_service.py
│   └── tutor_service.py
│
├── db/               # Database layer
│   ├── models.py     # SQLAlchemy ORM models
│   ├── repositories/ # Data access (one repo per aggregate)
│   │   ├── partner_repo.py
│   │   ├── content_repo.py
│   │   ├── session_repo.py
│   │   └── usage_repo.py
│   └── session.py    # DB session/connection management
│
├── llm/              # LLM provider abstraction
│   ├── gemini_client.py
│   ├── embedding_client.py
│   └── prompts.py    # System prompts (also documented in PROMPTS.md)
│
├── core/             # Cross-cutting concerns
│   ├── config.py     # Settings (env-based)
│   ├── auth.py       # API key validation
│   ├── rate_limit.py # Rate limiting
│   ├── logging.py    # Structured JSON logging
│   └── errors.py     # Error types and HTTP error mapping
│
├── schemas/          # Pydantic request/response models
│   ├── content.py
│   ├── session.py
│   └── common.py
│
└── main.py           # FastAPI app initialization
```

**Why this structure:**
- API layer is dumb — only translates HTTP to service calls
- Service layer is the only place business logic lives
- Repository layer is the only place that touches the database
- LLM layer is isolated so we can swap providers later (but won't in MVP)
- Easy to test each layer independently

### 2. Database (PostgreSQL + pgvector)

**Why Postgres + pgvector instead of a managed vector DB (Pinecone, Qdrant):**
- One database, one set of credentials, one backup story
- pgvector is mature enough for MVP scale (millions of vectors handled fine)
- We get transactional consistency between content metadata and vectors
- Postgres on Hetzner is ~€5/month; Pinecone starts at €70/month
- We can migrate to a dedicated vector DB later if we hit scale limits (we won't for a long time)

**Schema (full SQL in TECH_SPEC.md):**
- `partners` — partner accounts and API keys
- `content_items` — top-level lesson units (one per topic)
- `content_chunks` — chunked text + embeddings (1536 dimensions)
- `sessions` — tutoring sessions (one student × one topic)
- `messages` — chat messages within a session
- `usage_events` — token usage for billing/analytics

All tables have `partner_id` as the first column after `id`. Every query filters by it. **Always.**

### 3. LLM Layer

**Two Gemini calls per architecture:**

**A. Embeddings (text-embedding-004 or gemini-embedding-001):**
- Used at content ingestion time (chunk → vector)
- Used at every chat message (user message → vector → search)
- Cheap (~$0.00001 per 1k tokens)
- Cached aggressively (content embeddings never change unless content updates)

**B. Generation (gemini-2.0-flash or gemini-2.5-flash):**
- Used for every tutor response
- Streamed via SSE for low time-to-first-token
- Wrapped with retry logic (tenacity) — 3 attempts with exponential backoff
- Wrapped with timeout — 30 seconds total response time max
- Token usage logged after every call

**Both are accessed through `app/llm/gemini_client.py`** which provides a clean async interface and is the ONLY file that imports the Google GenAI SDK. Everything else uses our wrapper.

### 4. Authentication

**Simple API key authentication:**

- Each partner gets one API key on signup (32-byte random, base64-encoded)
- Stored as `sha256(api_key)` in the `partners` table — never the raw key
- Sent as `Authorization: Bearer <api_key>` header
- Middleware extracts and validates on every request
- On valid: attaches `partner_id` to request state
- On invalid: returns 401 immediately

**No OAuth, no JWT, no refresh tokens in MVP.** Partner-level API keys only. Student identity is partner-supplied (we trust the partner's `student_id` value).

### 5. Rate Limiting

**Per-partner rate limits enforced at the FastAPI middleware layer:**

- Use `slowapi` (Redis-backed) or in-memory limiter for MVP
- Default limits (configurable per partner in DB later):
  - 1000 requests / minute per partner
  - 100 chat messages / minute per partner
  - 10 content ingest requests / minute per partner
- Returns 429 with `Retry-After` header on limit exceeded
- We can switch to Redis-backed when we deploy multiple instances

---

## The Tutor Request Flow (the most important thing in the system)

This is what happens when a student sends a message:

```
1. Partner POSTs /v1/sessions/{session_id}/messages
   Body: { "role": "student", "content": "Why does x²-4 factor to (x-2)(x+2)?" }
   Headers: Authorization: Bearer <partner_api_key>

2. FastAPI middleware validates API key → resolves partner_id
   ├─ Invalid key? → 401, stop
   └─ Valid → continue

3. Rate limiter checks partner's quota
   ├─ Over limit? → 429, stop
   └─ Under limit → continue

4. Route handler validates request body via Pydantic
   ├─ Invalid? → 422, stop
   └─ Valid → call SessionService.send_message()

5. SessionService:
   a. Loads the session from DB
   b. Verifies session.partner_id == request.partner_id (CRITICAL — prevents
      partner A from accessing partner B's sessions)
   c. Loads recent message history (last N messages, e.g. 10)
   d. Saves the new student message to messages table
   e. Calls TutorService.generate_response()

6. TutorService (the heart of the system):
   a. Embed the student message via Gemini Embed API
   b. Vector search content_chunks WHERE topic_id = session.topic_id
      ORDER BY embedding <=> query_embedding LIMIT 5
   c. Build the LLM prompt:
      - System prompt (from PROMPTS.md, includes Socratic instructions)
      - Retrieved chunks as "LESSON CONTEXT"
      - Recent message history
      - Current student message
   d. If retrieved chunks have low similarity (e.g. all > 0.7 distance):
      → Return "I don't have that in your lesson" response, do NOT call LLM
   e. Otherwise: stream Gemini Flash response back to caller

7. FastAPI streams the response back via Server-Sent Events
   - Each Gemini token chunk → SSE event
   - On stream complete → save full assistant message to DB
   - Log token usage to usage_events table

8. Partner's frontend receives the streamed response and displays it
```

**Key design decisions explained:**

- **Why save the user message before generating the response?** So if the LLM call fails halfway, we still have a record of what the student asked and can show it on retry.
- **Why retrieve chunks by `topic_id`, not free-text across all content?** Because the partner already knows what topic the student is working on (passed when creating the session). This dramatically improves retrieval quality and speed.
- **Why a similarity threshold check before calling the LLM?** Cost saving and hallucination prevention. If we don't have relevant content, we shouldn't ask the LLM to make up an answer.
- **Why stream via SSE not WebSockets?** SSE is simpler, works through firewalls, and is unidirectional which is exactly what we need (server → client only). WebSockets are overkill.

---

## The Content Ingestion Flow

```
1. Partner POSTs /v1/content/ingest
   Body: {
     "topic_id": "math-grade-9-quadratics",  // partner-supplied stable ID
     "title": "Quadratic Equations",
     "subject": "mathematics",
     "language": "lt",
     "content": "<full lesson markdown>"
   }

2. Auth middleware → partner_id resolved

3. ContentService.ingest():
   a. UPSERT content_items row (partner_id, topic_id is the unique constraint)
   b. If content already existed: DELETE old chunks for this content_item
   c. Chunk the text using RecursiveCharacterTextSplitter
      - chunk_size: 800 characters
      - chunk_overlap: 150 characters
      - Respects markdown headings and paragraph boundaries
   d. For each chunk: call Gemini Embed API to get vector
      - Batch in groups of 100 (Gemini supports batch embedding)
   e. INSERT all chunks with their embeddings into content_chunks table
   f. Return { "topic_id": "...", "chunks_created": 47, "status": "ok" }

4. Done. The lesson is now searchable for tutoring.
```

**Idempotency:** Calling ingest twice with the same `partner_id + topic_id` UPDATES the existing content (delete old chunks, insert new). Partners can re-upload safely when they edit lessons.

---

## Configuration & Environment

**All config via environment variables. No hardcoded values.**

```
# .env.example
ENV=development
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/neuro

# Gemini
GEMINI_API_KEY=
GEMINI_GENERATION_MODEL=gemini-2.0-flash
GEMINI_EMBEDDING_MODEL=text-embedding-004
GEMINI_REGION=europe-west1

# Rate limiting
RATE_LIMIT_REQUESTS_PER_MINUTE=1000
RATE_LIMIT_MESSAGES_PER_MINUTE=100

# RAG
EMBEDDING_DIMENSIONS=768
CHUNK_SIZE=800
CHUNK_OVERLAP=150
RETRIEVAL_TOP_K=5
SIMILARITY_THRESHOLD=0.65

# Tutor behavior
MAX_CONVERSATION_HISTORY=10
MAX_RESPONSE_TOKENS=1024
LLM_TIMEOUT_SECONDS=30
LLM_MAX_RETRIES=3
```

---

## Deployment Architecture (MVP)

**Single-server deployment for v0.1. Scale later if needed.**

```
┌─────────────────────────────────────┐
│  Hetzner Cloud CX22 (or similar)    │
│  EU region (Falkenstein/Helsinki)   │
│  €5–10/month                        │
│                                     │
│  Docker Compose:                    │
│  ┌─────────────────────────┐        │
│  │  api (FastAPI/Uvicorn)  │ :8000  │
│  └────────────┬────────────┘        │
│               │                     │
│  ┌────────────▼────────────┐        │
│  │  postgres + pgvector    │ :5432  │
│  └─────────────────────────┘        │
│                                     │
│  Caddy reverse proxy → HTTPS        │
│  api.neuropetitorius.com            │
└─────────────────────────────────────┘
```

**Why single server:**
- Simpler ops, fewer things to break
- Cheap enough that cost is irrelevant
- Will handle 1000+ requests/minute easily for MVP traffic
- We can add horizontal scaling when revenue justifies it

**When to scale up:**
- If postgres CPU > 70% sustained → bigger DB instance
- If API CPU > 70% sustained → multiple API instances behind load balancer
- If embedding latency > 1s → add Redis cache for query embeddings
- If we hit Gemini rate limits → request quota increase from Google

---

## Observability

**Logging:**
- Structured JSON logs to stdout
- Every request logged with: request_id, partner_id, endpoint, status, duration_ms
- Every LLM call logged with: model, prompt_tokens, completion_tokens, duration_ms, partner_id
- Errors include full traceback + request context

**Metrics (post-MVP, but plan for it):**
- Prometheus endpoint on `/metrics`
- Key metrics: requests_total, request_duration, llm_calls_total, llm_tokens_total, errors_total
- All labeled by partner_id for billing reconciliation

**Tracing (post-MVP):**
- OpenTelemetry instrumentation
- Useful when debugging slow requests across DB + LLM calls

---

## Security Notes

- API keys hashed with SHA-256 before storage (so a DB breach doesn't leak keys)
- All endpoints require HTTPS (Caddy handles cert via Let's Encrypt)
- SQL injection prevented by SQLAlchemy ORM (no raw queries)
- Pydantic validates all input
- Rate limiting prevents abuse
- No PII in logs (mask student IDs if needed)
- Gemini API key stored in environment variable, never committed
- Partner data fully isolated via partner_id WHERE clauses on every query
- Row-level security enabled in Postgres as defense-in-depth (post-MVP)

---

## What Could Go Wrong (and how we mitigate)

| Risk | Mitigation |
|---|---|
| Gemini API down | Retry with backoff, return clean 503 to partner if all retries fail |
| LLM hallucinates despite RAG | Strict similarity threshold + system prompt explicitly forbids invention |
| Lithuanian quality is poor | Test thoroughly during PoC week; switch to gemini-1.5-pro if Flash is insufficient |
| Partner uploads massive file | Hard limit on content size (e.g., 100k characters per ingest call) |
| One partner monopolizes resources | Per-partner rate limiting (already in design) |
| Vector search gets slow | pgvector HNSW index, monitor query times, add Redis caching if needed |
| Database grows unbounded | Old session cleanup CRON (post-MVP) |