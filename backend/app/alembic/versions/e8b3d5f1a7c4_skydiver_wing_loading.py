"""Skydiver wing loading: canopy size, usual exit weight, exit weight per jump

Additive only, with no data: one nullable column on skydiver_component (a main or
reserve canopy's size in square feet), one on skydiver_jump (the exit weight on
that jump, in grams) and two on skydiver_person (the jumper's usual exit weight in
grams and the unit it was entered in), each with a check constraint that every
existing row passes (all are null). The previous code never reads or writes them,
so it keeps working during a rollover; a downgrade drops them (the sizes and
weights are lost, nothing else).

The usual exit weight sits on the person row rather than in
skydiver_jumper_licence: a weight without a licence would need a licence row
without a licence, which the previous code cannot read. No new table and no new
deletions (clearing a weight is an update), so the erasure ledger is unchanged.

Revision ID: e8b3d5f1a7c4
Revises: d6e1f4b8a2c9
Create Date: 2026-11-12
"""

import sqlalchemy as sa
from alembic import op

revision = "e8b3d5f1a7c4"
down_revision = "d6e1f4b8a2c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "skydiver_component",
        sa.Column("canopy_size_sqft", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "ck_skydiver_component_canopy_size",
        "skydiver_component",
        "canopy_size_sqft IS NULL OR (canopy_size_sqft BETWEEN 20 AND 400"
        " AND kind IN ('main', 'reserve'))",
    )
    op.add_column(
        "skydiver_jump", sa.Column("exit_weight_grams", sa.Integer(), nullable=True)
    )
    op.create_check_constraint(
        "ck_skydiver_jump_exit_weight",
        "skydiver_jump",
        "exit_weight_grams IS NULL OR exit_weight_grams BETWEEN 30000 AND 250000",
    )
    op.add_column(
        "skydiver_person", sa.Column("exit_weight_grams", sa.Integer(), nullable=True)
    )
    op.add_column(
        "skydiver_person",
        sa.Column("exit_weight_unit", sa.String(length=2), nullable=True),
    )
    op.create_check_constraint(
        "ck_skydiver_person_exit_weight",
        "skydiver_person",
        "(exit_weight_grams IS NULL AND exit_weight_unit IS NULL)"
        " OR (exit_weight_grams BETWEEN 30000 AND 250000"
        " AND exit_weight_unit IN ('kg', 'lb'))",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_skydiver_person_exit_weight", "skydiver_person", type_="check"
    )
    op.drop_column("skydiver_person", "exit_weight_unit")
    op.drop_column("skydiver_person", "exit_weight_grams")
    op.drop_constraint("ck_skydiver_jump_exit_weight", "skydiver_jump", type_="check")
    op.drop_column("skydiver_jump", "exit_weight_grams")
    op.drop_constraint(
        "ck_skydiver_component_canopy_size", "skydiver_component", type_="check"
    )
    op.drop_column("skydiver_component", "canopy_size_sqft")
