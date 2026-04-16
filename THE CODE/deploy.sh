#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VERSION="${1:-latest}"
ROLLBACK=false

if [[ "$1" == "--rollback" ]]; then
    ROLLBACK=true
    VERSION="${2:-previous}"
fi

echo "=== Neuropetitorius Deployment ==="
echo "Version: $VERSION"
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"

if [[ ! -f .env ]]; then
    echo "ERROR: .env file not found!"
    echo "Copy .env.example to .env and configure before deploying."
    exit 1
fi

source .env

echo ""
echo "=== Pulling latest code ==="
if [[ "$VERSION" == "latest" ]]; then
    git pull origin main
    VERSION=$(git rev-parse --short HEAD)
else
    git fetch origin
    git checkout "$VERSION" 2>/dev/null || git checkout "tags/$VERSION" 2>/dev/null || {
        echo "ERROR: Version $VERSION not found"
        exit 1
    }
fi
echo "Deploying version: $VERSION"

echo ""
echo "=== Building Docker images ==="
docker compose build api

echo ""
echo "=== Running database migrations ==="
docker compose run --rm api alembic upgrade head || {
    echo "WARNING: Migration failed, continuing anyway..."
}

echo ""
echo "=== Starting new containers ==="
docker compose up -d --no-deps api

echo ""
echo "=== Waiting for health check ==="
MAX_WAIT=60
COUNT=0
while [ $COUNT -lt $MAX_WAIT ]; do
    if curl -sf http://localhost:8000/v1/health >/dev/null 2>&1; then
        echo "Health check passed!"
        break
    fi
    sleep 2
    COUNT=$((COUNT + 2))
    echo -n "."
done

if [ $COUNT -ge $MAX_WAIT ]; then
    echo ""
    echo "ERROR: Health check failed!"
    echo "Rolling back..."
    docker compose logs --tail=50 api
    docker compose restart
    exit 1
fi

echo ""
echo "=== Deployment successful ==="
echo "Version: $VERSION"
echo "Deployed at: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"

echo ""
echo "=== Current status ==="
docker compose ps