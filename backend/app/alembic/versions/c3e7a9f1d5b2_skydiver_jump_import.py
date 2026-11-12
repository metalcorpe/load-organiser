"""Skydiver logbook import from a spreadsheet (owner decision 2026-11-12)

Additive: an import table (one row per completed import, unique per owner and
file fingerprint, numbered per owner), a nullable `import_id` on jumps, and the
jump source check also allows 'imported'. No data change.

Revision ID: c3e7a9f1d5b2
Revises: b9e4d1a7c3f5
Create Date: 2026-11-12
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c3e7a9f1d5b2"
down_revision = "b9e4d1a7c3f5"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def _source(allowed: str) -> None:
    op.drop_constraint("ck_skydiver_jump_source", "skydiver_jump", type_="check")
    op.create_check_constraint(
        "ck_skydiver_jump_source", "skydiver_jump", f"source IN ({allowed})"
    )


def upgrade() -> None:
    op.create_table(
        "skydiver_jump_import",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "owner_person_id",
            UUID,
            sa.ForeignKey("skydiver_person.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("counts", postgresql.JSONB(), nullable=False),
        sa.Column("place_ids", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("undone_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "owner_person_id", "fingerprint", name="uq_skydiver_jump_import"
        ),
        sa.UniqueConstraint(
            "owner_person_id", "sequence", name="uq_skydiver_jump_import_sequence"
        ),
    )
    op.add_column(
        "skydiver_jump",
        sa.Column(
            "import_id",
            UUID,
            sa.ForeignKey(
                "skydiver_jump_import.id",
                ondelete="SET NULL",
                name="skydiver_jump_import_id_fkey",
            ),
            nullable=True,
        ),
    )
    op.create_index("ix_skydiver_jump_import_id", "skydiver_jump", ["import_id"])
    _source("'manual', 'restored', 'imported'")


def downgrade() -> None:
    # Refuses (constraint violation) while imported jumps exist, rather than losing them.
    _source("'manual', 'restored'")
    op.drop_index("ix_skydiver_jump_import_id", table_name="skydiver_jump")
    op.drop_column("skydiver_jump", "import_id")
    op.drop_table("skydiver_jump_import")
