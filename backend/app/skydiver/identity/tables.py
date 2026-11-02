"""Persistence rows for identity. Adapters only: policy code never imports this module.

All instants are UTC-aware (`timestamptz`), unlike the legacy naive operational columns.
"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Index, String
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
    created_at: datetime = Field(sa_column=_instant())


class SkydiverSession(SQLModel, table=True):
    __tablename__ = "skydiver_session"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    account_id: uuid.UUID = Field(sa_column=_account_fk())
    secret_hash: str = Field(sa_column=Column(String(64), nullable=False, unique=True))
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
