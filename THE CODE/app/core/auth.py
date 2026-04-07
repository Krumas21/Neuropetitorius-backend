"""API key authentication utilities."""

import base64
import hashlib
import secrets


def hash_api_key(raw_key: str) -> str:
    """Hash an API key using SHA-256."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    """Generate a new API key.

    Returns:
        tuple of (raw_key, hash, prefix)
    """
    raw = secrets.token_bytes(32)
    raw_key = base64.urlsafe_b64encode(raw).decode("utf-8")
    raw_key = f"npk_{raw_key[:40]}"
    key_hash = hash_api_key(raw_key)
    prefix = raw_key[:12]
    return raw_key, key_hash, prefix


def verify_api_key(raw_key: str, stored_hash: str) -> bool:
    """Verify an API key against a stored hash."""
    return hash_api_key(raw_key) == stored_hash
