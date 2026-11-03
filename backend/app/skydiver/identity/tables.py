"""Persistence rows for identity. Adapters only: policy code never imports this module.

All instants are UTC-aware (`timestamptz`), unlike the legacy naive operational columns.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlmodel import Field, SQLModel


def _account_fk(*, unique: bool = False, primary_key: bool = False) -> Column:  # type: ignore[type-arg]
    return Column(
        "account_id",
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        unique=unique,
        primary_key=primary_key,
        index=not (unique or primary_key),
    )


def _instant(*, nullable: bool = False) -> Column:  # type: ignore[type-arg]
    return Column(DateTime(timezone=True), nullable=nullable)


class SkydiverPerson(SQLModel, table=True):
    """Persistent jumper identity: one per account, separate from credentials and roles."""

    __tablename__ = "skydiver_person"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    account_id: uuid.UUID = Field(sa_column=_account_fk(unique=True))
    display_name: str | None = Field(default=None, max_length=80)
    created_at: datetime = Field(sa_column=_instant())


class SkydiverAccountState(SQLModel, table=True):
    """Private account state for the beta. Also the per-account lock row."""

    __tablename__ = "skydiver_account_state"

    account_id: uuid.UUID = Field(sa_column=_account_fk(primary_key=True))
    email_verified_at: datetime | None = Field(
        default=None, sa_column=_instant(nullable=True)
    )
    # The address that was verified; verification lapses if the email changes.
    email_verified_for: str | None = Field(default=None, max_length=255)
    created_at: datetime = Field(sa_column=_instant())


class SkydiverSession(SQLModel, table=True):
    __tablename__ = "skydiver_session"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    account_id: uuid.UUID = Field(sa_column=_account_fk())
    secret_hash: str = Field(sa_column=Column(String(64), nullable=False, unique=True))
    credential_marker: str = Field(sa_column=Column(String(64), nullable=False))
    created_at: datetime = Field(sa_column=_instant())
    expires_at: datetime = Field(sa_column=_instant())
    revoked_at: datetime | None = Field(default=None, sa_column=_instant(nullable=True))
    revoke_reason: str | None = Field(default=None, max_length=32)


class SkydiverAccountToken(SQLModel, table=True):
    """Single-use email verification / password reset token (hash only)."""

    __tablename__ = "skydiver_account_token"
    __table_args__ = (
        CheckConstraint(
            "purpose IN ('verify_email', 'reset_password')",
            name="skydiver_account_token_purpose",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    account_id: uuid.UUID = Field(sa_column=_account_fk())
    purpose: str = Field(max_length=16)
    token_hash: str = Field(sa_column=Column(String(64), nullable=False, unique=True))
    # The address the link was mailed to; it only verifies that address.
    sent_to: str = Field(max_length=255)
    created_at: datetime = Field(sa_column=_instant())
    expires_at: datetime = Field(sa_column=_instant())
    used_at: datetime | None = Field(default=None, sa_column=_instant(nullable=True))


class SkydiverThrottleEvent(SQLModel, table=True):
    """Rolling-window throttle events, shared by all API processes."""

    __tablename__ = "skydiver_throttle_event"
    __table_args__ = (
        Index("ix_skydiver_throttle_lookup", "bucket", "key_hash", "created_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    bucket: str = Field(max_length=32)
    key_hash: str = Field(sa_column=Column(String(64), nullable=False))
    created_at: datetime = Field(sa_column=_instant())


class SkydiverRoleGrant(SQLModel, table=True):
    """Server-granted beta role (#146). Never registration input or a legacy flag.

    Granted by an operator; there is no API for it in the beta.
    """

    __tablename__ = "skydiver_role_grant"
    __table_args__ = (
        CheckConstraint("role IN ('reviewer')", name="skydiver_role_grant_role"),
        UniqueConstraint("account_id", "role", name="uq_skydiver_role_grant"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    account_id: uuid.UUID = Field(sa_column=_account_fk())
    role: str = Field(max_length=32)
    granted_at: datetime = Field(sa_column=_instant())


class SkydiverRegistrationGate(SQLModel, table=True):
    """Single-row version for compare-and-swap registration (no locks held).

    A registration commits only if it advances `version` from the value it read
    before counting accounts; a concurrent registration makes it re-read and retry.
    """

    __tablename__ = "skydiver_registration_gate"
    __table_args__ = (
        CheckConstraint("id = 1", name="skydiver_registration_gate_single"),
    )

    id: int = Field(default=1, primary_key=True)
    version: int = Field(
        sa_column=Column(BigInteger, nullable=False, server_default="0")
    )
