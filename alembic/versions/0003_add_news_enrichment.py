"""Add Korean news summary and category.

Revision ID: 0003
Revises: 0002
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("news_articles", sa.Column("korean_summary", sa.Text(), nullable=True))
    op.add_column(
        "news_articles",
        sa.Column("category", sa.String(length=40), nullable=False, server_default="기타"),
    )


def downgrade() -> None:
    op.drop_column("news_articles", "category")
    op.drop_column("news_articles", "korean_summary")
