"""Add class hierarchy fields to content_items.

Revision ID: 002
Revises: 001
Create Date: 2026-04-07

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("content_items", sa.Column("class_id", sa.String(64), nullable=True))
    op.add_column("content_items", sa.Column("class_name", sa.String(128), nullable=True))
    op.add_column("content_items", sa.Column("chapter", sa.String(256), nullable=True))


def downgrade() -> None:
    op.drop_column("content_items", "chapter")
    op.drop_column("content_items", "class_name")
    op.drop_column("content_items", "class_id")
