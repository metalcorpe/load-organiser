"""Skydiver report decider references the account (account deletion, A9)

`decided_by_account_id` had no foreign key, so a reviewer who deleted their account
left their old account id in the reports they had decided. Ids that no longer
name an account are cleared, then the column references `user.id` and is set to
null when that account is deleted, as other reviewer history already is.

Revision ID: c3e8a5f7d1b9
Revises: b7d1f4a2c9e5
Create Date: 2026-11-07
"""

from alembic import op

revision = "c3e8a5f7d1b9"
down_revision = "b7d1f4a2c9e5"
branch_labels = None
depends_on = None

FK = "skydiver_social_report_decided_by_account_id_fkey"


def upgrade() -> None:
    op.execute(
        "UPDATE skydiver_social_report r SET decided_by_account_id = NULL "
        "WHERE decided_by_account_id IS NOT NULL "
        'AND NOT EXISTS (SELECT 1 FROM "user" u WHERE u.id = r.decided_by_account_id)'
    )
    op.create_foreign_key(
        FK,
        "skydiver_social_report",
        "user",
        ["decided_by_account_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(FK, "skydiver_social_report", type_="foreignkey")
