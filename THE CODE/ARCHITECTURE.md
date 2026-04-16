# ARCHITECTURE.md

## High-Level System View

```
                    ┌──────────────────────────────────────┐
                    │         PARTNER PLATFORM             │
                    │  (Edukamentas, Eduka, etc.)      │
                    │                              │
                    │   Their frontend / their backend     │
                    └──────────────┬───────────────────────┘
                                   │ HTTPS + API Key
                                   │
                    ┌──────────────▼───────────────────────┐
                    │    NEUROPETITORIUS API (FastAPI)     │
                    │                              │
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
                    │   │  /sessions (Mode 1)       │    │
                    │   │  /sessions/{id}/messages  │    │
                    │   └──────────┬──────────────────┘    │
                    │              │                       │
                    │   ┌──────────▼──────────────────┐    │
                    │   │  Service Layer              │    │
                    │   │  - SessionService          │    │
                    │   │    (with embedding)        │    │
                    │   │  - TutorService (LLM logic)  │    │
                    │   └──────────┬──────────────────┘    │
                    │              │                       │
                    └──────────────┼───────────────────────┘
                                   │
                 ┌──────────────────┼──────────────────┐
                 │                  │                  │
         ┌───────▼──────┐   ┌────▼──────┐   ┌────▼──────────┐
         │  PostgreSQL  │   │  Gemini API │   │  Gemini Embed │
         │  + pgvector  │   │  (Flash)  │   │  API         │
         │              │   │  EU region │   │  EU region   │
         │  - partners  │   └───────��──┘   └──────────────┘
         │  - sessions  │
         │  - session_chunks │
         │    (vector)   │
         │  - embedding_cache │
         │  - messages   │
         │  - usage     │
         └──────────────┘
```

**Mode 1 Key Difference:** Content arrives with the session, not via a separate ingest call.

---

## Component Breakdown

### 1. FastAPI Application Layer

**Structure:**
```
app/
├── api/
│   ├── v1/
│   │   ├── sessions.py    # Session + content endpoints
│   │   └── health.py
│   └── deps.py
│
├── services/
│   ├── tutor.py         # RAG + streaming
│   ├── chunking.py     # Text chunking
│   └── scheduler.py    # CRON jobs
│
├── db/
│   ├── models.py      # ORM models (session_chunks, embedding_cache)
│   └── repositories/
│       └── session_repo.py  # Includes search_session_chunks()
│
├── llm/
│   ├── client.py    # Gemini generation + embeddings
│   └── prompts.py
│
└── core/
    ├── config.py   # Mode 1 settings
    ├── auth.py
    ├── rate_limit.py
    └── errors.py
```

### 2. Database (PostgreSQL + pgvector)

**Schema:**
- `partners` — partner accounts and API keys
- `sessions` — tutoring sessions with inline content metadata
- `session_chunks` — chunked text + embeddings (session-scoped)
- `embedding_cache` — shared cache for avoiding redundant embeddings
- `messages` — chat messages within a session
- `usage_events` — token usage for billing/analytics

All queries filter by `partner_id`. **Always.**

### 3. Authentication

- Each partner gets one API key on signup
- Stored as `sha256(api_key)` in the `partners` table
- Sent as `Authorization: Bearer <api_key>` header

---

## Session Creation Flow (Mode 1 - The Heavy Lift)

This is the most critical flow in Mode 1:

```
1. Partner POSTs /v1/sessions with inline content
   Body: {
     "student_external_id": "student-12345",
     "title": "Kvadratinės lygtys",
     "language": "lt",
     "content": {
       "mode": "inline",
       "title": "Kvadratinės lygtys",
       "subject": "mathematics",
       "text": "# Kvadratinės lygtys\n\n..."
     }
   }

2. Auth middleware → partner_id resolved

3. Rate limiter check

4. SessionService.create():
   a. Validate + normalize content
      - Strip trailing whitespace
      - Collapse 3+ consecutive newlines → 2
      - Normalize to NFC form
   b. Compute content_hash = sha256(normalized_text)
   c. Check embedding_cache:
      - HIT: load cached chunks (~50ms)
      - MISS: continue to step 5
   d. Chunk text using RecursiveCharacterTextSplitter
      - chunk_size: 800 chars
      - chunk_overlap: 150 chars
   e. Batch embed via Gemini Embed API (100 chunks per batch)
   f. Store in embedding_cache
   g. Insert session row with content metadata
   h. Insert session_chunks linked to session_id
   i. Return session details

5. Partner stores session_id for subsequent messages
```

**Performance:**
- First session on content: ~1.5s (embedding via Gemini)
- Subsequent sessions on same content: ~50ms (cache hit)

---

## The Tutor Request Flow

```
1. Partner POSTs /v1/sessions/{session_id}/messages
   Body: { "content": "Kaip spręsti x² - 4 = 0?" }
   Headers: Authorization: Bearer <partner_api_key>

2. FastAPI middleware validates API key → resolves partner_id

3. Rate limiter checks partner's quota

4. Route handler validates request body via Pydantic

5. SessionService:
   a. Loads session from DB
   b. Verifies session.partner_id == request.partner_id
   c. Saves student message to messages table

6. TutorService (the heart):
   a. Embed student message via Gemini Embed API
   b. Vector search session_chunks WHERE session_id = session.id
      ORDER BY embedding <=> query_embedding LIMIT 5
   c. Build LLM prompt:
      - System prompt (Socratic instructions)
      - Retrieved chunks as "LESSON CONTEXT"
      - Current student message
   d. If low similarity: return fallback response
   e. Otherwise: stream Gemini Flash response

7. Streamed back via Server-Sent Events
```

---

## Auto-Expiration (Mode 1 Promise)

**Sessions expire automatically:**

- **24 hours** without activity → delete
- **2 hours** never messaged → delete
- Runs nightly at 2:00 AM UTC

This enforces "content disappears when session ends" — critical for GDPR.

---

## Configuration & Environment

```python
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/neuro

# Gemini
GEMINI_API_KEY=
GEMINI_GENERATION_MODEL=gemini-2.0-flash
GEMINI_EMBEDDING_MODEL=text-embedding-004

# Rate limiting
RATE_LIMIT_RPM=1000
RATE_LIMIT_MESSAGES_PM=100

# RAG
CHUNK_SIZE=800
CHUNK_OVERLAP=150
RETRIEVAL_TOP_K=5
SIMILARITY_THRESHOLD=0.65

# Session content limits
SESSION_CONTENT_MAX_LENGTH=100000
SESSION_CONTENT_MIN_LENGTH=50

# Auto-expiration
SESSION_AUTO_EXPIRE_INACTIVE_HOURS=24
SESSION_AUTO_EXPIRE_NEVER_USED_HOURS=2

# Embedding cache
EMBEDDING_CACHE_TTL_DAYS=30
EMBEDDING_CACHE_MAX_ROWS=100000
```

---

## Security Notes

- API keys hashed with SHA-256 before storage
- All endpoints require HTTPS
- SQL injection prevented by SQLAlchemy ORM
- Pydantic validates all input
- Rate limiting prevents abuse
- Partner data fully isolated via `partner_id` WHERE clauses
- Defense in depth: session_id filter + partner_id filter on all queries

---

## What Could Go Wrong

| Risk | Mitigation |
|---|---|
| Gemini API down | Retry with backoff, return clean 503 |
| First session slow (1.5s) | Document for partners, embedding cache helps subsequent sessions |
| Partner sends massive content | Hard limit: 100,000 chars per session |
| One partner monopolizes resources | Per-partner rate limiting |
| Vector search slow | pgvector HNSW index |
| Cache grows unbounded | CRON job cleanup (30 days TTL) |
| Sessions persist too long | Auto-expiration CRON (24h inactivity) |