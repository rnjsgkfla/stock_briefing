"""Create news articles table.

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "news_articles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("external_id", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("source_url", sa.String(length=2000), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("symbols", sa.JSON(), nullable=False),
        sa.Column("sentiment", sa.String(length=40), nullable=True),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_news_articles_external_id"), "news_articles", ["external_id"], unique=True
    )
    op.create_index(
        op.f("ix_news_articles_published_at"), "news_articles", ["published_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_news_articles_published_at"), table_name="news_articles")
    op.drop_index(op.f("ix_news_articles_external_id"), table_name="news_articles")
    op.drop_table("news_articles")
