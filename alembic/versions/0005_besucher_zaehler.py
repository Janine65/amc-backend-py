"""Besucherzähler für die Homepage

Revision ID: 0005_besucher_zaehler
Revises: 0004_istmotorrad
Create Date: 2026-09-27

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_besucher_zaehler"
down_revision: str | None = "0004_istmotorrad"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "besucher_zaehler",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("zaehler", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("updatedAt", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.execute("INSERT INTO besucher_zaehler (id, zaehler) VALUES (1, 0)")


def downgrade() -> None:
    op.drop_table("besucher_zaehler")
