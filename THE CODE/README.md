# Neuropetitorius Backend

B2B AI tutoring API for educational platforms.

## Quick Start

```bash
# Start the stack
docker-compose up --build

# Check health
curl http://localhost:8000/v1/health
```

## Development

```bash
# Install dependencies
uv sync

# Run linter
ruff check .

# Run type checker
mypy app/

# Run tests
pytest
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

- `DATABASE_URL` - PostgreSQL connection string
- `GEMINI_API_KEY` - Google Gemini API key
- `GEMINI_GENERATION_MODEL` - Model for text generation
- `GEMINI_EMBEDDING_MODEL` - Model for embeddings