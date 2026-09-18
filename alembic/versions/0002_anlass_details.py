"""Anlaesse: Homepage-Felder zeit_von, zeit_bis, ort

Revision ID: 0002_anlass_details
Revises: 0001_homepage
Create Date: 2026-09-18

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_anlass_details"
down_revision: str | None = "0001_homepage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("anlaesse", sa.Column("zeit_von", sa.Time(), nullable=True))
    op.add_column("anlaesse", sa.Column("zeit_bis", sa.Time(), nullable=True))
    op.add_column("anlaesse", sa.Column("ort", sa.String(150), nullable=True))


def downgrade() -> None:
    op.drop_column("anlaesse", "ort")
    op.drop_column("anlaesse", "zeit_bis")
    op.drop_column("anlaesse", "zeit_von")
