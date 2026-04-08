# Neuropetitorius - Technical Specification

## Overview

**Neuropetitorius** is a B2B AI tutoring API platform ("Stripe for AI tutoring") that enables educational platforms to add intelligent, grounded tutoring to their products.

---

## Mission

Enable any educational platform to offer AI-powered tutoring that:
- Answers questions based **only** on provided learning materials
- Supports multiple languages (Lithuanian + English)
- Maintains conversation context per student session
- Scales automatically with partner usage

---

## Architecture

### High-Level Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Partner Platform                          │
│  (Website / App / LMS)                                          │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │ Content     │    │ Session      │    │ Student          │  │
│  │ Management  │───▶│ Management  │───▶│ Chat Interface   │  │
│  └──────────────┘    └──────────────┘    └──────────────────┘  │
│         │                   │                     │             │
└─────────│───────────────────│─────────────────────│─────────────┘
          │                   │                     │
          ▼                   ▼                     ▼
    ┌─────────────────────────────────────────────────────────┐
    │                   Neuropetitorius API                    │
    │                                                          │
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
    │  │ Content    │  │ Session    │  │ AI Tutor        │  │
    │  │ Ingestion  │  │ Management │  │ Engine (RAG)    │  │
    │  └─────────────┘  └─────────────┘  └─────────────────┘  │
    │         │               │                  │              │
    │         ▼               ▼                  ▼              │
    │  ┌─────────────────────────────────────────────────────┐  │
    │  │              PostgreSQL + pgvector                 │  │
    │  │  (Partners, Content, Sessions, Messages, Vectors) │  │
    │  └─────────────────────────────────────────────────────┘  │
    └─────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Gemini API     │
                    │  (AI Model)     │
                    └─────────────────┘
```

---

## Core Concepts

### 1. Content Hierarchy

```
Class → Subject → Chapter → Topic → Content
```

| Field | Description | Example |
|-------|-------------|---------|
| `class_id` | Internal class ID | `grade-10`, `class-5b` |
| `class_name` | Display name | `Grade 10`, `Class 5B` |
| `subject` | Subject area | `Mathematics`, `Physics` |
| `chapter` | Chapter/section | `Algebra Chapter 1` |
| `topic_id` | **Unique** topic identifier | `math-grade10-algebra-ch1` |
| `title` | Content title | `Introduction to Algebra` |
| `content` | Lesson text | `Algebra is a branch...` |

### 2. Content Ingestion

When content is uploaded:

1. **Validation** - Check required fields
2. **Hash** - SHA256 of content for change detection
3. **Chunking** - Split into ~800 token chunks with 150 overlap
4. **Embedding** - Convert each chunk to vector via Gemini Embedding
5. **Storage** - Save to PostgreSQL + pgvector

**Idempotency**: Re-uploading same content = no changes (chunks preserved)

### 3. Sessions

A session represents one student's learning journey:

- Linked to a specific `topic_id`
- Has `student_external_id` (partner's student ID)
- Maintains full conversation history

### 4. AI Tutor (RAG Pipeline)

When a student asks a question:

1. **Embed** - Convert question to vector
2. **Search** - Find top-K similar chunks from the topic
3. **Check relevance** - If no relevant chunks → return "no context" response
4. **Build prompt** - System instruction + retrieved context + question
5. **Generate** - Call Gemini API
6. **Stream** - Return response via SSE
7. **Save** - Store both student message and tutor response

---

## API Endpoints

### Authentication

All requests require: `Authorization: Bearer <api_key>`

### Content

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/content/ingest` | Upload lesson content |
| `GET` | `/v1/content` | List content (with filters) |
| `DELETE` | `/v1/content/{topic_id}` | Delete content |

### Sessions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/sessions` | Create session |
| `GET` | `/v1/sessions/{id}` | Get session + messages |
| `DELETE` | `/v1/sessions/{id}` | Delete session |

### Tutor

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/sessions/{id}/messages` | Send message, get AI response |

---

## Data Models

### Partner
- `id` (UUID)
- `name`
- `slug`
- `api_key_hash`
- `rate_limit_rpm`
- `is_active`

### ContentItem
- `id` (UUID)
- `partner_id` (FK)
- `class_id`
- `class_name`
- `subject`
- `chapter`
- `topic_id` (unique per partner)
- `title`
- `language` (lt/en)
- `raw_content`
- `content_hash`
- `created_at`, `updated_at`

### ContentChunk
- `id` (UUID)
- `content_item_id` (FK)
- `chunk_index`
- `text`
- `embedding` (vector(768))
- `token_count`

### Session
- `id` (UUID)
- `partner_id` (FK)
- `topic_id`
- `student_external_id`
- `title`
- `language`
- `created_at`

### Message
- `id` (UUID)
- `session_id` (FK)
- `role` (student/tutor)
- `content`
- `retrieved_chunk_ids` (JSON)
- `prompt_tokens`
- `completion_tokens`
- `created_at`

---

## Supported Content Formats

### Text
- Plain text in `content` field
- Max 500,000 characters

### Files
| Format | Extension | Notes |
|--------|-----------|-------|
| PDF | `.pdf` | Text extraction |
| Word | `.docx` | Paragraph extraction |
| Excel | `.xlsx`, `.xls` | Row/column data |
| Text | `.txt` | Plain text |
| Images | `.jpg`, `.png` | Metadata only (future: OCR) |

---

## Security

### Multi-Tenancy
- Every query filtered by `partner_id`
- Partners can only access their own data
- Session/Content access checks prevent cross-tenant queries

### API Key
- SHA-256 hashed in database
- Prefix: `npk_` for identification
- Rate limiting: configurable per partner (default 60 req/min)

### Secrets
- Gemini API key: environment variable only
- No secrets logged in output

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| API | FastAPI + Python 3.12 |
| Database | PostgreSQL + pgvector |
| AI | Google Gemini API |
| Deployment | Docker + Docker Compose |

---

## Deployment

### Local Development
```bash
cd THE CODE
docker-compose up -d
```

### Production
```bash
# Build and run
docker-compose -f docker-compose.yml up -d

# Or with production overrides
docker-compose -f docker-compose.yml -f production.yml up -d
```

---

## Future Enhancements

### v0.2
- Student memory across sessions
- Weakness tracking (what topics students struggle with)

### v0.3
- Quiz generation based on content
- Self-assessment support

### v0.4
- Flashcard generation
- Spaced repetition scheduling

### v0.5
- Webhooks for partner notifications
- Event streaming

### v0.6
- Analytics dashboard API
- Usage reporting

### v0.7
- Multi-LLM support
- Claude as failover

### v0.8
- Embeddable chat widget
- JavaScript SDK

---

## Integration Checklist

For partners integrating Neuropetitorius:

- [ ] Get API key
- [ ] Upload first lesson content
- [ ] Implement session creation (when student starts topic)
- [ ] Implement chat interface (SSE for streaming)
- [ ] Add content sync (manual or webhook)
- [ ] Test with real student questions
- [ ] Verify grounding (AI only answers from content)

---

## Support

- Documentation: `/Docs`
- Integration Guide: `/Docs/INTEGRATION_GUIDE.md`
- API Reference: `/Docs/API.md`
- Demo UI: `/Test front/index.html`

---

*Last Updated: April 2026*
