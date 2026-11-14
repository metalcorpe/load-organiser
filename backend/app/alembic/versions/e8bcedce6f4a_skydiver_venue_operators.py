"""Skydiver venue details as stated by the source: operators, season, aircraft

Additive only, with no data:

- skydiver_venue.operators: who runs the dropzone according to its source, a JSON
  array of up to 4 {"name", "url"} objects (default empty array, checked). It names
  the operator; it is not a claim, endorsement or verification (owner decision
  2026-11-14, docs/product/dropzone-directory.md);
- skydiver_venue.season and skydiver_venue.aircraft: short source-stated text
  (nullable, at most 160 characters).

The previous code never reads or writes them, so it keeps working during a
rollover. A downgrade drops the three columns (the details are lost, nothing else).

Revision ID: e8bcedce6f4a
Revises: e8b3d5f1a7c4
Create Date: 2026-11-14
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "e8bcedce6f4a"
down_revision = "e8b3d5f1a7c4"
branch_labels = None
depends_on = None

TABLE = "skydiver_venue"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column(
            "operators",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(TABLE, sa.Column("season", sa.String(length=160), nullable=True))
    op.add_column(TABLE, sa.Column("aircraft", sa.String(length=160), nullable=True))
    op.create_check_constraint(
        "skydiver_venue_operators_list",
        TABLE,
        "jsonb_typeof(operators) = 'array' AND jsonb_array_length(operators) <= 4",
    )


def downgrade() -> None:
    op.drop_constraint("skydiver_venue_operators_list", TABLE, type_="check")
    op.drop_column(TABLE, "aircraft")
    op.drop_column(TABLE, "season")
    op.drop_column(TABLE, "operators")
