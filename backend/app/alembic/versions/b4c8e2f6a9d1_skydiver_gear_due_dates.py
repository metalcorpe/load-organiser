"""Skydiver gear due dates: a reserve repack interval and an end-of-life date

Additive only: two nullable columns on skydiver_component, with no data. The
previous code never reads them; a downgrade drops them (the owner's interval and
end-of-life date are lost, nothing else). No new table and no new deletions, so
the erasure ledger is unchanged: a component's deletion is already recorded.

Revision ID: b4c8e2f6a9d1
Revises: a3f6c9e2d7b4
Create Date: 2026-11-12
"""

import sqlalchemy as sa
from alembic import op

revision = "b4c8e2f6a9d1"
down_revision = "a3f6c9e2d7b4"
branch_labels = None
depends_on = None

TABLE = "skydiver_component"
CHECK = "ck_skydiver_component_repack_interval"


def upgrade() -> None:
    op.add_column(TABLE, sa.Column("repack_interval_days", sa.Integer(), nullable=True))
    op.add_column(TABLE, sa.Column("end_of_life_on", sa.Date(), nullable=True))
    op.create_check_constraint(
        CHECK,
        TABLE,
        "repack_interval_days IS NULL OR repack_interval_days BETWEEN 1 AND 730",
    )


def downgrade() -> None:
    op.drop_constraint(CHECK, TABLE, type_="check")
    op.drop_column(TABLE, "end_of_life_on")
    op.drop_column(TABLE, "repack_interval_days")
