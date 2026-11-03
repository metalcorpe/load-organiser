"""Pure identity policy (#145): no database, settings or HTTP."""

from datetime import UTC, datetime, timedelta

import pytest

from app.skydiver.identity import policy


@pytest.mark.parametrize(
    ("password", "problem"),
    [
        ("a" * 14, "password_too_short"),
        ("a" * 15, None),
        ("a" * 128, None),
        ("a" * 129, "password_too_long"),
        ("🪂" * 15, None),  # code points, not bytes
        ("   " + "a" * 12, None),  # whitespace counts; nothing is trimmed
    ],
)
def test_password_policy(password: str, problem: str | None) -> None:
    assert policy.password_problem(password) == problem


def test_email_normalisation() -> None:
    assert policy.normalize_email("  Jumper@Example.COM ") == "jumper@example.com"


def test_secrets_are_256_bit_and_hashed_deterministically() -> None:
    secret = policy.new_secret()
    assert len(secret) == 43
    assert policy.new_secret() != secret
    digest = policy.hash_secret(secret)
    assert len(digest) == 64 and digest == policy.hash_secret(secret)
    assert secret not in digest
    # Hostile bearer values hash instead of raising.
    assert len(policy.hash_secret("é\x00")) == 64


def test_session_expiry_is_absolute_seven_days() -> None:
    start = datetime(2026, 11, 2, 12, tzinfo=UTC)
    assert policy.session_expiry(start) == start + timedelta(days=7)


@pytest.mark.parametrize(
    ("active", "revoked"),
    [(0, 0), (4, 0), (5, 1), (7, 3)],
)
def test_session_cap_revokes_oldest(active: int, revoked: int) -> None:
    ids = [str(i) for i in range(active)]
    assert policy.sessions_over_cap(ids) == ids[:revoked]


def test_throttle_keys_do_not_contain_raw_values() -> None:
    key = policy.throttle_key("login_pair", "203.0.113.9", "jumper@example.com")
    assert "203.0.113.9" not in key and "jumper" not in key
    assert key != policy.throttle_key("login_pair", "203.0.113.9", "other@example.com")


@pytest.mark.parametrize(
    ("address", "bucket"),
    [
        ("203.0.113.9", "203.0.113.9"),
        ("2001:db8:1:2:aaaa::1", "2001:db8:1:2::/64"),
        ("2001:db8:1:2:ffff::9", "2001:db8:1:2::/64"),
        ("::ffff:203.0.113.9", "203.0.113.9"),
        ("unknown", "unknown"),
    ],
)
def test_client_bucket(address: str, bucket: str) -> None:
    assert policy.client_bucket(address) == bucket


def test_credential_marker_changes_with_hash() -> None:
    assert policy.credential_marker("$argon2id$a") != policy.credential_marker(
        "$argon2id$b"
    )
