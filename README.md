# Neuropetitorius - AI Tutor API

B2B AI tutoring platform ("Stripe for AI tutoring") for educational platforms.

---

## Quick Start

### 1. Start the API

```bash
cd THE\ CODE
docker-compose up -d
```

The API will be running at `http://localhost:8000`

### 2. Access the Demo UI

Open in your browser:
```
file:///Users/pc/Documents/Business/Neuropetitorius%20B2B/test/Test%20front/index.html
```

Or serve it locally:
```bash
cd "Test front"
python3 -m http.server 8080
# Then open http://localhost:8080
```

### 3. Test API Key

The demo UI is pre-configured with a test API key:
```
npk_xy1rLr38P-UIqA1YCM1zxmr4vXM5K3-dZ5DSHcRU
```

---

## Features

- **Content Ingestion** - Upload lessons as text or files (PDF, DOCX, XLSX)
- **AI Tutoring** - RAG-powered tutor that answers from your content
- **Session Management** - Track student conversations
- **Multi-language** - Lithuanian + English support
- **Grounding** - AI only answers from uploaded content (no hallucinations)

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `POST /v1/content/ingest` | Upload lesson content |
| `DELETE /v1/content/{topic_id}` | Delete content |
| `POST /v1/sessions` | Create tutoring session |
| `GET /v1/sessions/{id}` | Get session with messages |
| `DELETE /v1/sessions/{id}` | Delete session |
| `POST /v1/sessions/{id}/messages` | Chat with AI tutor |
| `GET /v1/health` | Health check |

---

## Development

### Prerequisites
- Docker + Docker Compose
- Python 3.12+ (for local development)

### Local Setup

```bash
# 1. Clone and setup
cd THE\ CODE

# 2. Start services
docker-compose up -d

# 3. Run tests
pytest

# 4. Check code quality
ruff check .
mypy app/
```

### Environment Variables

Create `.env`:
```
DATABASE_URL=postgresql+asyncpg://neuro:neuro_dev_password@localhost:5432/neuro
GEMINI_API_KEY=your_gemini_api_key
GEMINI_GENERATION_MODEL=gemini-3-flash-preview
GEMINI_EMBEDDING_MODEL=gemini-embedding-001
```

---

## Documentation

- [API Documentation](Docs/API.md)
- [Integration Guide](Docs/INTEGRATION_GUIDE.md)

---

## Tech Stack

- **Backend**: FastAPI + Python 3.12
- **Database**: PostgreSQL + pgvector
- **AI**: Google Gemini API
- **Deployment**: Docker

---

## License

Proprietary - All rights reserved