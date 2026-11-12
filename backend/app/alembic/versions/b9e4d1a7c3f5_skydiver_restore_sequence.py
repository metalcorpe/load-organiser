"""Skydiver restore receipts get a per-person sequence (#160 restore race)

Two restores of different files into the same empty records could both pass
the emptiness check and both commit, merging two archives. Each restore now
claims the next sequence number for its person; the unique (owner, sequence)
pair lets only one of two simultaneous restores commit (compare-and-swap, no
lock). Existing receipts are numbered by time.

Revision ID: b9e4d1a7c3f5
Revises: a8d2f6c4e1b7
Create Date: 2026-11-11
"""

import sqlalchemy as sa
from alembic import op

revision = "b9e4d1a7c3f5"
down_revision = "a8d2f6c4e1b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "skydiver_restore_receipt", sa.Column("sequence", sa.Integer(), nullable=True)
    )
    op.execute(
        """
        UPDATE skydiver_restore_receipt AS r SET sequence = n.seq
        FROM (
            SELECT id, row_number() OVER (
                PARTITION BY owner_person_id ORDER BY created_at, id
            ) AS seq
            FROM skydiver_restore_receipt
        ) AS n
        WHERE r.id = n.id
        """
    )
    op.alter_column("skydiver_restore_receipt", "sequence", nullable=False)
    op.create_unique_constraint(
        "uq_skydiver_restore_receipt_sequence",
        "skydiver_restore_receipt",
        ["owner_person_id", "sequence"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_skydiver_restore_receipt_sequence",
        "skydiver_restore_receipt",
        type_="unique",
    )
    op.drop_column("skydiver_restore_receipt", "sequence")
