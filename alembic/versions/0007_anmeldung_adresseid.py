"""Anmeldungen: Verknüpfung zur Adresse (adresseid)

Revision ID: 0007_anmeldung_adresseid
Revises: 0006_kontakte
Create Date: 2026-09-27

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_anmeldung_adresseid"
down_revision: str | None = "0006_kontakte"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "anlass_anmeldungen",
        sa.Column("adresseid", sa.Integer(), sa.ForeignKey("adressen.id", ondelete="SET NULL"), nullable=True),
    )
    # Bestehende Anmeldungen automatisch verknüpfen (Name, Vorname, E-Mail)
    op.execute(
        """
        UPDATE anlass_anmeldungen am
        SET adresseid = a.id
        FROM adressen a
        WHERE am.adresseid IS NULL
          AND lower(a.name) = lower(am.name)
          AND lower(a.vorname) = lower(am.vorname)
          AND lower(a.email) = lower(am.email)
        """
    )


def downgrade() -> None:
    op.drop_column("anlass_anmeldungen", "adresseid")
