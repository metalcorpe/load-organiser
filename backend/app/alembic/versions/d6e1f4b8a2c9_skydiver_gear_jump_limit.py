"""Skydiver gear jump limit: one optional jump-count limit per component

Additive only: three nullable columns on skydiver_component (the limit, the
owner's label for it and the service kind that restarts the count), all empty
or all set, with no data. The previous code never reads or writes them, so it
keeps working during a rollover; a downgrade drops them (the owner's limits are
lost, nothing else). No new table and no new deletions, so the erasure ledger
is unchanged: a component's deletion is already recorded.

Revision ID: d6e1f4b8a2c9
Revises: c5d9e3a7f1b2
Create Date: 2026-11-12
"""

import sqlalchemy as sa
from alembic import op

revision = "d6e1f4b8a2c9"
down_revision = "c5d9e3a7f1b2"
branch_labels = None
depends_on = None

TABLE = "skydiver_component"
CHECK = "ck_skydiver_component_jump_limit"


def upgrade() -> None:
    op.add_column(TABLE, sa.Column("jump_limit", sa.Integer(), nullable=True))
    op.add_column(
        TABLE, sa.Column("jump_limit_label", sa.String(length=80), nullable=True)
    )
    op.add_column(
        TABLE,
        sa.Column("jump_limit_service_kind", sa.String(length=16), nullable=True),
    )
    op.create_check_constraint(
        CHECK,
        TABLE,
        "(jump_limit IS NULL AND jump_limit_label IS NULL"
        " AND jump_limit_service_kind IS NULL)"
        " OR (jump_limit BETWEEN 1 AND 100000 AND jump_limit_label IS NOT NULL"
        " AND jump_limit_service_kind IN"
        " ('repack', 'inspection', 'maintenance', 'aad_service', 'other'))",
    )


def downgrade() -> None:
    op.drop_constraint(CHECK, TABLE, type_="check")
    op.drop_column(TABLE, "jump_limit_service_kind")
    op.drop_column(TABLE, "jump_limit_label")
    op.drop_column(TABLE, "jump_limit")
