"""Skydiver opportunity price tiers: dated and separate charges

Additive only, with no data:

- skydiver_opportunity.price_tiers: a JSON array of up to 6
  {"label", "amount", "currency", "basis", "from_on", "until_on", "optional"}
  objects (default empty array, checked). Tier dates are inclusive calendar dates in
  the listing's time zone. Tiers replace the single stated price, so a listing has
  price_amount or tiers or neither, never both (checked).

The previous code never reads or writes the column, so it keeps working during a
rollover. A downgrade drops the column (the tiers are lost, nothing else).

Revision ID: b7d2f9e4c1a6
Revises: e8bcedce6f4a
Create Date: 2026-11-16
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b7d2f9e4c1a6"
down_revision = "e8bcedce6f4a"
branch_labels = None
depends_on = None

TABLE = "skydiver_opportunity"
CHECK = "skydiver_opportunity_price_tiers"


def upgrade() -> None:
    op.add_column(
        TABLE,
        sa.Column(
            "price_tiers",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.create_check_constraint(
        CHECK,
        TABLE,
        "jsonb_typeof(price_tiers) = 'array' AND jsonb_array_length(price_tiers) <= 6"
        " AND (price_amount IS NULL OR jsonb_array_length(price_tiers) = 0)",
    )


def downgrade() -> None:
    op.drop_constraint(CHECK, TABLE, type_="check")
    op.drop_column(TABLE, "price_tiers")
