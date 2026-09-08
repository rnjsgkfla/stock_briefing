"""Add article extraction metadata.

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "news_articles",
        sa.Column(
            "content_source",
            sa.String(length=40),
            nullable=False,
            server_default="provider_summary",
        ),
    )
    op.add_column(
        "news_articles",
        sa.Column(
            "extraction_status",
            sa.String(length=40),
            nullable=False,
            server_default="not_attempted",
        ),
    )
    op.add_column(
        "news_articles",
        sa.Column("content_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "news_articles",
        sa.Column("extracted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("news_articles", "extracted_at")
    op.drop_column("news_articles", "content_hash")
    op.drop_column("news_articles", "extraction_status")
    op.drop_column("news_articles", "content_source")
