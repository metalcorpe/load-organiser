"""Skydiver general feedback submissions (#162)

Adds the `feedback` kind to submissions: a message about the beta itself, with no
listing target, reviewed in the existing submissions queue. Downgrade deletes
feedback submissions, which the older constraint does not allow.

Revision ID: f1c4e8a6b3d2
Revises: d4f9b6a2e8c1
Create Date: 2026-11-08
"""

from alembic import op

revision = "f1c4e8a6b3d2"
down_revision = "d4f9b6a2e8c1"
branch_labels = None
depends_on = None

TABLE = "skydiver_submission"
CHECK = "ck_skydiver_submission_kind"


def upgrade() -> None:
    op.drop_constraint(CHECK, TABLE, type_="check")
    op.create_check_constraint(
        CHECK,
        TABLE,
        "kind IN ('suggest_venue', 'suggest_listing', 'correction', 'report', 'feedback')",
    )


def downgrade() -> None:
    op.execute("DELETE FROM skydiver_submission WHERE kind = 'feedback'")
    op.drop_constraint(CHECK, TABLE, type_="check")
    op.create_check_constraint(
        CHECK,
        TABLE,
        "kind IN ('suggest_venue', 'suggest_listing', 'correction', 'report')",
    )
