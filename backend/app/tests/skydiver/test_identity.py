"""#145 identity use cases over HTTP against the real PostgreSQL store.

The clock and mailer are fakes; everything else (router, service, SQL store,
migration-created tables, #170 hashing) is the production code path.
"""

import random
import re
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import bcrypt
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import select, text
from sqlmodel import Session, col

from app.core.db import engine
from app.models import User
from app.skydiver.adapters import AppPasswordHasher
from app.skydiver.identity.api import PREFIX, client_ip_resolver, create_router
from app.skydiver.identity.service import IdentityConfig, IdentityService
from app.skydiver.identity.store import sql_store_factory
from app.skydiver.identity.tables import SkydiverAccountToken, SkydiverSession

GOOD_PASSWORD = "correct horse battery staple"
OTHER_PASSWORD = "another long passphrase here"


@dataclass
class Clock:
    now: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kwargs: float) -> None:
        self.now += timedelta(**kwargs)


@dataclass
class Outbox:
    messages: list[dict[str, str]] = field(default_factory=list)

    def send(self, *, to: str, subject: str, text: str) -> None:
        self.messages.append({"to": to, "subject": subject, "text": text})

    def token_for(self, to: str, path: str) -> str:
        for message in reversed(self.messages):
            match = re.search(rf"{path}\?token=([A-Za-z0-9_-]+)", message["text"])
            if message["to"] == to and match:
                return match.group(1)
        raise AssertionError(f"no {path} mail for {to}")


@dataclass
class Harness:
    client: TestClient
    clock: Clock
    outbox: Outbox
    config: dict[str, object]
    ip: str

    def post(
        self, path: str, body: object = None, secret: str | None = None
    ) -> Response:
        return self.client.post(
            f"{PREFIX}{path}", json=body, headers=self._headers(secret)
        )

    def get(self, path: str, secret: str | None = None) -> Response:
        return self.client.get(f"{PREFIX}{path}", headers=self._headers(secret))

    def delete(self, path: str, secret: str | None = None) -> Response:
        return self.client.delete(f"{PREFIX}{path}", headers=self._headers(secret))

    def _headers(self, secret: str | None) -> dict[str, str]:
        headers = {"x-test-ip": self.ip}
        if secret:
            headers["authorization"] = f"Bearer {secret}"
        return headers

    def register(self, email: str, password: str = GOOD_PASSWORD) -> None:
        response = self.post("/registrations", {"email": email, "password": password})
        assert response.status_code == 202, response.text

    def verify(self, email: str) -> None:
        token = self.outbox.token_for(email, "/verify-email")
        response = self.post("/email-verification/confirm", {"token": token})
        assert response.status_code == 204

    def login(self, email: str, password: str = GOOD_PASSWORD) -> str:
        response = self.post("/sessions", {"email": email, "password": password})
        assert response.status_code == 201, response.text
        return str(response.json()["session_secret"])


def _random_ip() -> str:
    # A fresh address per test keeps per-IP throttle windows independent.
    return (
        f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
    )


@pytest.fixture
def harness() -> Iterator[Harness]:
    clock, outbox = Clock(), Outbox()
    config: dict[str, object] = {"registration_open": True, "max_accounts": 10_000}
    hasher = AppPasswordHasher()

    def service() -> IdentityService:
        return IdentityService(
            stores=sql_store_factory(engine),
            hasher=hasher,
            mailer=outbox,
            clock=clock,
            config=IdentityConfig(
                web_origin="https://web.example",
                registration_open=bool(config["registration_open"]),
                max_accounts=int(str(config["max_accounts"])),
            ),
        )

    def test_ip(request: Request) -> str:
        return request.headers["x-test-ip"]

    app = FastAPI()
    app.include_router(create_router(service=service, client_ip=test_ip))
    with TestClient(app) as client:
        yield Harness(client, clock, outbox, config, _random_ip())


def email() -> str:
    return f"jumper-{uuid.uuid4().hex[:12]}@example.com"


def _session_rows(address: str) -> list[SkydiverSession]:
    with Session(engine) as session:
        user = session.execute(
            select(User).where(col(User.email) == address)
        ).scalar_one()
        return list(
            session.execute(
                select(SkydiverSession).where(
                    col(SkydiverSession.account_id) == user.id
                )
            ).scalars()
        )


# --------------------------------------------------------------- registration


def test_register_verify_login_round_trip_stores_only_hashes(harness: Harness) -> None:
    address = email()
    harness.register(address)
    token = harness.outbox.token_for(address, "/verify-email")

    secret = harness.login(address)
    viewer = harness.get("/session", secret).json()
    assert viewer["email"] == address
    assert viewer["email_verified"] is False

    harness.verify(address)
    viewer = harness.get("/session", secret).json()
    assert viewer["email_verified"] is True
    assert viewer["person_id"] and viewer["person_id"] != viewer["account_id"]

    with Session(engine) as session:
        dump = session.execute(
            text(
                "SELECT string_agg(t::text, '|') FROM ("
                " SELECT secret_hash AS t FROM skydiver_session"
                " UNION ALL SELECT token_hash FROM skydiver_account_token) x"
            )
        ).scalar_one()
    assert secret not in dump and token not in dump
    assert len(secret) >= 43  # 256-bit secret


def test_verification_token_is_single_use_and_expires(harness: Harness) -> None:
    first, second = email(), email()
    harness.register(first)
    harness.register(second)
    harness.verify(first)
    reused = harness.post(
        "/email-verification/confirm",
        {"token": harness.outbox.token_for(first, "/verify-email")},
    )
    assert reused.status_code == 400
    assert reused.json() == {"detail": "invalid_or_expired_token"}

    harness.clock.advance(minutes=31)
    expired = harness.post(
        "/email-verification/confirm",
        {"token": harness.outbox.token_for(second, "/verify-email")},
    )
    assert expired.status_code == 400


def test_duplicate_registration_is_neutral(harness: Harness) -> None:
    address = email()
    harness.register(address)
    again = harness.post(
        "/registrations", {"email": address.upper(), "password": OTHER_PASSWORD}
    )
    assert again.status_code == 202 and again.json() == {"status": "accepted"}
    assert "sign-in help" in harness.outbox.messages[-1]["subject"]
    with Session(engine) as session:
        count = session.execute(
            text('SELECT count(*) FROM "user" WHERE lower(email) = :e'), {"e": address}
        ).scalar_one()
    assert count == 1
    # The original password still works; the attempt changed nothing.
    harness.login(address)


@pytest.mark.parametrize(
    ("password", "code"),
    [("x" * 14, "password_too_short"), ("x" * 129, "password_too_long")],
)
def test_new_password_policy(harness: Harness, password: str, code: str) -> None:
    response = harness.post("/registrations", {"email": email(), "password": password})
    assert response.status_code == 422
    assert response.json() == {"detail": code}


def test_unicode_password_is_not_normalised_or_trimmed(harness: Harness) -> None:
    address, password = email(), " 🪂 Καλή πτώση 🪂 "
    assert len(password) == 16  # code points, at or above the 15 minimum
    harness.register(address, password)
    harness.login(address, password)
    stripped = harness.post(
        "/sessions", {"email": address, "password": password.strip()}
    )
    assert stripped.status_code == 401


def test_registration_switch_and_account_cap(harness: Harness) -> None:
    harness.config["registration_open"] = False
    closed = harness.post(
        "/registrations", {"email": email(), "password": GOOD_PASSWORD}
    )
    assert closed.status_code == 403
    assert closed.json() == {"detail": "registration_closed"}

    harness.config["registration_open"] = True
    harness.config["max_accounts"] = 0
    capped = harness.post(
        "/registrations", {"email": email(), "password": GOOD_PASSWORD}
    )
    assert capped.status_code == 403


# ------------------------------------------------------------------- sessions


def test_login_failures_are_indistinguishable(harness: Harness) -> None:
    address = email()
    harness.register(address)
    wrong = harness.post("/sessions", {"email": address, "password": OTHER_PASSWORD})
    unknown = harness.post("/sessions", {"email": email(), "password": GOOD_PASSWORD})
    for response in (wrong, unknown):
        assert response.status_code == 401
        assert response.json() == {"detail": "invalid_credentials"}
        assert response.headers["cache-control"] == "no-store"


def test_login_throttle_per_ip_and_identifier(harness: Harness) -> None:
    address = email()
    harness.register(address)
    for _ in range(10):
        harness.post("/sessions", {"email": address, "password": OTHER_PASSWORD})
    blocked = harness.post("/sessions", {"email": address, "password": GOOD_PASSWORD})
    assert blocked.status_code == 429
    assert blocked.headers["retry-after"] == "900"

    harness.clock.advance(minutes=15, seconds=1)
    harness.login(address)


def test_session_expires_after_seven_days_without_sliding(harness: Harness) -> None:
    address = email()
    harness.register(address)
    secret = harness.login(address)
    expires = harness.get("/session", secret).json()["session_expires_at"]

    harness.clock.advance(days=6, hours=23)
    assert harness.get("/session", secret).json()["session_expires_at"] == expires
    harness.clock.advance(hours=1)
    response = harness.get("/session", secret)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_at_most_five_active_sessions(harness: Harness) -> None:
    address = email()
    harness.register(address)
    secrets = []
    for _ in range(6):
        secrets.append(harness.login(address))
        harness.clock.advance(seconds=1)
    assert harness.get("/session", secrets[0]).status_code == 401
    for secret in secrets[1:]:
        assert harness.get("/session", secret).status_code == 200
    reasons = {row.revoke_reason for row in _session_rows(address)}
    assert reasons == {None, "session_limit"}


def test_logout_revokes_only_that_session(harness: Harness) -> None:
    address = email()
    harness.register(address)
    phone, laptop = harness.login(address), harness.login(address)
    assert harness.delete("/session", phone).status_code == 204
    assert harness.get("/session", phone).status_code == 401
    assert harness.get("/session", laptop).status_code == 200
    # Idempotent, and an unknown secret reveals nothing.
    assert harness.delete("/session", phone).status_code == 204
    assert harness.delete("/session", "not-a-session").status_code == 204


def test_sessions_are_isolated_between_accounts(harness: Harness) -> None:
    alice, bob = email(), email()
    harness.register(alice)
    harness.register(bob)
    alice_secret, bob_secret = harness.login(alice), harness.login(bob)
    assert harness.get("/session", alice_secret).json()["email"] == alice
    assert harness.get("/session", bob_secret).json()["email"] == bob
    harness.delete("/session", alice_secret)
    assert harness.get("/session", bob_secret).status_code == 200


def test_revoke_all_requires_fresh_password(harness: Harness) -> None:
    address = email()
    harness.register(address)
    one, two = harness.login(address), harness.login(address)
    wrong = harness.post("/sessions/revoke-all", {"password": OTHER_PASSWORD}, one)
    assert wrong.status_code == 422
    assert wrong.json() == {"detail": "password_confirmation_failed"}
    assert harness.get("/session", two).status_code == 200

    ok = harness.post("/sessions/revoke-all", {"password": GOOD_PASSWORD}, one)
    assert ok.status_code == 204
    for secret in (one, two):
        assert harness.get("/session", secret).status_code == 401


def test_password_change_keeps_current_session_only(harness: Harness) -> None:
    address = email()
    harness.register(address)
    current, other = harness.login(address), harness.login(address)
    short = harness.post(
        "/password",
        {"current_password": GOOD_PASSWORD, "new_password": "short"},
        current,
    )
    assert short.status_code == 422
    changed = harness.post(
        "/password",
        {"current_password": GOOD_PASSWORD, "new_password": OTHER_PASSWORD},
        current,
    )
    assert changed.status_code == 204
    assert harness.get("/session", current).status_code == 200
    assert harness.get("/session", other).status_code == 401
    old = harness.post("/sessions", {"email": address, "password": GOOD_PASSWORD})
    assert old.status_code == 401
    harness.login(address, OTHER_PASSWORD)


def test_suspended_account_loses_sessions_and_login(harness: Harness) -> None:
    address = email()
    harness.register(address)
    secret = harness.login(address)
    with Session(engine) as session:
        session.execute(
            text('UPDATE "user" SET is_active = false WHERE email = :e'), {"e": address}
        )
        session.commit()
    assert harness.get("/session", secret).status_code == 401
    banned = harness.post("/sessions", {"email": address, "password": GOOD_PASSWORD})
    assert banned.status_code == 401


def test_legacy_bcrypt_account_gets_identity_and_argon2_on_login(
    harness: Harness,
) -> None:
    address = email()
    legacy_hash = bcrypt.hashpw(b"legacy-password", bcrypt.gensalt(rounds=4)).decode()
    with Session(engine) as session:
        # Created outside the identity module, as by the legacy API: no person row.
        session.add(User(email=address, hashed_password=legacy_hash))
        session.commit()

    secret = harness.login(address, "legacy-password")
    viewer = harness.get("/session", secret).json()
    assert viewer["person_id"]
    with Session(engine) as session:
        stored = session.execute(
            select(col(User.hashed_password)).where(col(User.email) == address)
        ).scalar_one()
    assert stored.startswith("$argon2id$")


# ------------------------------------------------------------------- recovery


def test_password_reset_is_neutral_single_use_and_revokes_sessions(
    harness: Harness,
) -> None:
    address = email()
    harness.register(address)
    secret = harness.login(address)
    sent_before = len(harness.outbox.messages)

    unknown = harness.post("/password-reset", {"email": email()})
    assert unknown.status_code == 202
    assert len(harness.outbox.messages) == sent_before

    known = harness.post("/password-reset", {"email": address})
    assert known.status_code == 202 and known.json() == unknown.json()
    token = harness.outbox.token_for(address, "/reset-password")

    reset = harness.post(
        "/password-reset/confirm", {"token": token, "new_password": OTHER_PASSWORD}
    )
    assert reset.status_code == 204
    assert harness.get("/session", secret).status_code == 401
    again = harness.post(
        "/password-reset/confirm", {"token": token, "new_password": GOOD_PASSWORD}
    )
    assert again.status_code == 400

    new_secret = harness.login(address, OTHER_PASSWORD)
    # Completing a reset proves control of the inbox.
    assert harness.get("/session", new_secret).json()["email_verified"] is True


def test_reset_link_expires_after_thirty_minutes(harness: Harness) -> None:
    address = email()
    harness.register(address)
    harness.post("/password-reset", {"email": address})
    token = harness.outbox.token_for(address, "/reset-password")
    harness.clock.advance(minutes=30, seconds=1)
    expired = harness.post(
        "/password-reset/confirm", {"token": token, "new_password": OTHER_PASSWORD}
    )
    assert expired.status_code == 400
    harness.login(address)


def test_newer_reset_link_retires_older_one(harness: Harness) -> None:
    address = email()
    harness.register(address)
    harness.post("/password-reset", {"email": address})
    first = harness.outbox.token_for(address, "/reset-password")
    harness.post("/password-reset", {"email": address})
    stale = harness.post(
        "/password-reset/confirm", {"token": first, "new_password": OTHER_PASSWORD}
    )
    assert stale.status_code == 400


def test_reset_identifier_limit_is_silent(harness: Harness) -> None:
    address = email()
    harness.register(address)
    before = len(harness.outbox.messages)
    for _ in range(5):
        response = harness.post("/password-reset", {"email": address})
        assert response.status_code == 202
    assert len(harness.outbox.messages) - before == 3
    with Session(engine) as session:
        live = session.execute(
            select(SkydiverAccountToken)
            .where(col(SkydiverAccountToken.purpose) == "reset_password")
            .where(col(SkydiverAccountToken.used_at).is_(None))
            .join(User, col(User.id) == col(SkydiverAccountToken.account_id))
            .where(col(User.email) == address)
        ).all()
    assert len(live) == 1


def test_resend_verification_replaces_previous_link(harness: Harness) -> None:
    address = email()
    harness.register(address)
    first = harness.outbox.token_for(address, "/verify-email")
    secret = harness.login(address)
    assert harness.post("/email-verification", None, secret).status_code == 202
    second = harness.outbox.token_for(address, "/verify-email")
    assert first != second
    stale = harness.post("/email-verification/confirm", {"token": first})
    assert stale.status_code == 400
    harness.verify(address)


def test_unauthenticated_requests_are_rejected(harness: Harness) -> None:
    for response in (
        harness.get("/session"),
        harness.get("/session", "forged-secret"),
        harness.post("/email-verification"),
        harness.post("/sessions/revoke-all", {"password": GOOD_PASSWORD}, "forged"),
    ):
        assert response.status_code == 401


# ------------------------------------------------------------ client address


def test_forwarded_client_ip_is_trusted_only_with_proxy_key() -> None:
    resolve = client_ip_resolver("k" * 32)
    app = FastAPI()

    @app.get("/ip")
    def ip(request: Request) -> str:
        return resolve(request)

    with TestClient(app) as client:
        forged = client.get("/ip", headers={"x-organiser-client-ip": "203.0.113.9"})
        assert forged.json() == "testclient"
        trusted = client.get(
            "/ip",
            headers={
                "x-organiser-client-ip": "203.0.113.9",
                "x-organiser-proxy-key": "k" * 32,
            },
        )
        assert trusted.json() == "203.0.113.9"
        junk = client.get(
            "/ip",
            headers={
                "x-organiser-client-ip": "not-an-ip",
                "x-organiser-proxy-key": "k" * 32,
            },
        )
        assert junk.json() == "testclient"
