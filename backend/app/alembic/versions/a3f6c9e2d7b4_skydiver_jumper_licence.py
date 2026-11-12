"""Skydiver jumper licence for private currency guidance

Additive only: one new owner-scoped table with no data. The previous code never
reads it; a downgrade drops it (the setting is lost, nothing else). Clearing a
licence deletes its row, so deletions are recorded in the erasure ledger
(migration d4f9b6a2e8c1) like the baseline's: a restore plus a ledger replay
keeps a cleared licence cleared.

Revision ID: a3f6c9e2d7b4
Revises: c3e7a9f1d5b2
Create Date: 2026-11-12
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a3f6c9e2d7b4"
down_revision = "c3e7a9f1d5b2"
branch_labels = None
depends_on = None

TABLE = "skydiver_jumper_licence"
# Same function and trigger naming as migration d4f9b6a2e8c1; the ledger tests
# check the triggers against REPLAY in app/skydiver/recovery/ledger.py.
TRIGGER = f"skydiver_erasure_delete_{TABLE}"[:63]


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column(
            "owner_person_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("skydiver_person.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("licence", sa.String(8), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "licence IN ('student', 'a', 'b', 'c', 'd')",
            name="ck_skydiver_jumper_licence",
        ),
    )
    op.execute(
        f'CREATE TRIGGER {TRIGGER} AFTER DELETE ON "{TABLE}" '
        "FOR EACH ROW EXECUTE FUNCTION skydiver_erasure_record('owner_person_id')"
    )


def downgrade() -> None:
    op.execute(f'DROP TRIGGER {TRIGGER} ON "{TABLE}"')
    op.drop_table(TABLE)
