"""Skydiver erasure ledger prune cutoff (architecture A9)

Records the latest prune cutoff in the database, so that a restored backup knows
which older ledger entries it no longer holds. The replay used the oldest held
entry instead, but recording time is not commit order: an entry recorded earlier
and committed after the backup could be wrongly left out. One row, id 1.

Revision ID: e7a3c5d8f2b4
Revises: d4f9b6a2e8c1
Create Date: 2026-11-08
"""

import sqlalchemy as sa
from alembic import op

revision = "e7a3c5d8f2b4"
down_revision = "d4f9b6a2e8c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "skydiver_erasure_ledger_pruned",
        sa.Column("id", sa.SmallInteger(), primary_key=True),
        sa.Column("pruned_before", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_skydiver_erasure_ledger_pruned_one"),
    )


def downgrade() -> None:
    op.drop_table("skydiver_erasure_ledger_pruned")
