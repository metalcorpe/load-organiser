"""Skydiver private gear: components, rigs, servicing and history (#152)

Additive only; owner-scoped tables with no data.

Revision ID: c7f1a2d9e3b5
Revises: b5e3c8a1f204
Create Date: 2026-11-03
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c7f1a2d9e3b5"
down_revision = "b5e3c8a1f204"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
TZ = sa.DateTime(timezone=True)
PARTIAL = "IS NULL OR length({0}) IN (4, 7, 10)"


def _owner() -> sa.Column:  # type: ignore[type-arg]
    return sa.Column(
        "owner_person_id",
        UUID,
        sa.ForeignKey("skydiver_person.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


def _version() -> sa.Column:  # type: ignore[type-arg]
    return sa.Column("version", sa.Integer(), nullable=False, server_default="1")


def upgrade() -> None:
    op.create_table(
        "skydiver_component",
        sa.Column("id", UUID, primary_key=True),
        _owner(),
        sa.Column("client_key", UUID, nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("label", sa.String(80), nullable=False),
        sa.Column("manufacturer", sa.String(80), nullable=True),
        sa.Column("model", sa.String(80), nullable=True),
        sa.Column("serial", sa.String(120), nullable=True),
        sa.Column("serial_key", sa.String(120), nullable=True),
        sa.Column("manufactured", sa.String(10), nullable=True),
        sa.Column("relation", sa.String(16), nullable=False),
        sa.Column("acquisition_method", sa.String(16), nullable=True),
        sa.Column("acquired", sa.String(10), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("archived_at", TZ, nullable=True),
        _version(),
        sa.Column("created_at", TZ, nullable=False),
        sa.Column("updated_at", TZ, nullable=False),
        sa.CheckConstraint(
            "kind IN ('container', 'main', 'reserve', 'aad', 'other')",
            name="ck_skydiver_component_kind",
        ),
        sa.CheckConstraint(
            "relation IN ('owned', 'borrowed', 'rented')",
            name="ck_skydiver_component_relation",
        ),
        sa.CheckConstraint(
            "acquisition_method IS NULL OR acquisition_method IN "
            "('purchase', 'gift', 'inheritance', 'other')",
            name="ck_skydiver_component_acquisition_method",
        ),
        sa.CheckConstraint(
            "relation = 'owned' OR (acquisition_method IS NULL AND acquired IS NULL)",
            name="ck_skydiver_component_acquisition_owned",
        ),
        sa.CheckConstraint(
            "manufactured " + PARTIAL.format("manufactured"),
            name="ck_skydiver_component_manufactured",
        ),
        sa.CheckConstraint(
            "acquired " + PARTIAL.format("acquired"),
            name="ck_skydiver_component_acquired",
        ),
        sa.UniqueConstraint(
            "owner_person_id", "client_key", name="uq_skydiver_component_key"
        ),
    )
    op.create_table(
        "skydiver_rig",
        sa.Column("id", UUID, primary_key=True),
        _owner(),
        sa.Column("client_key", UUID, nullable=False),
        sa.Column("label", sa.String(80), nullable=False),
        sa.Column("archived_at", TZ, nullable=True),
        _version(),
        sa.Column("created_at", TZ, nullable=False),
        sa.Column("updated_at", TZ, nullable=False),
        sa.UniqueConstraint(
            "owner_person_id", "client_key", name="uq_skydiver_rig_key"
        ),
    )
    op.create_table(
        "skydiver_rig_membership",
        sa.Column("id", UUID, primary_key=True),
        _owner(),
        sa.Column(
            "rig_id",
            UUID,
            sa.ForeignKey("skydiver_rig.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "component_id",
            UUID,
            sa.ForeignKey("skydiver_component.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("from_on", sa.Date(), nullable=False),
        sa.Column("until_on", sa.Date(), nullable=True),
        sa.CheckConstraint(
            "until_on IS NULL OR until_on >= from_on",
            name="ck_skydiver_membership_dates",
        ),
    )
    op.create_index(
        "ix_skydiver_membership_component",
        "skydiver_rig_membership",
        ["component_id", "from_on"],
    )
    op.create_index(
        "ix_skydiver_membership_rig", "skydiver_rig_membership", ["rig_id", "from_on"]
    )
    op.create_table(
        "skydiver_service_entry",
        sa.Column("id", UUID, primary_key=True),
        _owner(),
        sa.Column("client_key", UUID, nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column(
            "component_id",
            UUID,
            sa.ForeignKey("skydiver_component.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("done_on", sa.Date(), nullable=False),
        sa.Column("due_on", sa.Date(), nullable=True),
        sa.Column("performed_by", sa.String(120), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", TZ, nullable=False),
        sa.CheckConstraint(
            "kind IN ('repack', 'inspection', 'maintenance', 'aad_service', 'other')",
            name="ck_skydiver_service_kind",
        ),
        sa.CheckConstraint(
            "due_on IS NULL OR due_on >= done_on", name="ck_skydiver_service_due"
        ),
        sa.UniqueConstraint(
            "owner_person_id", "client_key", name="uq_skydiver_service_key"
        ),
    )
    op.create_index(
        "ix_skydiver_service_component",
        "skydiver_service_entry",
        ["component_id", "done_on"],
    )
    op.create_table(
        "skydiver_gear_event",
        sa.Column("id", UUID, primary_key=True),
        _owner(),
        sa.Column(
            "component_id",
            UUID,
            sa.ForeignKey("skydiver_component.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("detail", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", TZ, nullable=False),
    )
    op.create_index(
        "ix_skydiver_gear_event_component",
        "skydiver_gear_event",
        ["component_id", "id"],
    )


def downgrade() -> None:
    op.drop_table("skydiver_gear_event")
    op.drop_table("skydiver_service_entry")
    op.drop_table("skydiver_rig_membership")
    op.drop_table("skydiver_rig")
    op.drop_table("skydiver_component")
