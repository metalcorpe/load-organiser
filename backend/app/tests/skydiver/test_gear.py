"""#152 private gear over HTTP against the real PostgreSQL store."""

import json
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.db import engine
from app.skydiver.access.http import AccessDependencies
from app.skydiver.access.policy import Actor, actor_roles
from app.skydiver.gear import policy as gear_policy
from app.skydiver.gear.api import create_router
from app.skydiver.gear.service import GearService, KeyReused
from app.skydiver.gear.store import SqlGearStore, sql_gear_store_factory
from app.tests.skydiver.support import Accounts

NOW = datetime(2026, 11, 3, 12, 0, tzinfo=UTC)


class Api:
    def __init__(self, client: TestClient, accounts: Accounts) -> None:
        self.client = client
        self.accounts = accounts

    def call(
        self, method: str, path: str, secret: str | None = None, body: Any = None,
        **params: Any,
    ) -> httpx2.Response:  # fmt: skip
        headers = {"authorization": f"Bearer {secret}"} if secret else {}
        return self.client.request(
            method, f"/api/skydiver/v1{path}", json=body, headers=headers,
            params=params or None,
        )  # fmt: skip

    def ok(self, method: str, path: str, secret: str, body: Any = None, status: int = 200) -> Any:  # fmt: skip
        response = self.call(method, path, secret, body)
        assert response.status_code == status, response.text
        return response.json() if response.content else None

    def component(self, secret: str, **fields: Any) -> dict[str, Any]:
        body = {
            "client_key": str(uuid.uuid4()),
            "kind": "main",
            "label": "Main",
            **fields,
        }
        return dict(self.ok("POST", "/gear/components", secret, body, 201))

    def rig(self, secret: str, label: str) -> dict[str, Any]:
        body = {"client_key": str(uuid.uuid4()), "label": label}
        return dict(self.ok("POST", "/gear/rigs", secret, body, 201))


@pytest.fixture(scope="module")
def api() -> Iterator[Api]:
    accounts = Accounts.create()
    gear = GearService(stores=sql_gear_store_factory(engine), clock=lambda: NOW)
    app = FastAPI()
    app.include_router(
        create_router(
            service=lambda: gear, access=AccessDependencies(lambda: accounts.service)
        )
    )
    with TestClient(app) as client:
        yield Api(client, accounts)


def test_component_keeps_identifiers_and_is_self_reported(api: Api) -> None:
    owner = api.accounts.session()
    detail = api.component(
        owner, kind="reserve", label="Reserve", manufacturer="PD", model="Optimum 176",
        serial="  0042-ab/7 ", manufactured="2019-04", relation="owned",
        acquisition_method="purchase", acquired="2020",
    )  # fmt: skip
    item = detail["component"]
    assert item["serial"] == "0042-ab/7"
    assert (item["manufactured"], item["acquired"]) == ("2019-04", "2020")
    assert item["provenance"] == "self_reported"
    assert item["version"] == 1
    assert [e["kind"] for e in detail["events"]] == ["created"]
    listed = api.ok("GET", "/gear/components", owner)
    assert [c["component"]["id"] for c in listed] == [item["id"]]


def test_create_is_retry_safe(api: Api) -> None:
    owner = api.accounts.session()
    body = {"client_key": str(uuid.uuid4()), "kind": "aad", "label": "AAD"}
    first = api.call("POST", "/gear/components", owner, body)
    again = api.call("POST", "/gear/components", owner, body)
    assert (first.status_code, again.status_code) == (201, 200)
    assert first.json()["component"]["id"] == again.json()["component"]["id"]
    reused = api.call("POST", "/gear/components", owner, {**body, "label": "Other"})
    assert reused.status_code == 409
    assert len(api.ok("GET", "/gear/components", owner)) == 1


def test_gear_is_owner_only_and_serials_never_match_across_accounts(api: Api) -> None:
    owner, other = api.accounts.session(), api.accounts.session()
    mine = api.component(owner, serial="SN-1234")["component"]
    # Another account can record the same serial; nothing reveals or blocks it.
    theirs = api.component(other, serial="sn 1234")
    assert theirs["same_serial"] == []
    assert api.call("GET", f"/gear/components/{mine['id']}", other).status_code == 404
    assert (
        api.call(
            "PATCH", f"/gear/components/{mine['id']}", other, {"label": "Taken"}
        ).status_code
        == 404
    )
    assert [c["component"]["id"] for c in api.ok("GET", "/gear/components", other)] == [
        theirs["component"]["id"]
    ]
    # Within one's own gear, a repeated serial is pointed out.
    second = api.component(owner, label="Spare", serial="sn1234")
    assert second["same_serial"] == [mine["id"]]
    assert owner not in json.dumps(second)


def test_corrections_keep_earlier_identifiers_but_not_notes(api: Api) -> None:
    owner = api.accounts.session()
    item = api.component(owner, serial="A1", notes="private first note")["component"]
    path = f"/gear/components/{item['id']}"
    detail = api.ok(
        "PATCH", path, owner, {"serial": "A7", "notes": "second note", "version": 1}
    )
    corrected = detail["events"][-1]
    assert corrected["kind"] == "corrected"
    assert corrected["detail"]["serial"] == {"from": "A1", "to": "A7"}
    assert corrected["detail"]["notes"] == "changed"
    assert "private first note" not in json.dumps(detail)
    stale = api.call("PATCH", path, owner, {"label": "Old view", "version": 1})
    assert stale.status_code == 409 and stale.json() == {"detail": "edit_conflict"}


def test_acquisition_details_require_owned(api: Api) -> None:
    owner = api.accounts.session()
    body = {
        "client_key": str(uuid.uuid4()), "kind": "main", "label": "Rental main",
        "relation": "rented", "acquisition_method": "purchase",
    }  # fmt: skip
    refused = api.call("POST", "/gear/components", owner, body)
    assert refused.json() == {"detail": "acquisition_requires_owned"}
    future = {**body, "relation": "owned", "manufactured": "2031"}
    assert api.call("POST", "/gear/components", owner, future).json() == {
        "detail": "manufactured_invalid"
    }


def test_rig_assembly_is_dated_and_moves_keep_history(api: Api) -> None:
    owner = api.accounts.session()
    main = api.component(owner)["component"]
    first, second = api.rig(owner, "Rig A"), api.rig(owner, "Rig B")
    path = f"/gear/components/{main['id']}/rig"
    api.ok(
        "POST", path, owner, {"rig_id": first["id"], "on": "2026-03-01", "version": 1}
    )
    moved = api.ok(
        "POST", path, owner, {"rig_id": second["id"], "on": "2026-09-15", "version": 2}
    )
    assert moved["rig"]["rig_label"] == "Rig B"
    assert [
        (r["rig_label"], r["from_on"], r["until_on"]) for r in moved["rig_history"]
    ] == [
        ("Rig B", "2026-09-15", None),
        ("Rig A", "2026-03-01", "2026-09-15"),
    ]
    # A move cannot be backdated before the current assembly or into the future.
    backdated = api.call(
        "POST", path, owner, {"rig_id": first["id"], "on": "2026-09-01"}
    )
    assert backdated.json() == {"detail": "rig_date_before_current"}
    future = api.call("POST", path, owner, {"rig_id": first["id"], "on": "2026-12-01"})
    assert future.json() == {"detail": "rig_date_in_future"}
    rigs = {r["label"]: r for r in api.ok("GET", "/gear/rigs", owner)}
    assert [c["id"] for c in rigs["Rig B"]["components"]] == [main["id"]]
    assert rigs["Rig A"]["components"] == []

    # Archiving takes it out of the rig today and keeps the dated history.
    archived = api.ok(
        "POST", f"/gear/components/{main['id']}/archive", owner,
        {"archived": True, "version": moved["component"]["version"]},
    )  # fmt: skip
    assert archived["rig"] is None and archived["component"]["archived"] is True
    assert archived["rig_history"][0]["until_on"] == "2026-11-03"
    assert api.ok("GET", "/gear/components", owner) == []
    assert len(api.call("GET", "/gear/components", owner, archived="true").json()) == 1


def test_service_entries_are_self_reported_with_due_dates(api: Api) -> None:
    owner = api.accounts.session()
    reserve = api.component(owner, kind="reserve", label="Reserve")["component"]
    path = f"/gear/components/{reserve['id']}/service"
    body = {
        "client_key": str(uuid.uuid4()), "kind": "repack", "done_on": "2026-10-01",
        "due_on": "2027-04-01", "performed_by": "Rigger at the DZ",
    }  # fmt: skip
    entry = api.ok("POST", path, owner, body, 201)
    assert entry["provenance"] == "self_reported"
    assert api.call("POST", path, owner, body).status_code == 200  # retry
    listed = api.ok("GET", "/gear/components", owner)[0]
    assert listed["next_due"] == "2027-04-01"
    bad = {**body, "client_key": str(uuid.uuid4()), "due_on": "2026-09-01"}
    assert api.call("POST", path, owner, bad).json() == {"detail": "due_before_service"}
    other = api.accounts.session()
    assert api.call("POST", path, other, {**body, "client_key": str(uuid.uuid4())}).status_code == 404  # fmt: skip
    gone = api.call("DELETE", f"{path}/{entry['id']}", owner)
    assert gone.status_code == 204


def test_due_dates_come_from_the_owners_own_records(api: Api) -> None:
    # NOW is 2026-11-03 12:00 UTC: the latest calendar date anywhere is 4 November.
    owner = api.accounts.session()

    def service(component: dict[str, Any], kind: str, done_on: str, due_on: str | None = None) -> None:  # fmt: skip
        body = {"client_key": str(uuid.uuid4()), "kind": kind, "done_on": done_on, "due_on": due_on}  # fmt: skip
        api.ok("POST", f"/gear/components/{component['id']}/service", owner, body, 201)

    reserve = api.component(owner, kind="reserve", label="Reserve")["component"]
    service(reserve, "repack", "2026-05-13")  # + 180 days = 9 November
    aad = api.component(owner, kind="aad", label="Cypres", end_of_life_on="2026-12-04")["component"]  # fmt: skip
    service(aad, "aad_service", "2022-11-03", "2026-11-03")  # overdue by one day
    later = api.component(owner, kind="aad", label="Spare AAD", end_of_life_on="2026-12-05")  # fmt: skip
    archived = api.component(owner, kind="reserve", label="Old reserve")["component"]
    service(archived, "repack", "2026-10-01")
    api.ok("POST", f"/gear/components/{archived['id']}/archive", owner, {"archived": True})  # fmt: skip

    due = api.ok("GET", "/gear/due", owner)
    assert [(d["component"]["label"], d["kind"], d["due_on"], d["status"]) for d in due] == [
        ("Cypres", "service", "2026-11-03", "overdue"),
        ("Reserve", "reserve_repack", "2026-11-09", "soon"),
        ("Cypres", "end_of_life", "2026-12-04", "soon"),  # the 30th day
        ("Spare AAD", "end_of_life", "2026-12-05", "later"),
    ]  # fmt: skip
    repack = due[1]
    assert (repack["basis"], repack["interval_days"], repack["interval_source"]) == (
        "interval", 180, "USPA / FAA 14 CFR 105.43",
    )  # fmt: skip
    assert due[0]["service_kind"] == "aad_service" and due[0]["basis"] == "entered"
    assert later["component"]["end_of_life_on"] == "2026-12-05"

    # The owner's own interval replaces the default.
    patched = api.ok(
        "PATCH", f"/gear/components/{reserve['id']}", owner,
        {"repack_interval_days": 120, "version": reserve["version"]},
    )["component"]  # fmt: skip
    assert patched["repack_interval_days"] == 120
    mine = next(d for d in api.ok("GET", "/gear/due", owner) if d["kind"] == "reserve_repack")  # fmt: skip
    assert (mine["due_on"], mine["interval_days"], mine["interval_source"]) == ("2026-09-10", 120, None)  # fmt: skip
    assert mine["status"] == "overdue"
    bad = api.call(
        "PATCH", f"/gear/components/{reserve['id']}", owner,
        {"repack_interval_days": 0, "version": patched["version"]},
    )  # fmt: skip
    assert bad.status_code == 422

    # Owner-scoped: nobody else sees any of it; no session, no answer.
    assert api.ok("GET", "/gear/due", api.accounts.session()) == []
    assert api.call("GET", "/gear/due").status_code == 401


def test_writes_need_a_confirmed_email_and_limits_apply(
    api: Api, monkeypatch: pytest.MonkeyPatch
) -> None:
    unverified = api.accounts.session(verified=False)
    assert api.call("GET", "/gear/components", unverified).status_code == 200
    body = {"client_key": str(uuid.uuid4()), "kind": "main", "label": "Main"}
    assert api.call("POST", "/gear/components", unverified, body).status_code == 403
    assert api.call("GET", "/gear/components").status_code == 401

    monkeypatch.setattr(gear_policy, "MAX_COMPONENTS", 1)
    owner = api.accounts.session()
    api.component(owner)
    over = api.call("POST", "/gear/components", owner, {**body, "client_key": str(uuid.uuid4())})  # fmt: skip
    assert over.status_code == 409 and over.json() == {
        "detail": "component_limit_reached"
    }


def test_stints_never_overlap_or_end_before_they_start(api: Api) -> None:
    owner = api.accounts.session()
    main = api.component(owner)["component"]
    first, second = api.rig(owner, "Rig A"), api.rig(owner, "Rig B")
    path = f"/gear/components/{main['id']}/rig"
    api.ok("POST", path, owner, {"rig_id": first["id"], "on": "2026-10-01"})
    api.ok("POST", path, owner, {"rig_id": None, "on": "2026-10-20"})
    # Out of any rig, a new stint cannot start before the last one ended.
    overlap = api.call(
        "POST", path, owner, {"rig_id": second["id"], "on": "2026-10-05"}
    )
    assert overlap.status_code == 422
    assert overlap.json() == {"detail": "rig_date_before_current"}

    # NOW is 2026-11-03 UTC, already 2026-11-04 somewhere: a stint may start
    # then, and archiving (component or rig) ends it no earlier than it began.
    placed = api.ok("POST", path, owner, {"rig_id": second["id"], "on": "2026-11-04"})
    archived = api.ok(
        "POST", f"/gear/components/{main['id']}/archive", owner,
        {"archived": True, "version": placed["component"]["version"]},
    )  # fmt: skip
    assert archived["rig_history"][0]["until_on"] == "2026-11-04"

    other = api.component(owner, label="Other main")["component"]
    rig = api.rig(owner, "Rig C")
    api.ok(
        "POST", f"/gear/components/{other['id']}/rig", owner,
        {"rig_id": rig["id"], "on": "2026-11-04"},
    )  # fmt: skip
    api.ok("PATCH", f"/gear/rigs/{rig['id']}", owner, {"archived": True})
    history = api.ok("GET", f"/gear/components/{other['id']}", owner)["rig_history"]
    assert history[0]["until_on"] == "2026-11-04"


class _LateStore(SqlGearStore):
    """Misses the first by-key read, as a request racing a same-key retry would."""

    missed: set[str] = set()

    def _late(self, name: str, found: Any) -> Any:
        if name not in self.missed:
            self.missed.add(name)
            return None
        return found

    def component_by_key(self, actor: Any, client_key: uuid.UUID) -> Any:
        return self._late("component", super().component_by_key(actor, client_key))

    def rig_by_key(self, actor: Any, client_key: uuid.UUID) -> Any:
        return self._late("rig", super().rig_by_key(actor, client_key))

    def service_by_key(self, actor: Any, client_key: uuid.UUID) -> Any:
        return self._late("service", super().service_by_key(actor, client_key))


def test_a_lost_same_key_race_returns_the_winner(api: Api) -> None:
    owner = api.accounts.session()
    actor = _actor(api.accounts.service.current_viewer(secret=owner))
    real = GearService(stores=sql_gear_store_factory(engine), clock=lambda: NOW)
    key, rig_key, service_key = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    fields = {"kind": "main", "label": "Main"}
    first, _ = real.create_component(actor, key, fields)
    real.create_rig(actor, rig_key, "Rig")
    service = {"kind": "repack", "done_on": NOW.date()}
    real.add_service(actor, first.component.id, service_key, service)

    @contextmanager
    def late_stores() -> Iterator[SqlGearStore]:
        with Session(engine) as session:
            yield _LateStore(session)
            session.commit()

    _LateStore.missed = set()
    late = GearService(stores=late_stores, clock=lambda: NOW)
    again, created = late.create_component(actor, key, fields)
    assert (again.component.id, created) == (first.component.id, False)
    assert late.create_rig(actor, rig_key, "Rig")[1] is False
    _, created = late.add_service(actor, first.component.id, service_key, service)
    assert created is False
    _LateStore.missed = set()
    with pytest.raises(KeyReused):
        late.create_component(actor, key, {**fields, "label": "Other"})


def _actor(viewer: Any) -> Actor:
    return Actor(
        account_id=viewer.account_id,
        person_id=viewer.person_id,
        email_verified=viewer.email_verified,
        roles=actor_roles(viewer.roles),
    )
