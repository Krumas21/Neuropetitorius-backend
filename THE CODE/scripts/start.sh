#!/bin/bash
set -e
cd /app

echo "Starting uvicorn..."
exec /app/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000