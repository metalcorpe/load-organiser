"""Skydiver personal export/restore: restore receipts, restored source (#155)

Additive: a receipt table, and the jump/baseline source checks also allow
'restored' (records re-created from the owner's own export). No data change.

Revision ID: f5b8d2e1c4a7
Revises: e4a7c1d9b2f6
Create Date: 2026-11-03
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f5b8d2e1c4a7"
down_revision = "e4a7c1d9b2f6"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def _source(table: str, name: str, allowed: str) -> None:
    op.drop_constraint(name, table, type_="check")
    op.create_check_constraint(name, table, f"source IN ({allowed})")


def upgrade() -> None:
    op.create_table(
        "skydiver_restore_receipt",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "owner_person_id",
            UUID,
            sa.ForeignKey("skydiver_person.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("format_version", sa.Integer(), nullable=False),
        sa.Column("counts", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "owner_person_id", "fingerprint", name="uq_skydiver_restore_receipt"
        ),
    )
    _source("skydiver_jump", "ck_skydiver_jump_source", "'manual', 'restored'")
    _source(
        "skydiver_jump_baseline", "ck_skydiver_baseline_source", "'manual', 'restored'"
    )


def downgrade() -> None:
    # Refuses (constraint violation) while restored rows exist, rather than losing them.
    _source("skydiver_jump_baseline", "ck_skydiver_baseline_source", "'manual'")
    _source("skydiver_jump", "ck_skydiver_jump_source", "'manual'")
    op.drop_table("skydiver_restore_receipt")
