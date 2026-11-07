"""Account deletion (architecture A9) over the real app against PostgreSQL.

A person with one of everything deletes their account. Nothing that referred to
them remains readable or stored, other people's records are unchanged, and the
email can register again as a new, empty account.
"""

import uuid
from collections.abc import Iterator
from typing import Any

import httpx2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.db import engine
from app.main import create_app
from app.tests.skydiver.support import PASSWORD, Accounts, random_ip

PREFIX = "/api/skydiver/v1"
SOURCE = {"source_url": "https://example.org/dz", "checked_on": "2026-11-01"}


class Api:
    def __init__(self, client: TestClient, accounts: Accounts) -> None:
        self.client, self.accounts = client, accounts

    def call(self, method: str, path: str, secret: str | None, body: Any = None) -> httpx2.Response:  # fmt: skip
        headers = {"authorization": f"Bearer {secret}"} if secret else {}
        return self.client.request(method, PREFIX + path, json=body, headers=headers)

    def ok(self, method: str, path: str, secret: str | None, body: Any = None) -> Any:
        response = self.call(method, path, secret, body)
        assert 200 <= response.status_code < 300, (method, path, response.text)
        return response.json() if response.content else None

    def signed_up(self, email: str) -> str:
        """Register, confirm and sign in `email`; the session secret."""
        service = self.accounts.service
        service.register(email=email, password=PASSWORD, display_name=None, client_ip=random_ip())  # fmt: skip
        service.confirm_email(token=self.accounts.outbox.token_for(email))
        return str(
            service.login(email=email, password=PASSWORD, client_ip=random_ip()).secret
        )


@pytest.fixture(scope="module")
def api() -> Iterator[Api]:
    with TestClient(create_app(include_legacy=False)) as client:
        yield Api(client, Accounts.create())


def _references(person_id: str) -> dict[str, int]:
    """Rows in any table that still name this person, by column."""
    found: dict[str, int] = {}
    with engine.connect() as conn:
        columns = conn.execute(
            text(
                "SELECT table_name, column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND data_type = 'uuid' "
                "AND (column_name LIKE '%person_id' OR column_name = 'id' "
                "AND table_name = 'skydiver_person')"
            )
        ).all()
        for table, column in columns:
            count = conn.execute(
                text(f'SELECT count(*) FROM "{table}" WHERE "{column}" = :p'),  # noqa: S608
                {"p": person_id},
            ).scalar_one()
            if count:
                found[f"{table}.{column}"] = count
    return found


def test_deleting_an_account_removes_everything_it_owned(api: Api) -> None:
    email = f"leaving-{uuid.uuid4().hex[:10]}@example.com"
    me = api.signed_up(email)
    friend = api.accounts.session()
    reviewer = api.accounts.session(reviewer=True)
    person_id = api.ok("GET", "/auth/session", me)["person_id"]
    handle, friend_handle = (f"d{uuid.uuid4().hex[:12]}" for _ in range(2))

    # One of everything, including relations with someone else.
    api.ok("PUT", "/me/profile", me, {"handle": handle, "display_name": "Leaving", "discoverable": True})  # fmt: skip
    api.ok("PUT", "/me/profile", friend, {"handle": friend_handle, "display_name": "Staying", "discoverable": True})  # fmt: skip
    api.ok("PUT", f"/people/{handle}/follow", friend)
    api.ok("POST", f"/me/people/requests/{friend_handle}/approve", me)
    api.ok("PUT", f"/people/{friend_handle}/follow", me)
    venue = api.ok("POST", "/directory/venues", reviewer, {"name": f"Dl{uuid.uuid4().hex[:8]}", "country": "ES", **SOURCE})  # fmt: skip
    component = api.ok("POST", "/gear/components", me, {"client_key": str(uuid.uuid4()), "kind": "main", "label": "Main"})["component"]  # fmt: skip
    api.ok("POST", "/places", me, {"name": "Strip", "country": "PT"})
    jump = api.ok("POST", "/jumps", me, {"client_key": str(uuid.uuid4()), "jumped_on": "2026-10-10", "jump_type": "belly", "venue_id": venue["id"], "component_ids": [component["id"]]})["jump"]  # fmt: skip
    api.ok("PUT", "/history/baseline", me, {"prior_jumps": 10, "before_on": "2026-01-01"})  # fmt: skip
    api.ok("POST", "/plans", me, {"title": "Trip", "starts_on": "2026-12-03", "ends_on": "2026-12-04", "venue_id": venue["id"]})  # fmt: skip
    post = api.ok("POST", f"/me/jumps/{jump['id']}/post", me, {"jump_version": jump["version"], "audience": "public", "shares": ["venue"]})  # fmt: skip
    api.ok("POST", f"/people/{friend_handle}/reports", me, {"reason": "spam"})
    assert _references(person_id), "the fixture must create referencing rows"

    # A wrong password changes nothing.
    wrong = api.call(
        "POST", "/auth/account/deletion", me, {"password": "not it at all"}
    )
    assert (wrong.status_code, wrong.json()) == (422, {"detail": "password_confirmation_failed"})  # fmt: skip
    assert api.ok("GET", f"/posts/{post['id']}", None)["id"] == post["id"]

    api.ok("POST", "/auth/account/deletion", me, {"password": PASSWORD})

    assert api.call("GET", "/auth/session", me).status_code == 401
    assert api.call("GET", f"/posts/{post['id']}", None).status_code == 404
    assert api.call("GET", f"/people/{handle}", friend).status_code == 404
    assert api.call("GET", f"/venues/{venue['id']}/posts", None).json()["items"] == []
    for relation in ("followers", "following", "requests"):
        assert api.ok("GET", f"/me/people/{relation}", friend) == [], relation
    assert _references(person_id) == {}

    # Someone else's records and the public directory are unchanged.
    assert api.ok("GET", f"/people/{friend_handle}", friend)["handle"] == friend_handle
    assert venue["id"] in api.call("GET", f"/venues/{venue['id']}", None).text

    # The address can start again, empty: nothing comes back.
    again = api.signed_up(email)
    assert api.ok("GET", "/auth/session", again)["person_id"] != person_id
    assert api.ok("GET", "/me/profile", again) is None
    assert api.ok("GET", "/jumps", again)["items"] == []


def test_deletion_needs_a_session(api: Api) -> None:
    response = api.call("POST", "/auth/account/deletion", None, {"password": PASSWORD})
    assert response.status_code == 401
