"""Pure identity rules (architecture A4/A7, data contracts "Account and browser contract").

No FastAPI, SQL, settings or provider imports: everything here is plain values and is
tested without a database.
"""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

PASSWORD_MIN_CHARS = 15
PASSWORD_MAX_CHARS = 128
EMAIL_MAX_CHARS = 254
DISPLAY_NAME_MAX_CHARS = 80

SESSION_LIFETIME = timedelta(days=7)
MAX_ACTIVE_SESSIONS = 5
ACCOUNT_TOKEN_LIFETIME = timedelta(minutes=30)

# 32 random bytes = 256 bits, URL-safe base64 without padding (43 characters).
SECRET_BYTES = 32


@dataclass(frozen=True)
class ThrottleRule:
    bucket: str
    limit: int
    window: timedelta


LOGIN_PAIR = ThrottleRule("login_pair", 10, timedelta(minutes=15))
LOGIN_IP = ThrottleRule("login_ip", 50, timedelta(minutes=15))
RESET_IDENTIFIER = ThrottleRule("reset_identifier", 3, timedelta(hours=1))
RESET_IP = ThrottleRule("reset_ip", 10, timedelta(hours=1))
REGISTER_IP = ThrottleRule("register_ip", 10, timedelta(hours=1))
VERIFY_RESEND_ACCOUNT = ThrottleRule("verify_resend", 3, timedelta(hours=1))


def password_problem(password: str) -> str | None:
    """Return a reason code when a *new* password breaks the policy, else None.

    Length counts Unicode code points. The password is never trimmed or normalised,
    and there are no composition rules. Existing shorter credentials still verify
    at login; this applies only to signup, reset and change.
    """
    if len(password) < PASSWORD_MIN_CHARS:
        return "password_too_short"
    if len(password) > PASSWORD_MAX_CHARS:
        return "password_too_long"
    return None


def normalize_email(email: str) -> str:
    """Canonical lookup form: surrounding whitespace removed, case-folded."""
    return email.strip().lower()


def new_secret() -> str:
    return secrets.token_urlsafe(SECRET_BYTES)


def hash_secret(secret: str) -> str:
    """SHA-256 of a high-entropy random secret. Only this digest is stored."""
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def throttle_key(*parts: str) -> str:
    """Opaque key for throttle rows: raw IPs and identifiers are not stored."""
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def session_expiry(created_at: datetime) -> datetime:
    """Absolute expiry; sessions are never extended (no sliding keepalive)."""
    return created_at + SESSION_LIFETIME


def sessions_over_cap[T](active_oldest_first: list[T], incoming: int = 1) -> list[T]:
    """IDs to revoke so that, after adding `incoming` sessions, at most the cap remain."""
    excess = len(active_oldest_first) + incoming - MAX_ACTIVE_SESSIONS
    return active_oldest_first[:excess] if excess > 0 else []
