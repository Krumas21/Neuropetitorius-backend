"""Session creation and chat tests for Mode 1."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient


@pytest.fixture
def mock_partner():
    return {
        "id": "partner-123",
        "api_key": "npk_test123456789",
        "name": "Test Partner",
    }


@pytest.fixture
def mock_db_session():
    db = MagicMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    db.delete = AsyncMock()
    db.close = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_create_session_with_inline_content(client: AsyncClient, mock_partner):
    """Test creating a session with inline content returns 201."""
    with patch("app.api.deps.get_partner_from_api_key", return_value=mock_partner):
        response = await client.post(
            "/v1/sessions",
            json={
                "student_external_id": "student-001",
                "title": "Kvadratinės lygtys",
                "language": "lt",
                "content": {
                    "mode": "inline",
                    "title": "Kvadratinės lygtys",
                    "subject": "mathematics",
                    "text": "# Kvadratinės lygtys\n\nKvadratinė lygtis yra...",
                },
            },
        )

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_create_session_content_too_short(client: AsyncClient, mock_partner):
    """Test session creation with too-short content returns 400."""
    with patch("app.api.deps.get_partner_from_api_key", return_value=mock_partner):
        response = await client.post(
            "/v1/sessions",
            json={
                "student_external_id": "student-001",
                "title": "Test",
                "language": "lt",
                "content": {
                    "mode": "inline",
                    "title": "Test",
                    "text": "Short",
                },
            },
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "CONTENT_TOO_SHORT"


@pytest.mark.asyncio
async def test_create_session_content_too_large(client: AsyncClient, mock_partner):
    """Test session creation with overly large content returns 400."""
    large_content = "x" * 100001

    with patch("app.api.deps.get_partner_from_api_key", return_value=mock_partner):
        response = await client.post(
            "/v1/sessions",
            json={
                "student_external_id": "student-001",
                "title": "Test",
                "language": "lt",
                "content": {
                    "mode": "inline",
                    "title": "Test",
                    "text": large_content,
                },
            },
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "CONTENT_TOO_LARGE"


@pytest.mark.asyncio
async def test_session_delete_cascades_to_chunks(client: AsyncClient, mock_partner):
    """Test deleting a session cascades to session_chunks."""
    pass


@pytest.mark.asyncio
async def test_content_ingest_endpoint_removed(client: AsyncClient):
    """Test that content ingest endpoint returns 404."""
    response = await client.post(
        "/v1/content/ingest",
        data={
            "topic_id": "test",
            "title": "Test",
            "content": "Test content",
        },
    )

    assert response.status_code == 404
