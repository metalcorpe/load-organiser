"""Skydiver wing loading: canopy size, usual exit weight, exit weight per jump

Additive only, with no data:

- skydiver_component.canopy_size_sqft: a main or reserve canopy's size in square
  feet (nullable, checked);
- skydiver_jump.exit_weight_grams: the exit weight on that jump (nullable,
  checked);
- skydiver_exit_weight: one new owner-scoped table holding the jumper's usual
  exit weight in grams and the unit it was entered in. No row: none set;
- skydiver_person.weight_unit: the unit the jumper last chose (kg or lb), a
  display preference with no weight in it, kept when the weight is cleared.

The previous code never reads or writes any of them, so it keeps working during
a rollover. Clearing the usual exit weight deletes its row, so the deletion is
recorded in the erasure ledger (migration d4f9b6a2e8c1's function, owner key
only, never the weight), like the licence's (migration a3f6c9e2d7b4): a restore
plus a ledger replay keeps a cleared weight cleared. A per-jump exit weight is a
column of the jump: cleared by an edit (not an erasure), it reverts with a
restore like other jump fields, and goes with the jump when the jump is deleted.
A downgrade drops all of them (the sizes and weights are lost, nothing else).

Revision ID: e8b3d5f1a7c4
Revises: d6e1f4b8a2c9
Create Date: 2026-11-12
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "e8b3d5f1a7c4"
down_revision = "d6e1f4b8a2c9"
branch_labels = None
depends_on = None

TABLE = "skydiver_exit_weight"
# Same function and trigger naming as migration d4f9b6a2e8c1; the ledger tests
# check the triggers against REPLAY in app/skydiver/recovery/ledger.py.
TRIGGER = f"skydiver_erasure_delete_{TABLE}"[:63]


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
        "skydiver_person", sa.Column("weight_unit", sa.String(length=2), nullable=True)
    )
    op.create_check_constraint(
        "ck_skydiver_person_weight_unit",
        "skydiver_person",
        "weight_unit IS NULL OR weight_unit IN ('kg', 'lb')",
    )
    op.create_table(
        TABLE,
        sa.Column(
            "owner_person_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("skydiver_person.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("grams", sa.Integer(), nullable=False),
        sa.Column("unit", sa.String(2), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "grams BETWEEN 30000 AND 250000", name="ck_skydiver_exit_weight_grams"
        ),
        sa.CheckConstraint("unit IN ('kg', 'lb')", name="ck_skydiver_exit_weight_unit"),
    )
    op.execute(
        f'CREATE TRIGGER {TRIGGER} AFTER DELETE ON "{TABLE}" '
        "FOR EACH ROW EXECUTE FUNCTION skydiver_erasure_record('owner_person_id')"
    )


def downgrade() -> None:
    op.execute(f'DROP TRIGGER {TRIGGER} ON "{TABLE}"')
    op.drop_table(TABLE)
    op.drop_constraint(
        "ck_skydiver_person_weight_unit", "skydiver_person", type_="check"
    )
    op.drop_column("skydiver_person", "weight_unit")
    op.drop_constraint("ck_skydiver_jump_exit_weight", "skydiver_jump", type_="check")
    op.drop_column("skydiver_jump", "exit_weight_grams")
    op.drop_constraint(
        "ck_skydiver_component_canopy_size", "skydiver_component", type_="check"
    )
    op.drop_column("skydiver_component", "canopy_size_sqft")
