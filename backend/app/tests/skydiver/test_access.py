"""#146 access conventions over HTTP against the real PostgreSQL store.

No beta personal-record feature exists yet (#152+), so a test-only owned table and
router exercise the conventions the features must use: `AccessDependencies`,
`get_owned`/`owned` and `lock_owner`. Accounts, sessions and roles are real.
"""

import random
import re
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Annotated

import pytest
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Response
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy import Column, ForeignKey, update
from sqlmodel import Field, Session, SQLModel, col

from app.core.db import engine
from app.models import User
from app.skydiver.access.http import AccessDependencies
from app.skydiver.access.policy import Actor, Role
from app.skydiver.access.sql import get_owned, lock_owner, owned
from app.skydiver.adapters import AppPasswordHasher
from app.skydiver.identity.service import IdentityConfig, IdentityService
from app.skydiver.identity.store import sql_store_factory
from app.skydiver.identity.tables import SkydiverRoleGrant

PASSWORD = "correct horse battery staple"


class AccessProbeNote(SQLModel, table=True):
    """Test-only stand-in for a personal record. Created and dropped by this module."""

    __tablename__ = "test_access_probe_note"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_person_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("skydiver_person.id", ondelete="CASCADE"), nullable=False
        )
    )
    text: str = Field(max_length=200)


class NoteIn(BaseModel):
    text: str
    # A client-supplied owner must be ignored, never trusted.
    owner_person_id: uuid.UUID | None = None


class NoteOut(BaseModel):
    id: uuid.UUID
    text: str


@dataclass
class Outbox:
    messages: list[dict[str, str]] = field(default_factory=list)

    def send(self, *, to: str, subject: str, text: str) -> None:
        self.messages.append({"to": to, "text": text})

    def token_for(self, to: str) -> str:
        for message in reversed(self.messages):
            found = re.search(r"verify-email\?token=([A-Za-z0-9_-]+)", message["text"])
            if message["to"] == to and found:
                return found.group(1)
        raise AssertionError(f"no verification mail for {to}")


def probe_router(access: AccessDependencies) -> APIRouter:
    router = APIRouter(prefix="/probe")
    Reader = Annotated[Actor, Depends(access.actor)]
    Writer = Annotated[Actor, Depends(access.verified_actor)]
    Reviewer = Annotated[Actor, Depends(access.role(Role.REVIEWER))]

    def missing() -> HTTPException:
        return HTTPException(status_code=404, detail="not_found")

    @router.get("/notes")
    def list_notes(actor: Reader) -> list[NoteOut]:
        with Session(engine) as session:
            rows = session.execute(owned(AccessProbeNote, actor)).scalars().all()
            return [NoteOut(id=row.id, text=row.text) for row in rows]

    @router.get("/notes/{note_id}")
    def read_note(note_id: uuid.UUID, actor: Reader) -> NoteOut:
        with Session(engine) as session:
            row = get_owned(session, AccessProbeNote, note_id, actor)
            if row is None:
                raise missing()
            return NoteOut(id=row.id, text=row.text)

    @router.post("/notes", status_code=201)
    def create_note(body: NoteIn, actor: Writer) -> NoteOut:
        with Session(engine) as session:
            lock_owner(session, actor)
            row = AccessProbeNote(owner_person_id=actor.person_id, text=body.text)
            session.add(row)
            session.commit()
            return NoteOut(id=row.id, text=row.text)

    @router.put("/notes/{note_id}")
    def update_note(note_id: uuid.UUID, body: NoteIn, actor: Writer) -> NoteOut:
        with Session(engine) as session:
            row = get_owned(session, AccessProbeNote, note_id, actor, for_update=True)
            if row is None:
                raise missing()
            row.text = body.text
            session.add(row)
            session.commit()
            return NoteOut(id=row.id, text=row.text)

    @router.delete("/notes/{note_id}", status_code=204)
    def delete_note(note_id: uuid.UUID, actor: Writer) -> Response:
        with Session(engine) as session:
            row = get_owned(session, AccessProbeNote, note_id, actor, for_update=True)
            if row is None:
                raise missing()
            session.delete(row)
            session.commit()
        return Response(status_code=204)

    @router.get("/review-queue")
    def review_queue(_: Reviewer) -> dict[str, str]:
        return {"status": "ok"}

    return router


def _random_ip() -> str:
    # Fresh address per call keeps per-IP throttle windows out of these tests.
    return f"10.146.{random.randint(0, 255)}.{random.randint(1, 254)}"


@dataclass
class Probe:
    client: TestClient
    service: IdentityService
    outbox: Outbox

    def account(
        self, *, verified: bool = True, superuser: bool = False, reviewer: bool = False
    ) -> str:
        address = f"access-{uuid.uuid4().hex[:12]}@example.com"
        self.service.register(
            email=address,
            password=PASSWORD,
            display_name=None,
            client_ip=_random_ip(),
        )
        if verified:
            self.service.confirm_email(token=self.outbox.token_for(address))
        with Session(engine) as session:
            user_id = session.execute(
                update(User)
                .where(col(User.email) == address)
                .values(is_superuser=superuser)
                .returning(col(User.id))
            ).scalar_one()
            if reviewer:
                session.add(
                    SkydiverRoleGrant(
                        account_id=user_id,
                        role="reviewer",
                        granted_at=datetime.now(UTC),
                    )
                )
            session.commit()
        return self.service.login(
            email=address, password=PASSWORD, client_ip=_random_ip()
        ).secret

    def call(self, method: str, path: str, secret: str | None, body: object = None):  # type: ignore[no-untyped-def]
        headers = {"authorization": f"Bearer {secret}"} if secret else {}
        return self.client.request(method, path, json=body, headers=headers)


@pytest.fixture(scope="module")
def probe() -> Iterator[Probe]:
    AccessProbeNote.__table__.create(engine, checkfirst=True)  # type: ignore[attr-defined]
    outbox = Outbox()
    service = IdentityService(
        stores=sql_store_factory(engine),
        hasher=AppPasswordHasher(),
        mailer=outbox,
        clock=lambda: datetime.now(UTC),
        config=IdentityConfig(
            web_origin="https://web.example",
            registration_open=True,
            max_accounts=1_000_000,
        ),
    )
    app = FastAPI()
    app.include_router(probe_router(AccessDependencies(lambda: service)))
    try:
        with TestClient(app) as client:
            yield Probe(client, service, outbox)
    finally:
        AccessProbeNote.__table__.drop(engine, checkfirst=True)  # type: ignore[attr-defined]


ENDPOINTS = [
    ("GET", "/probe/notes"),
    ("GET", "/probe/notes/{id}"),
    ("POST", "/probe/notes"),
    ("PUT", "/probe/notes/{id}"),
    ("DELETE", "/probe/notes/{id}"),
    ("GET", "/probe/review-queue"),
]


def test_anonymous_and_invalid_sessions_are_rejected(probe: Probe) -> None:
    for secret in (None, "x" * 43):
        for method, path in ENDPOINTS:
            response = probe.call(
                method, path.format(id=uuid.uuid4()), secret, {"text": "t"}
            )
            assert response.status_code == 401, (method, path, secret)
            assert response.headers["www-authenticate"] == "Bearer"


def test_owner_reads_and_writes_own_records(probe: Probe) -> None:
    owner = probe.account()
    created = probe.call("POST", "/probe/notes", owner, {"text": "mine"})
    assert created.status_code == 201
    note_id = created.json()["id"]
    assert probe.call("GET", f"/probe/notes/{note_id}", owner).json()["text"] == "mine"
    assert [n["id"] for n in probe.call("GET", "/probe/notes", owner).json()] == [
        note_id
    ]
    edited = probe.call("PUT", f"/probe/notes/{note_id}", owner, {"text": "edited"})
    assert edited.status_code == 200
    assert probe.call("DELETE", f"/probe/notes/{note_id}", owner).status_code == 204
    assert probe.call("GET", f"/probe/notes/{note_id}", owner).status_code == 404


def test_other_users_get_404_for_foreign_ids_and_see_none_in_lists(
    probe: Probe,
) -> None:
    owner, other = probe.account(), probe.account()
    note_id = probe.call("POST", "/probe/notes", owner, {"text": "private"}).json()[
        "id"
    ]
    probe.call("POST", "/probe/notes", other, {"text": "theirs"})

    foreign = probe.call("GET", f"/probe/notes/{note_id}", other)
    absent = probe.call("GET", f"/probe/notes/{uuid.uuid4()}", other)
    # Foreign and absent are indistinguishable.
    assert foreign.status_code == absent.status_code == 404
    assert foreign.json() == absent.json()
    assert (
        probe.call("PUT", f"/probe/notes/{note_id}", other, {"text": "x"}).status_code
        == 404
    )
    assert probe.call("DELETE", f"/probe/notes/{note_id}", other).status_code == 404
    assert note_id not in [
        n["id"] for n in probe.call("GET", "/probe/notes", other).json()
    ]
    # The owner's record is untouched.
    assert (
        probe.call("GET", f"/probe/notes/{note_id}", owner).json()["text"] == "private"
    )


def test_client_supplied_owner_is_ignored(probe: Probe) -> None:
    victim, attacker = probe.account(), probe.account()
    victim_person = probe.service.current_viewer(secret=victim).person_id
    created = probe.call(
        "POST",
        "/probe/notes",
        attacker,
        {"text": "planted", "owner_person_id": str(victim_person)},
    )
    assert created.status_code == 201
    assert created.json()["id"] not in [
        n["id"] for n in probe.call("GET", "/probe/notes", victim).json()
    ]
    assert created.json()["id"] in [
        n["id"] for n in probe.call("GET", "/probe/notes", attacker).json()
    ]


def test_unverified_accounts_read_but_cannot_write(probe: Probe) -> None:
    unverified = probe.account(verified=False)
    assert probe.call("GET", "/probe/notes", unverified).status_code == 200
    denied = probe.call("POST", "/probe/notes", unverified, {"text": "t"})
    assert denied.status_code == 403
    assert denied.json() == {"detail": "email_unverified"}


def test_reviewer_role_is_scoped_and_grants_no_private_access(probe: Probe) -> None:
    owner, reviewer, ordinary = (
        probe.account(),
        probe.account(reviewer=True),
        probe.account(),
    )
    note_id = probe.call("POST", "/probe/notes", owner, {"text": "private"}).json()[
        "id"
    ]

    assert probe.call("GET", "/probe/review-queue", reviewer).status_code == 200
    denied = probe.call("GET", "/probe/review-queue", ordinary)
    assert denied.status_code == 403 and denied.json() == {"detail": "forbidden"}
    # A role is not a key to other people's private records.
    assert probe.call("GET", f"/probe/notes/{note_id}", reviewer).status_code == 404
    assert probe.call("DELETE", f"/probe/notes/{note_id}", reviewer).status_code == 404


def test_legacy_superuser_has_no_beta_privilege(probe: Probe) -> None:
    owner, superuser = probe.account(), probe.account(superuser=True)
    note_id = probe.call("POST", "/probe/notes", owner, {"text": "private"}).json()[
        "id"
    ]
    assert probe.call("GET", "/probe/review-queue", superuser).status_code == 403
    assert probe.call("GET", f"/probe/notes/{note_id}", superuser).status_code == 404


def test_revoked_session_loses_access_immediately(probe: Probe) -> None:
    owner = probe.account()
    note_id = probe.call("POST", "/probe/notes", owner, {"text": "t"}).json()["id"]
    probe.service.logout(secret=owner)
    assert probe.call("GET", f"/probe/notes/{note_id}", owner).status_code == 401


def test_role_revocation_applies_on_the_next_request(probe: Probe) -> None:
    reviewer = probe.account(reviewer=True)
    assert probe.call("GET", "/probe/review-queue", reviewer).status_code == 200
    account_id = probe.service.current_viewer(secret=reviewer).account_id
    with Session(engine) as session:
        session.execute(
            SkydiverRoleGrant.__table__.delete().where(  # type: ignore[attr-defined]
                SkydiverRoleGrant.__table__.c.account_id == account_id  # type: ignore[attr-defined]
            )
        )
        session.commit()
    assert probe.call("GET", "/probe/review-queue", reviewer).status_code == 403
