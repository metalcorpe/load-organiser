from datetime import datetime

import bcrypt
import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.core.security import (
    get_password_hash,
    verify_and_update_password,
    verify_password,
)
from app.models import (
    Jump,
    Load,
    WeatherCondition,
    WeatherReport,
    utc_naive_now,
)


def test_new_passwords_use_argon2_without_bcrypt_truncation() -> None:
    password = "🪂" * 30
    hashed = get_password_hash(password)
    assert hashed.startswith("$argon2id$")
    assert verify_password(password, hashed)
    assert not verify_password(password + "different", hashed)


@pytest.mark.parametrize("password", ["legacy-password", "🪂" * 30])
def test_existing_bcrypt_hashes_remain_readable(password: str) -> None:
    # This is the 72-byte behavior used by the previous Passlib configuration.
    hashed = bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt(rounds=4))
    assert verify_password(password, hashed.decode("ascii"))
    assert not verify_password("incorrect-password", hashed.decode("ascii"))


def test_legacy_bcrypt_hash_is_upgraded_to_full_password_argon2() -> None:
    password = "🪂" * 30  # 120 bytes: beyond bcrypt's 72-byte limit
    legacy = bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt(rounds=4))

    verified, updated = verify_and_update_password(password, legacy.decode("ascii"))
    assert verified
    assert updated is not None and updated.startswith("$argon2id$")
    # The upgrade covers the full password, not the truncated bcrypt input.
    assert verify_password(password, updated)
    assert not verify_password("🪂" * 18, updated)


def test_current_argon2_hash_is_not_rehashed_and_wrong_password_fails() -> None:
    hashed = get_password_hash("current-password")
    assert verify_and_update_password("current-password", hashed) == (True, None)
    assert verify_and_update_password("wrong", hashed) == (False, None)


def test_created_at_columns_share_naive_utc_default() -> None:
    for model in (Load, Jump, WeatherReport):
        column = model.__table__.columns["created_at"]
        assert column.type.timezone is False
        assert model.model_fields["created_at"].default_factory is utc_naive_now
    assert utc_naive_now().tzinfo is None


def test_legacy_datetime_columns_keep_naive_storage() -> None:
    # SQLModel now defaults to timezone-aware storage. Keep existing columns
    # compatible until an explicit data/timezone migration is designed.
    for model, fields in (
        (Load, ("scheduled_time", "created_at")),
        (WeatherReport, ("date", "created_at")),
    ):
        for field in fields:
            assert model.__table__.columns[field].type.timezone is False

    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    recorded_at = datetime(2026, 1, 1, 12, 0)
    report = WeatherReport(
        date=recorded_at,
        wind_speed=5,
        wind_direction=90,
        visibility=10,
        condition=next(iter(WeatherCondition)),
    )
    with Session(engine) as session:
        session.add(report)
        session.commit()
        session.refresh(report)
        assert report.date == recorded_at
        assert report.created_at.tzinfo is None


def test_send_email_without_configuration_keeps_descriptive_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app import utils

    monkeypatch.setattr(utils.settings, "EMAILS_FROM_EMAIL", None)
    with pytest.raises(RuntimeError, match="no provided configuration for email"):
        utils.send_email(email_to="user@example.com")
