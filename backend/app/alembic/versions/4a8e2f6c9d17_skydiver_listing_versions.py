"""Skydiver compare-and-swap versions on venues, providers and listings (#151)

Additive only: integer versions default to 1 for existing rows.

Revision ID: 4a8e2f6c9d17
Revises: 9c1d4e7f2b60
Create Date: 2026-11-03
"""

import sqlalchemy as sa
from alembic import op

revision = "4a8e2f6c9d17"
down_revision = "9c1d4e7f2b60"
branch_labels = None
depends_on = None

COLUMNS = (
    ("skydiver_venue", "version"),
    ("skydiver_provider", "version"),
    ("skydiver_provider", "listings_version"),
    ("skydiver_opportunity", "version"),
)


def upgrade() -> None:
    for table, column in COLUMNS:
        op.add_column(
            table,
            sa.Column(column, sa.Integer(), nullable=False, server_default="1"),
        )


def downgrade() -> None:
    for table, column in reversed(COLUMNS):
        op.drop_column(table, column)
