"""Datensparsame Besuchersitzungen und Seitenaufrufe."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008_besucher_statistik"
down_revision: str | None = "0007_anmeldung_adresseid"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "besucher_sitzung",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("duration_observed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("country", sa.String(2), nullable=True),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("referrer_host", sa.String(253), nullable=True),
        sa.Column("entry_path", sa.String(100), nullable=False),
        sa.Column("device", sa.String(20), nullable=False),
        sa.Column("browser", sa.String(20), nullable=False),
    )
    op.create_index("ix_besucher_sitzung_started_at", "besucher_sitzung", ["started_at"])
    op.create_table(
        "besucher_seite",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("besucher_sitzung.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("path", sa.String(100), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )
    op.create_index("ix_besucher_seite_session_id", "besucher_seite", ["session_id"])


def downgrade() -> None:
    op.drop_table("besucher_seite")
    op.drop_table("besucher_sitzung")
