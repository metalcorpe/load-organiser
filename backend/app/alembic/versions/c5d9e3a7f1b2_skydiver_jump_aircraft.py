"""Skydiver jump aircraft: an optional free-text aircraft on each jump

Additive only: one nullable column on skydiver_jump, with no data. The previous
code never reads or writes it, so it keeps working during a rollover; a
downgrade drops it (the aircraft text is lost, nothing else). No new table and
no new deletions, so the erasure ledger is unchanged: a jump's deletion is
already recorded.

Revision ID: c5d9e3a7f1b2
Revises: b4c8e2f6a9d1
Create Date: 2026-11-12
"""

import sqlalchemy as sa
from alembic import op

revision = "c5d9e3a7f1b2"
down_revision = "b4c8e2f6a9d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "skydiver_jump", sa.Column("aircraft", sa.String(length=60), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("skydiver_jump", "aircraft")
