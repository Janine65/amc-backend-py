"""Homepage-Tabellen: news, berichte, anlass_anmeldungen, jahr_freigabe

Revision ID: 0001_homepage
Revises:
Create Date: 2026-09-18

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_homepage"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "news",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("titel", sa.String(150), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("bild", sa.String(255), nullable=True),
        sa.Column("datum", sa.Date(), nullable=False),
        sa.Column("publiziert", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("createdAt", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("updatedAt", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_table(
        "berichte",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("titel", sa.String(150), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("datei", sa.String(255), nullable=True),
        sa.Column("datum", sa.Date(), nullable=False),
        sa.Column("publiziert", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("createdAt", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("updatedAt", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_table(
        "anlass_anmeldungen",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column(
            "anlassid",
            sa.Integer(),
            sa.ForeignKey("anlaesse.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("vorname", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("bemerkung", sa.String(500), nullable=True),
        sa.Column("status", sa.SmallInteger(), nullable=False, server_default="1"),
        sa.Column("createdAt", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("updatedAt", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.UniqueConstraint("anlassid", "email", name="anmeldung_unique"),
    )
    op.create_table(
        "jahr_freigabe",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column("jahr", sa.String(4), nullable=False, unique=True),
        sa.Column("clubmeister", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("kegelmeister", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("createdAt", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("updatedAt", sa.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("jahr_freigabe")
    op.drop_table("anlass_anmeldungen")
    op.drop_table("berichte")
    op.drop_table("news")
