"""Anlaesse: Flag istmotorrad (nur Homepage, keine Meisterschaft)

Revision ID: 0004_istmotorrad
Revises: 0003_beschreibung_text
Create Date: 2026-09-25

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_istmotorrad"
down_revision: str | None = "0003_beschreibung_text"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "anlaesse",
        sa.Column("istmotorrad", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("anlaesse", "istmotorrad")
