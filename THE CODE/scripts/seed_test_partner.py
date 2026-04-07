"""Script to seed a test partner."""

import asyncio

from app.core.auth import generate_api_key
from app.db.repositories.partner_repo import partner_repo
from app.db.session import get_session_maker, init_db


async def seed_test_partner():
    """Create a test partner with an API key."""
    init_db()
    session_maker = get_session_maker()

    raw_key, key_hash, prefix = generate_api_key()

    async with session_maker() as db:
        partner = await partner_repo.create(
            db,
            name="Test Partner",
            slug="test-partner",
            api_key_hash=key_hash,
            api_key_prefix=prefix,
            contact_email="test@example.com",
        )

    print(f"Partner created: {partner.id}")
    print(f"API Key (save this!): {raw_key}")
    print(f"API Key Prefix (for display): {prefix}")


if __name__ == "__main__":
    asyncio.run(seed_test_partner())
