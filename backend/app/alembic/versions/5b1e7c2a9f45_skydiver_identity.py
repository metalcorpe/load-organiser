"""Skydiver beta identity: person, account state, sessions, tokens, throttle (#145)

Additive only. Existing users get a person and account-state row (email unverified).

Revision ID: 5b1e7c2a9f45
Revises: c6459ca8ce2a
Create Date: 2026-11-02
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "5b1e7c2a9f45"
down_revision = "c6459ca8ce2a"
branch_labels = None
depends_on = None

TZ = sa.DateTime(timezone=True)


def _account_fk() -> sa.ForeignKey:
    return sa.ForeignKey("user.id", ondelete="CASCADE")


def upgrade() -> None:
    op.create_table(
        "skydiver_person",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            _account_fk(),
            nullable=False,
            unique=True,
        ),
        sa.Column("display_name", sa.String(80), nullable=True),
        sa.Column("created_at", TZ, nullable=False),
    )
    op.create_table(
        "skydiver_account_state",
        sa.Column(
            "account_id", postgresql.UUID(as_uuid=True), _account_fk(), primary_key=True
        ),
        sa.Column("email_verified_at", TZ, nullable=True),
        sa.Column("email_verified_for", sa.String(255), nullable=True),
        sa.Column("created_at", TZ, nullable=False),
    )
    op.create_table(
        "skydiver_session",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            _account_fk(),
            nullable=False,
            index=True,
        ),
        sa.Column("secret_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("credential_marker", sa.String(64), nullable=False),
        sa.Column("created_at", TZ, nullable=False),
        sa.Column("expires_at", TZ, nullable=False),
        sa.Column("revoked_at", TZ, nullable=True),
        sa.Column("revoke_reason", sa.String(32), nullable=True),
    )
    op.create_table(
        "skydiver_account_token",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            _account_fk(),
            nullable=False,
            index=True,
        ),
        sa.Column("purpose", sa.String(16), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("created_at", TZ, nullable=False),
        sa.Column("expires_at", TZ, nullable=False),
        sa.Column("used_at", TZ, nullable=True),
        sa.CheckConstraint(
            "purpose IN ('verify_email', 'reset_password')",
            name="skydiver_account_token_purpose",
        ),
    )
    op.create_table(
        "skydiver_throttle_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("bucket", sa.String(32), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False),
        sa.Column("created_at", TZ, nullable=False),
    )
    op.create_index(
        "ix_skydiver_throttle_lookup",
        "skydiver_throttle_event",
        ["bucket", "key_hash", "created_at"],
    )
    op.execute(
        """
        INSERT INTO skydiver_person (id, account_id, display_name, created_at)
        SELECT gen_random_uuid(), id, full_name, now() FROM "user"
        """
    )
    op.execute(
        """
        INSERT INTO skydiver_account_state (account_id, created_at)
        SELECT id, now() FROM "user"
        """
    )


def downgrade() -> None:
    op.drop_index("ix_skydiver_throttle_lookup", table_name="skydiver_throttle_event")
    for table in (
        "skydiver_throttle_event",
        "skydiver_account_token",
        "skydiver_session",
        "skydiver_account_state",
        "skydiver_person",
    ):
        op.drop_table(table)
