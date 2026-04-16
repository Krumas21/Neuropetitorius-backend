"""Mode 1: Just-in-time content delivery.

Revision ID: 004_mode1
Revises: 003_add_allowed_origins
Create Date: 2026-04-15

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "004_mode1"
down_revision: Union[str, None] = "003_add_allowed_origins"
branch: Union[str, None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS content_chunks")
    op.execute("DROP TABLE IF EXISTS content_items")

    op.create_table(
        "session_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", postgresql.Vector(768), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["partner_id"], ["partners.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
    )

    op.create_index("idx_session_chunks_session", "session_chunks", ["session_id"])
    op.create_index("idx_session_chunks_partner", "session_chunks", ["partner_id"])
    op.execute(
        """CREATE INDEX idx_session_chunks_embedding ON session_chunks
           USING hnsw (embedding vector_cosine_ops)
           WITH (m = 16, ef_construction = 64)"""
    )

    op.create_table(
        "embedding_cache",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("content_hash", sa.Text(), nullable=False, unique=True),
        sa.Column("chunks", postgresql.JSONB(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("hit_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "first_cached_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_used_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_index(
        "idx_embedding_cache_last_used",
        "embedding_cache",
        ["last_used_at"],
    )

    op.add_column("sessions", sa.Column("content_title", sa.Text(), nullable=True))
    op.add_column("sessions", sa.Column("content_subject", sa.Text(), nullable=True))
    op.add_column("sessions", sa.Column("content_fingerprint", sa.Text(), nullable=True))
    op.add_column("sessions", sa.Column("content_length", sa.Integer(), nullable=True))
    op.drop_column("sessions", "topic_id")


def downgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("topic_id", sa.String(256), nullable=False),
    )
    op.drop_column("sessions", "content_title")
    op.drop_column("sessions", "content_subject")
    op.drop_column("sessions", "content_fingerprint")
    op.drop_column("sessions", "content_length")

    op.drop_index("idx_embedding_cache_last_used", "embedding_cache")
    op.drop_table("embedding_cache")
    op.drop_index("idx_session_chunks_embedding")
    op.drop_index("idx_session_chunks_partner")
    op.drop_index("idx_session_chunks_session")
    op.drop_table("session_chunks")

    op.execute(
        """CREATE TABLE content_items (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
        class_id VARCHAR(64),
        class_name VARCHAR(128),
        subject VARCHAR(64),
        chapter VARCHAR(256),
        topic_id VARCHAR(256) NOT NULL,
        title VARCHAR(512) NOT NULL,
        language VARCHAR(10) DEFAULT 'lt',
        raw_content TEXT NOT NULL,
        content_hash VARCHAR(64) NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE(partner_id, topic_id)
    )"""
    )

    op.execute(
        """CREATE TABLE content_chunks (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        partner_id UUID NOT NULL REFERENCES partners(id) ON DELETE CASCADE,
        content_item_id UUID NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
        chunk_index INTEGER NOT NULL,
        text TEXT NOT NULL,
        embedding TEXT NOT NULL,
        token_count INTEGER NOT NULL,
        created_at TIMESTAMPTZ DEFAULT NOW()
    )"""
    )

    op.execute("CREATE INDEX idx_content_chunks_item ON content_chunks(content_item_id)")
    op.execute("CREATE INDEX idx_content_chunks_partner ON content_chunks(partner_id)")
