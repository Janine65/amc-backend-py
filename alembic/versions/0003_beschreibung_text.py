"""Anlaesse: beschreibung von VARCHAR(100) auf TEXT erweitern

Revision ID: 0003_beschreibung_text
Revises: 0002_anlass_details
Create Date: 2026-09-18

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_beschreibung_text"
down_revision: str | None = "0002_anlass_details"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "anlaesse",
        "beschreibung",
        existing_type=sa.String(100),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "anlaesse",
        "beschreibung",
        existing_type=sa.Text(),
        type_=sa.String(100),
        existing_nullable=True,
    )
