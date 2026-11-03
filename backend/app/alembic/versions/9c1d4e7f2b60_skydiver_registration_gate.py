"""Skydiver registration gate for compare-and-swap registration

Replaces the transaction-scoped advisory lock (architecture A6: no advisory
locks). Adds one structural row (id 1, version 0); no account data.

Revision ID: 9c1d4e7f2b60
Revises: 7e4c2b9d1a53
Create Date: 2026-11-03
"""

import sqlalchemy as sa
from alembic import op

revision = "9c1d4e7f2b60"
down_revision = "7e4c2b9d1a53"
branch_labels = None
depends_on = None


def upgrade() -> None:
    gate = op.create_table(
        "skydiver_registration_gate",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="0"),
        sa.CheckConstraint("id = 1", name="skydiver_registration_gate_single"),
    )
    op.bulk_insert(gate, [{"id": 1, "version": 0}])


def downgrade() -> None:
    op.drop_table("skydiver_registration_gate")
