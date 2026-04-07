# TASKS.md

The MVP build is broken into 6 milestones. Each milestone is independently shippable and testable. Complete one milestone fully (including tests) before starting the next.

**Estimated total time:** 6–8 weeks for one developer working full-time, or 10–12 weeks at part-time pace.

**Track progress here.** As you complete tasks, mark them with `[x]`. When a milestone is fully done, the agent should pause and request user verification before moving to the next.

---

## Milestone 0: Project Skeleton (Day 1–2)

**Goal:** A FastAPI app that runs locally, returns "ok" on health check, has all dev tooling configured.

- [ ] Initialize git repo
- [ ] Create directory structure as defined in `TECH_SPEC.md`
- [ ] Set up `pyproject.toml` with all dependencies (use uv)
- [ ] Create `app/main.py` with minimal FastAPI app
- [ ] Create `app/core/config.py` with Pydantic Settings + `.env.example`
- [ ] Create `app/core/logging.py` with structlog JSON setup
- [ ] Create `app/api/v1/health.py` with `GET /v1/health`
- [ ] Create `Dockerfile` and `docker-compose.yml` (postgres + api services)
- [ ] Verify: `docker-compose up` starts cleanly, `curl localhost:8000/v1/health` returns 200
- [ ] Set up `ruff.toml` and run `ruff check .` (must pass)
- [ ] Set up `mypy.ini` and run `mypy app/` (must pass)
- [ ] Create `tests/conftest.py` with pytest fixtures for FastAPI test client + test DB
- [ ] Write first test: `tests/test_health.py`
- [ ] Create `README.md` with local setup instructions
- [ ] Create `.gitignore` (must include `.env`, `__pycache__`, `.venv`, etc.)

**Definition of done:**
- `docker-compose up` starts everything cleanly
- `pytest` runs and passes (at minimum the health test)
- `ruff check .` passes
- `mypy app/` passes
- README explains how to run locally in <10 lines

---

## Milestone 1: Database & Migrations (Day 3–5)

**Goal:** Complete database schema deployed via Alembic migrations. Repository pattern set up with ORM models.

- [ ] Install pgvector in the postgres container (use `pgvector/pgvector:pg16` image)
- [ ] Create `app/db/base.py` with SQLAlchemy declarative base
- [ ] Create `app/db/session.py` with async engine + session factory
- [ ] Create `app/db/models.py` with all 6 tables from `TECH_SPEC.md`:
  - [ ] Partner
  - [ ] ContentItem
  - [ ] ContentChunk (with vector(768) column)
  - [ ] Session
  - [ ] Message
  - [ ] UsageEvent
- [ ] Initialize Alembic: `alembic init alembic`
- [ ] Configure `alembic/env.py` to use async engine and import models metadata
- [ ] Generate first migration: enable pgvector extension + create all tables
- [ ] Add HNSW index for content_chunks.embedding (cosine ops)
- [ ] Test: migration runs cleanly on a fresh DB
- [ ] Create repository files in `app/db/repositories/`:
  - [ ] `partner_repo.py` (get_by_api_key_hash, create)
  - [ ] `content_repo.py` (upsert_item, delete_item, insert_chunks, search_chunks)
  - [ ] `session_repo.py` (create, get_by_id, list_messages)
  - [ ] `usage_repo.py` (log_event)
- [ ] Each repository method should be async and take `db: AsyncSession` as parameter
- [ ] Write integration tests for each repository (use pytest-asyncio + test DB)

**Definition of done:**
- Fresh `docker-compose up` runs migrations and creates all tables
- HNSW index exists on content_chunks
- All repository methods have at least one passing test
- Tests use a separate test database (not the dev DB)

---

## Milestone 2: Authentication & Rate Limiting (Day 6–7)

**Goal:** Partner API key authentication works. Rate limiting works. All endpoints reject invalid auth with clean error messages.

- [ ] Create `app/core/auth.py`:
  - [ ] `hash_api_key(raw_key: str) -> str` (SHA-256)
  - [ ] `generate_api_key() -> tuple[str, str, str]` returns (raw_key, hash, prefix)
  - [ ] FastAPI dependency `get_current_partner(authorization: str) -> Partner`
- [ ] Add auth dependency to `app/api/deps.py`
- [ ] Create `app/core/errors.py` with custom exceptions and FastAPI exception handlers
- [ ] Define error codes from `TECH_SPEC.md`
- [ ] Set up `app/core/rate_limit.py` using slowapi (in-memory for MVP)
- [ ] Per-partner rate limiting using partner_id as key
- [ ] Wire rate limiter into FastAPI middleware
- [ ] Create `scripts/seed_test_partner.py`:
  - [ ] Generates a random API key
  - [ ] Inserts a partner row with the hash
  - [ ] Prints the raw key to stdout (only place it's ever shown)
- [ ] Run the script and verify a partner exists in the DB
- [ ] Add a protected dummy endpoint `GET /v1/test-auth` for verification
- [ ] Write tests:
  - [ ] Missing Authorization header → 401
  - [ ] Invalid API key → 401
  - [ ] Valid API key → 200, partner_id available in handler
  - [ ] Inactive partner → 401
  - [ ] Rate limit exceeded → 429

**Definition of done:**
- Calling any auth-required endpoint without a valid API key returns 401
- Calling with a valid API key works
- Rate limiting kicks in after configured threshold
- Test partner script works and prints API key

---

## Milestone 3: Content Ingestion (Day 8–11)

**Goal:** Partners can upload lesson content. The system chunks it, embeds via Gemini, and stores in pgvector.

- [ ] Create `app/llm/gemini_client.py`:
  - [ ] Initialize Gemini client with API key from settings
  - [ ] Method: `embed_documents(texts: list[str]) -> list[list[float]]` (batch up to 100)
  - [ ] Use `task_type=RETRIEVAL_DOCUMENT` for ingestion
  - [ ] Wrap with tenacity retry (3 attempts, exponential backoff)
  - [ ] 30-second timeout per call
  - [ ] Log each call to usage_events
- [ ] Create `app/core/chunking.py`:
  - [ ] `chunk_text(text: str, chunk_size=800, overlap=150) -> list[str]`
  - [ ] Use a recursive splitter that respects paragraph and sentence boundaries
  - [ ] You can use `langchain-text-splitters` (just for this utility, not full langchain)
- [ ] Create `app/services/content_service.py`:
  - [ ] `ingest_content(partner_id, request) -> IngestResponse`
  - [ ] Compute content_hash (SHA-256 of content)
  - [ ] If existing content_item with same hash exists → return early (no change)
  - [ ] Otherwise: UPSERT content_item, DELETE old chunks, chunk text, embed in batches, INSERT chunks
  - [ ] Wrap entire operation in a single DB transaction
  - [ ] Return chunks_created + tokens_embedded
- [ ] Create `app/schemas/content.py` with Pydantic models for request/response
- [ ] Create `app/api/v1/content.py`:
  - [ ] `POST /v1/content/ingest`
  - [ ] `DELETE /v1/content/{topic_id}`
- [ ] Wire content router into v1 router
- [ ] Write tests:
  - [ ] Ingest happy path with mocked Gemini embeddings
  - [ ] Re-ingest with same content → no change, no new embeddings
  - [ ] Re-ingest with modified content → old chunks deleted, new ones created
  - [ ] Content too large → 400
  - [ ] Invalid topic_id format → 422
  - [ ] Delete topic → 204, chunks gone
  - [ ] Delete topic from another partner → 404 (not 403, to avoid leaking existence)
- [ ] Manual test: ingest a real Lithuanian math lesson and verify chunks in DB

**Definition of done:**
- A partner can POST a lesson and see it chunked + embedded in the DB
- Re-uploading the same lesson is idempotent
- Vector search returns the chunks (test with raw SQL query if needed at this stage)

---

## Milestone 4: Sessions & Message Persistence (Day 12–14)

**Goal:** Partners can create sessions and the system stores message history. No LLM yet — that's next.

- [ ] Create `app/services/session_service.py`:
  - [ ] `create_session(partner_id, request) -> Session`
  - [ ] Verify topic_id exists for this partner before creating session
  - [ ] `get_session_with_messages(partner_id, session_id, limit, before_id) -> SessionWithMessages`
  - [ ] Verify session.partner_id matches request partner_id (CRITICAL)
  - [ ] `delete_session(partner_id, session_id)`
- [ ] Create `app/schemas/session.py` with Pydantic models
- [ ] Create `app/api/v1/sessions.py`:
  - [ ] `POST /v1/sessions`
  - [ ] `GET /v1/sessions/{session_id}`
  - [ ] `DELETE /v1/sessions/{session_id}`
  - [ ] `POST /v1/sessions/{session_id}/messages` — stub for now, returns "not implemented"
- [ ] Write tests:
  - [ ] Create session with valid topic → 201
  - [ ] Create session with non-existent topic → 404
  - [ ] Get own session → 200 with messages
  - [ ] Get another partner's session → 404
  - [ ] Delete own session → 204
  - [ ] Delete another partner's session → 404

**Definition of done:**
- Sessions can be created and retrieved
- Cross-partner access is prevented
- The messages endpoint exists but doesn't yet generate responses

---

## Milestone 5: Tutor Engine (Day 15–22) — THE BIG ONE

**Goal:** The actual AI tutoring works. Student sends a message, gets a grounded response streamed back.

- [ ] Add to `app/llm/gemini_client.py`:
  - [ ] `embed_query(text: str) -> list[float]` with `task_type=RETRIEVAL_QUERY`
  - [ ] `generate_stream(system_instruction, contents, generation_config)` returns async iterator of token chunks
  - [ ] Handle Gemini exceptions and translate to our error codes
- [ ] Create `app/llm/prompts.py` with all prompts from `PROMPTS.md`:
  - [ ] `TUTOR_SYSTEM_PROMPT` (with `{language}` and `{lesson_context}` placeholders)
  - [ ] `NO_CONTEXT_RESPONSE_LT`
  - [ ] `NO_CONTEXT_RESPONSE_EN`
  - [ ] `format_lesson_context(chunks)` helper
  - [ ] `build_gemini_messages(history, new_user_message)` helper
- [ ] Add to `app/db/repositories/content_repo.py`:
  - [ ] `search_chunks(partner_id, topic_id, query_embedding, top_k) -> list[ChunkResult]`
  - [ ] Use pgvector cosine distance: `embedding <=> :query_embedding`
  - [ ] Return chunks with their distance score
  - [ ] Filter by partner_id AND topic_id
- [ ] Create `app/services/tutor_service.py`:
  - [ ] `generate_response_stream(partner_id, session_id, student_message)` -> async generator yielding events
  - [ ] Step 1: Save student message to DB
  - [ ] Step 2: Embed student message via Gemini
  - [ ] Step 3: Retrieve top-K chunks for session.topic_id
  - [ ] Step 4: Check if best chunk distance > SIMILARITY_THRESHOLD → yield no-context response, save it, return
  - [ ] Step 5: Build system prompt with retrieved chunks
  - [ ] Step 6: Load last N messages from session as history
  - [ ] Step 7: Call Gemini stream
  - [ ] Step 8: Yield each token as SSE event
  - [ ] Step 9: Accumulate full response, save to DB on completion
  - [ ] Step 10: Log usage event with token counts
  - [ ] Wrap entire flow in try/except to handle LLM failures gracefully
- [ ] Implement SSE response in `app/api/v1/sessions.py`:
  - [ ] `POST /v1/sessions/{session_id}/messages`
  - [ ] Use FastAPI's `StreamingResponse` with `media_type="text/event-stream"`
  - [ ] Format events as `event: token\ndata: {json}\n\n`
  - [ ] On completion: send `event: done` with metadata
  - [ ] On error: send `event: error` with error code and message
- [ ] Tests (use mocked Gemini):
  - [ ] Send message → receive streamed response
  - [ ] Message in non-existent session → 404
  - [ ] Message in another partner's session → 404
  - [ ] No relevant chunks → no-context response, no LLM call
  - [ ] Gemini failure → error event, message NOT saved
  - [ ] Successful message → student msg + tutor msg both in DB
  - [ ] Usage event logged with correct token counts
- [ ] **Integration test with REAL Gemini API:**
  - [ ] Ingest a real Lithuanian math lesson
  - [ ] Create a session
  - [ ] Send a question
  - [ ] Verify the response is grounded in the lesson content (manually inspect)
  - [ ] Verify Lithuanian grammar quality with a native speaker

**Definition of done:**
- End-to-end test passes with real Gemini API
- Streaming works (you can see tokens arriving in real time via curl)
- Hallucination test passes (asking off-topic questions gets refused)
- Lithuanian quality verified by native speaker
- All error paths handled cleanly

---

## Milestone 6: Polish, Deploy, Document (Day 23–28)

**Goal:** Production-ready deployment + documentation good enough for partners to integrate without help.

- [ ] Add `request_id` middleware (UUID per request, included in all logs and responses)
- [ ] Verify all logs are structured JSON, no plain text logs
- [ ] Verify NO secrets in logs (mask Gemini API key, mask partner API keys)
- [ ] Add `/v1/health` deep check that pings DB and Gemini
- [ ] Add `app/main.py` startup event that runs migrations on boot (or document running them separately)
- [ ] Configure CORS appropriately (locked down by default, configurable per environment)
- [ ] Set up Caddy reverse proxy in docker-compose for production:
  - [ ] HTTPS via Let's Encrypt
  - [ ] Proxy `api.neuropetitorius.com → api:8000`
- [ ] Deploy to Hetzner Cloud:
  - [ ] Provision a CX22 instance in Falkenstein or Helsinki
  - [ ] Install Docker
  - [ ] Set up systemd unit for docker-compose
  - [ ] Set production env vars (real Gemini API key)
  - [ ] Run migrations
  - [ ] Verify health check from outside
- [ ] Write README.md:
  - [ ] Local development setup (5 commands or fewer)
  - [ ] How to run tests
  - [ ] How to deploy
  - [ ] Architecture overview link to ARCHITECTURE.md
- [ ] Write API.md (partner-facing API documentation):
  - [ ] Authentication
  - [ ] All endpoints with curl examples
  - [ ] Error codes
  - [ ] Rate limits
  - [ ] SSE format explanation with JS example
  - [ ] Lithuanian and English examples
- [ ] Write INTEGRATION_GUIDE.md (for partner developers):
  - [ ] "Integrate Neuropetitorius in 1 hour"
  - [ ] Step-by-step from API key → first chat
  - [ ] Code samples in Python and JavaScript
- [ ] Generate one realistic end-to-end demo:
  - [ ] Real Lithuanian math lesson uploaded
  - [ ] Real student questions in Lithuanian
  - [ ] Recorded curl session showing streaming responses
- [ ] Smoke test on production server with real Gemini calls

**Definition of done:**
- Production server is live at api.neuropetitorius.com
- A developer can read the INTEGRATION_GUIDE.md and integrate without asking questions
- Demo recording exists and looks good
- All milestones marked complete

---

## Post-MVP (DO NOT WORK ON THESE YET)

These are tracked here for context only. They are explicitly out of scope for v0.1.

- v0.2: Persistent student memory + weakness tracking
- v0.3: Quiz generation
- v0.4: Flashcard generation with spaced repetition
- v0.5: Webhooks for partner event notifications
- v0.6: Analytics dashboard API
- v0.7: PDF content ingestion
- v0.8: Multi-LLM provider support (Claude failover)
- v0.9: Embeddable chat widget

---

## Daily Working Rhythm

For each task in a milestone:
1. Read the relevant section of `TECH_SPEC.md` and `ARCHITECTURE.md`
2. Implement the smallest possible version
3. Write the test
4. Verify the test passes
5. Run `ruff check .` and `mypy app/` — both must pass
6. Commit with a clear message: `feat(content): implement chunking with overlap`
7. Mark the task `[x]` in this file
8. Move to the next task

When a milestone is complete:
1. Run the full test suite
2. Manually test the new functionality with curl
3. Update README if user-facing changes
4. Tag the commit: `git tag v0.1-milestone-3`
5. Pause and request user review before starting next milestone