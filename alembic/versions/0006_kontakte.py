"""Kontaktanfragen von der Homepage

Revision ID: 0006_kontakte
Revises: 0005_besucher_zaehler
Create Date: 2026-09-27

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_kontakte"
down_revision: str | None = "0005_besucher_zaehler"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "kontakte",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("vorname", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("betreff", sa.String(200), nullable=False),
        sa.Column("nachricht", sa.Text(), nullable=False),
        sa.Column("createdAt", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("updatedAt", sa.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("kontakte")
