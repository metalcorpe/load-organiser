"""Skydiver beta role grants (#146)

Additive only. No grants are created: legacy `is_superuser` confers no beta role.

Revision ID: 8c3d1f6b2a70
Revises: 5b1e7c2a9f45
Create Date: 2026-11-03
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "8c3d1f6b2a70"
down_revision = "5b1e7c2a9f45"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "skydiver_role_grant",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('reviewer')", name="skydiver_role_grant_role"),
        sa.UniqueConstraint("account_id", "role", name="uq_skydiver_role_grant"),
    )


def downgrade() -> None:
    op.drop_table("skydiver_role_grant")
