"""Skydiver providers, dated opportunities and listing history (#149)

Additive only. No provider or opportunity data is inserted: listings come from
reviewed sources.

Revision ID: 2d5befa4f070
Revises: 2f7a9c4e1b38
Create Date: 2026-11-03
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "2d5befa4f070"
down_revision = "2f7a9c4e1b38"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
TZ = sa.DateTime(timezone=True)


def _tags(name: str) -> sa.Column:  # type: ignore[type-arg]
    return sa.Column(
        name, postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"
    )


def upgrade() -> None:
    op.create_table(
        "skydiver_provider",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("name_key", sa.Text(), nullable=False, index=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("country", sa.String(2), nullable=True),
        sa.Column("website_url", sa.String(2048), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column(
            "merged_into_id",
            UUID,
            sa.ForeignKey("skydiver_provider.id"),
            nullable=True,
        ),
        sa.Column("source_url", sa.String(2048), nullable=True),
        sa.Column("source_note", sa.String(280), nullable=True),
        sa.Column("checked_on", sa.Date(), nullable=True),
        sa.Column("created_at", TZ, nullable=False),
        sa.Column("updated_at", TZ, nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'archived', 'merged')",
            name="skydiver_provider_status",
        ),
        sa.CheckConstraint(
            "kind IN ('organization', 'person')", name="skydiver_provider_kind"
        ),
        sa.CheckConstraint(
            "(status = 'merged') = (merged_into_id IS NOT NULL)",
            name="skydiver_provider_merge_target",
        ),
        sa.CheckConstraint(
            "status <> 'published' OR (source_url IS NOT NULL AND checked_on IS NOT NULL)",
            name="skydiver_provider_source_backed",
        ),
        sa.CheckConstraint("merged_into_id <> id", name="skydiver_provider_not_self"),
    )
    op.create_table(
        "skydiver_opportunity",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("title_key", sa.Text(), nullable=False),
        sa.Column("category", sa.String(16), nullable=False),
        sa.Column(
            "provider_id",
            UUID,
            sa.ForeignKey("skydiver_provider.id"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "venue_id",
            UUID,
            sa.ForeignKey("skydiver_venue.id"),
            nullable=True,
            index=True,
        ),
        sa.Column("country", sa.String(2), nullable=False),
        sa.Column("location_note", sa.String(200), nullable=True),
        sa.Column("starts_on", sa.Date(), nullable=True),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("time_zone", sa.String(64), nullable=True),
        sa.Column("expires_at", TZ, nullable=True),
        sa.Column("sort_on", sa.Date(), nullable=False),
        _tags("disciplines"),
        _tags("audience"),
        _tags("languages"),
        sa.Column("summary", sa.String(500), nullable=True),
        sa.Column("prerequisites", sa.String(1000), nullable=True),
        sa.Column("price_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("price_currency", sa.String(3), nullable=True),
        sa.Column("price_basis", sa.String(16), nullable=True),
        sa.Column("price_note", sa.String(280), nullable=True),
        sa.Column("registration_url", sa.String(2048), nullable=True),
        sa.Column("source_url", sa.String(2048), nullable=True),
        sa.Column("source_note", sa.String(280), nullable=True),
        sa.Column("checked_on", sa.Date(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column(
            "duplicate_of_id",
            UUID,
            sa.ForeignKey("skydiver_opportunity.id"),
            nullable=True,
        ),
        sa.Column("created_at", TZ, nullable=False),
        sa.Column("updated_at", TZ, nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'review', 'published', 'postponed', 'cancelled',"
            " 'archived', 'duplicate')",
            name="skydiver_opportunity_status",
        ),
        sa.CheckConstraint(
            "category IN ('event', 'boogie', 'camp', 'course')",
            name="skydiver_opportunity_category",
        ),
        sa.CheckConstraint(
            "(status = 'duplicate') = (duplicate_of_id IS NOT NULL)",
            name="skydiver_opportunity_duplicate_target",
        ),
        sa.CheckConstraint(
            "duplicate_of_id <> id", name="skydiver_opportunity_not_self"
        ),
        sa.CheckConstraint(
            "(starts_on IS NULL) = (ends_on IS NULL) AND starts_on <= ends_on",
            name="skydiver_opportunity_dates",
        ),
        sa.CheckConstraint(
            "starts_on IS NULL OR time_zone IS NOT NULL",
            name="skydiver_opportunity_dates_zoned",
        ),
        sa.CheckConstraint(
            "(expires_at IS NULL) = (ends_on IS NULL)",
            name="skydiver_opportunity_expiry",
        ),
        sa.CheckConstraint(
            "(price_amount IS NULL) = (price_currency IS NULL)"
            " AND (price_amount IS NULL) = (price_basis IS NULL)",
            name="skydiver_opportunity_price",
        ),
        sa.CheckConstraint(
            "status NOT IN ('published', 'postponed', 'cancelled') OR"
            " (source_url IS NOT NULL AND checked_on IS NOT NULL"
            " AND registration_url IS NOT NULL"
            " AND (venue_id IS NOT NULL OR location_note IS NOT NULL))",
            name="skydiver_opportunity_publishable",
        ),
        sa.CheckConstraint(
            "status NOT IN ('published', 'cancelled') OR starts_on IS NOT NULL",
            name="skydiver_opportunity_dated",
        ),
    )
    op.create_index(
        "ix_skydiver_opportunity_upcoming",
        "skydiver_opportunity",
        ["status", "sort_on", "id"],
    )
    op.create_table(
        "skydiver_listing_event",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "provider_id",
            UUID,
            sa.ForeignKey("skydiver_provider.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "opportunity_id",
            UUID,
            sa.ForeignKey("skydiver_opportunity.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("detail", postgresql.JSONB(), nullable=False),
        sa.Column(
            "actor_account_id",
            UUID,
            sa.ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", TZ, nullable=False),
        sa.CheckConstraint(
            "(provider_id IS NULL) <> (opportunity_id IS NULL)",
            name="skydiver_listing_event_subject",
        ),
    )


def downgrade() -> None:
    op.drop_table("skydiver_listing_event")
    op.drop_index("ix_skydiver_opportunity_upcoming", table_name="skydiver_opportunity")
    op.drop_table("skydiver_opportunity")
    op.drop_table("skydiver_provider")
