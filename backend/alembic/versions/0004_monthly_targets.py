"""monthly_targets table.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-16
"""

import app.models  # noqa: F401 — register metadata
from alembic import op
from app.db.session import Base

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS monthly_targets")
