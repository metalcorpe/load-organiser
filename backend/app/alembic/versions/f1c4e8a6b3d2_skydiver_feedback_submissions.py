"""Skydiver general feedback submissions (#162)

Adds the `feedback` kind to submissions: a message about the beta itself, with no
listing target, reviewed in the existing submissions queue. Downgrade deletes
feedback submissions, which the older constraint does not allow.

Revision ID: f1c4e8a6b3d2
Revises: e7a3c5d8f2b4
Create Date: 2026-11-08
"""

from alembic import op

revision = "f1c4e8a6b3d2"
down_revision = "e7a3c5d8f2b4"
branch_labels = None
depends_on = None

TABLE = "skydiver_submission"
CHECK = "ck_skydiver_submission_kind"
UNTARGETED = "ck_skydiver_submission_feedback_untargeted"


def upgrade() -> None:
    op.drop_constraint(CHECK, TABLE, type_="check")
    op.create_check_constraint(
        CHECK,
        TABLE,
        "kind IN ('suggest_venue', 'suggest_listing', 'correction', 'report', 'feedback')",
    )
    op.create_check_constraint(
        UNTARGETED, TABLE, "kind <> 'feedback' OR target_id IS NULL"
    )


def downgrade() -> None:
    op.drop_constraint(UNTARGETED, TABLE, type_="check")
    op.execute("DELETE FROM skydiver_submission WHERE kind = 'feedback'")
    op.drop_constraint(CHECK, TABLE, type_="check")
    op.create_check_constraint(
        CHECK,
        TABLE,
        "kind IN ('suggest_venue', 'suggest_listing', 'correction', 'report')",
    )
