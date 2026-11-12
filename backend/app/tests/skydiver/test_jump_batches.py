"""Changing many jumps at once, and its undo, over HTTP against PostgreSQL."""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session, col, update

from app.core.db import engine
from app.skydiver.access.http import AccessDependencies
from app.skydiver.access.policy import Actor
from app.skydiver.directory.api import create_router as create_directory_router
from app.skydiver.directory.service import DirectoryService
from app.skydiver.directory.store import sql_directory_store_factory
from app.skydiver.directory.tables import SkydiverVenue
from app.skydiver.gear.api import create_router as create_gear_router
from app.skydiver.gear.service import GearService
from app.skydiver.gear.store import sql_gear_store_factory
from app.skydiver.logbook.api import create_router
from app.skydiver.logbook.service import LogbookService
from app.skydiver.logbook.store import SqlLogbookStore, sql_logbook_store_factory
from app.skydiver.logbook.tables import SkydiverJump
from app.tests.skydiver.support import Accounts

NOW = datetime(2026, 11, 3, 12, 0, tzinfo=UTC)
SOURCE = {"source_url": "https://example.org/dz", "checked_on": "2026-11-01"}


class Api:
    def __init__(self, client: TestClient, accounts: Accounts, clock: list[datetime]) -> None:  # fmt: skip
        self.client = client
        self.accounts = accounts
        self.clock = clock
        self.reviewer = accounts.session(reviewer=True)

    def call(self, method: str, path: str, secret: str | None = None, body: Any = None) -> httpx2.Response:  # fmt: skip
        headers = {"authorization": f"Bearer {secret}"} if secret else {}
        return self.client.request(
            method, f"/api/skydiver/v1{path}", json=body, headers=headers
        )

    def ok(self, method: str, path: str, secret: str, body: Any = None, status: int = 200) -> Any:  # fmt: skip
        response = self.call(method, path, secret, body)
        assert response.status_code == status, response.text
        return response.json() if response.content else None

    def place(self, secret: str, name: str = "Farm strip") -> str:
        body = {"name": name, "country": "PT"}
        return str(self.ok("POST", "/places", secret, body, 201)["id"])

    def venue(self) -> str:
        body = {"name": f"Bt{uuid.uuid4().hex[:8]} DZ", "country": "ES", **SOURCE}
        venue = self.ok("POST", "/directory/venues", self.reviewer, body, 201)
        self.ok(
            "POST", f"/directory/venues/{venue['id']}/status", self.reviewer,
            {"status": "listed"},
        )  # fmt: skip
        return str(venue["id"])

    def component(self, secret: str, label: str) -> str:
        body = {"client_key": str(uuid.uuid4()), "kind": "main", "label": label}
        return str(self.ok("POST", "/gear/components", secret, body, 201)["component"]["id"])  # fmt: skip

    def jumps(self, secret: str, place: str, count: int, **fields: Any) -> list[dict[str, Any]]:  # fmt: skip
        made = []
        for n in range(count):
            body = {
                "client_key": str(uuid.uuid4()), "jumped_on": f"2026-10-{n + 1:02d}",
                "jump_type": "belly", "place_id": place, **fields,
            }  # fmt: skip
            made.append(self.ok("POST", "/jumps", secret, body, 201)["jump"])
        return made

    def get(self, secret: str, jump_id: str) -> dict[str, Any]:
        return dict(self.ok("GET", f"/jumps/{jump_id}", secret))

    def preview(self, secret: str, ids: list[str], changes: dict[str, Any]) -> httpx2.Response:  # fmt: skip
        return self.call("POST", "/jumps/batch/preview", secret, {"jump_ids": ids, "changes": changes})  # fmt: skip

    def apply(self, secret: str, jumps: list[dict[str, Any]], changes: dict[str, Any]) -> httpx2.Response:  # fmt: skip
        body = {"jumps": [{"id": j["id"], "version": j["version"]} for j in jumps], "changes": changes}  # fmt: skip
        return self.call("POST", "/jumps/batch", secret, body)

    def undo(self, secret: str, batch_id: str) -> httpx2.Response:
        return self.call("POST", "/jumps/batch/undo", secret, {"batch_id": batch_id})


@pytest.fixture(scope="module")
def api() -> Iterator[Api]:
    accounts = Accounts.create()
    clock = [NOW]
    directory = DirectoryService(
        stores=sql_directory_store_factory(engine), clock=lambda: clock[0]
    )
    gear = GearService(stores=sql_gear_store_factory(engine), clock=lambda: clock[0])
    logbook = LogbookService(
        stores=sql_logbook_store_factory(engine),
        clock=lambda: clock[0],
        directory=directory,
    )
    access = AccessDependencies(lambda: accounts.service)
    app = FastAPI()
    app.include_router(create_router(service=lambda: logbook, access=access))
    app.include_router(
        create_directory_router(service=lambda: directory, access=access)
    )
    app.include_router(create_gear_router(service=lambda: gear, access=access))
    with TestClient(app) as client:
        yield Api(client, accounts, clock)


@pytest.fixture(autouse=True)
def _reset_clock(api: Api) -> Iterator[None]:
    api.clock[0] = NOW
    yield
    api.clock[0] = NOW


def test_preview_counts_what_would_change_and_writes_nothing(api: Api) -> None:
    owner = api.accounts.session()
    place = api.place(owner)
    jumps = api.jumps(owner, place, 3)
    already = api.ok(
        "PATCH", f"/jumps/{jumps[2]['id']}", owner,
        {"jump_type": "freefly", "aircraft": "Cessna 208", "version": jumps[2]["version"]},
    )["jump"]  # fmt: skip
    stranger = api.accounts.session()
    foreign = api.jumps(stranger, api.place(stranger, "Other"), 1)
    ids = [j["id"] for j in jumps] + [foreign[0]["id"], str(uuid.uuid4())]

    preview = api.preview(
        owner, ids, {"jump_type": "freefly", "aircraft": "Cessna 208"}
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert (body["changing"], body["missing"]) == (2, 2)
    assert [(i["id"], i["will_change"], i["version"]) for i in body["items"]] == [
        (jumps[0]["id"], True, 1),
        (jumps[1]["id"], True, 1),
        (jumps[2]["id"], False, already["version"]),
    ]
    assert body["location"] is None and body["components"] is None
    # Nothing was written.
    assert api.get(owner, jumps[0]["id"])["jump"]["jump_type"] == "belly"
    assert api.ok("GET", "/jumps/batch/latest", owner) == {"latest": None}


def test_apply_skips_a_jump_edited_since_the_preview(api: Api) -> None:
    owner = api.accounts.session()
    place = api.place(owner)
    jumps = api.jumps(owner, place, 3)
    # Edited in another tab after the preview showed version 1.
    api.ok(
        "PATCH", f"/jumps/{jumps[1]['id']}", owner,
        {"notes": "meanwhile", "version": jumps[1]["version"]},
    )  # fmt: skip
    applied = api.apply(
        owner, jumps, {"jump_type": "freefly", "aircraft": "Cessna 208"}
    )
    assert applied.status_code == 200, applied.text
    result = applied.json()
    assert result["changed"] == [jumps[0]["id"], jumps[2]["id"]]
    assert result["skipped"] == [{"id": jumps[1]["id"], "reason": "edited"}]
    assert result["unchanged"] == []

    first = api.get(owner, jumps[0]["id"])
    assert (first["jump"]["jump_type"], first["jump"]["aircraft"]) == ("freefly", "Cessna 208")  # fmt: skip
    assert first["jump"]["version"] == 2
    # Recorded in the jump's own history like a single edit, with the batch.
    event = first["events"][-1]
    assert event["kind"] == "corrected"
    assert event["detail"]["jump_type"] == {"from": "belly", "to": "freefly"}
    assert event["detail"]["aircraft"] == {"from": None, "to": "Cessna 208"}
    assert event["detail"]["batch"] == {"id": result["batch_id"], "version": 2}
    # The edited jump was not overwritten.
    kept = api.get(owner, jumps[1]["id"])["jump"]
    assert (kept["jump_type"], kept["aircraft"], kept["notes"]) == ("belly", None, "meanwhile")  # fmt: skip

    latest = api.ok("GET", "/jumps/batch/latest", owner)["latest"]
    assert latest["batch_id"] == result["batch_id"]
    assert (latest["changed"], latest["undone"], latest["can_undo"]) == (2, False, True)


def test_place_and_gear_change_and_undo_puts_back_only_untouched_jumps(
    api: Api,
) -> None:
    owner = api.accounts.session()
    place = api.place(owner)
    venue = api.venue()
    old, new = api.component(owner, "Old main"), api.component(owner, "New main")
    jumps = api.jumps(owner, place, 3, component_ids=[old], aircraft="Islander")
    changes = {"venue_id": venue, "place_id": None, "component_ids": [new], "aircraft": None}  # fmt: skip
    preview = api.preview(owner, [j["id"] for j in jumps], changes).json()
    assert preview["location"]["id"] == venue and preview["location"]["kind"] == "venue"
    assert [c["label"] for c in preview["components"]] == ["New main"]
    result = api.apply(owner, jumps, changes).json()
    assert len(result["changed"]) == 3
    moved = api.get(owner, jumps[0]["id"])["jump"]
    assert moved["location"]["id"] == venue
    assert [c["id"] for c in moved["components"]] == [new]
    assert moved["aircraft"] is None

    # One jump edited after the change keeps that edit; the others go back.
    edited = api.get(owner, jumps[2]["id"])["jump"]
    api.ok("PATCH", f"/jumps/{edited['id']}", owner, {"jump_type": "angle", "version": edited["version"]})  # fmt: skip
    undo = api.undo(owner, result["batch_id"])
    assert undo.status_code == 200, undo.text
    assert undo.json() == {
        "restored": [jumps[0]["id"], jumps[1]["id"]],
        "skipped": [{"id": jumps[2]["id"], "reason": "edited"}],
    }
    back = api.get(owner, jumps[0]["id"])
    assert back["jump"]["location"] == {
        "kind": "place", "id": place, "name": "Farm strip", "country": "PT", "closed": False,
    }  # fmt: skip
    assert [c["id"] for c in back["jump"]["components"]] == [old]
    assert back["jump"]["aircraft"] == "Islander"
    assert back["events"][-1]["detail"]["undo_of"] == result["batch_id"]
    assert back["events"][-1]["kind"] == "corrected"
    still = api.get(owner, jumps[2]["id"])["jump"]
    assert (still["jump_type"], still["location"]["id"]) == ("angle", venue)

    # Once only.
    again = api.undo(owner, result["batch_id"])
    assert (again.status_code, again.json()) == (409, {"detail": "already_undone"})
    latest = api.ok("GET", "/jumps/batch/latest", owner)["latest"]
    assert (latest["undone"], latest["can_undo"]) == (True, False)


def test_undo_is_for_the_latest_change_within_24_hours(api: Api) -> None:
    owner = api.accounts.session()
    jumps = api.jumps(owner, api.place(owner), 2)
    first = api.apply(owner, jumps[:1], {"jump_type": "freefly"}).json()
    second = api.apply(owner, jumps[1:], {"jump_type": "angle"}).json()
    # A later change of many jumps replaces the earlier one's undo.
    older = api.undo(owner, first["batch_id"])
    assert (older.status_code, older.json()) == (409, {"detail": "undo_unavailable"})

    api.clock[0] = NOW + timedelta(hours=24)
    latest = api.ok("GET", "/jumps/batch/latest", owner)["latest"]
    assert latest["batch_id"] == second["batch_id"] and latest["can_undo"] is False
    expired = api.undo(owner, second["batch_id"])
    assert (expired.status_code, expired.json()) == (
        409,
        {"detail": "undo_unavailable"},
    )
    assert api.get(owner, jumps[1]["id"])["jump"]["jump_type"] == "angle"


def test_nobody_else_can_see_change_or_undo_the_owners_jumps(api: Api) -> None:
    owner, other = api.accounts.session(), api.accounts.session()
    place = api.place(owner)
    jumps = api.jumps(owner, place, 2)
    result = api.apply(owner, jumps, {"aircraft": "Skyvan"}).json()

    preview = api.preview(other, [j["id"] for j in jumps], {"aircraft": "x"}).json()
    assert (preview["items"], preview["missing"]) == ([], 2)
    mine = [{"id": j["id"], "version": 2} for j in jumps]
    taken = api.call("POST", "/jumps/batch", other, {"jumps": mine, "changes": {"aircraft": "x"}})  # fmt: skip
    assert taken.json()["skipped"] == [
        {"id": j["id"], "reason": "not_found"} for j in jumps
    ]
    assert taken.json()["batch_id"] is None
    # The owner's batch answers exactly like one that does not exist.
    theirs = api.undo(other, result["batch_id"])
    absent = api.undo(other, str(uuid.uuid4()))
    assert (theirs.status_code, theirs.json()) == (absent.status_code, absent.json())
    assert api.ok("GET", "/jumps/batch/latest", other) == {"latest": None}
    # Another person's place or gear cannot be set.
    owners_part = api.component(owner, "Owner main")
    gear = api.preview(other, [str(uuid.uuid4())], {"component_ids": [owners_part]})
    assert gear.json() == {"detail": "component_unknown"}
    spot = api.preview(
        other, [str(uuid.uuid4())], {"place_id": place, "venue_id": None}
    )
    assert spot.json() == {"detail": "place_unknown"}
    assert {api.get(owner, j["id"])["jump"]["aircraft"] for j in jumps} == {"Skyvan"}

    for method, path in (
        ("POST", "/jumps/batch/preview"), ("POST", "/jumps/batch"),
        ("GET", "/jumps/batch/latest"), ("POST", "/jumps/batch/undo"),
    ):  # fmt: skip
        assert api.call(method, path, None, {}).status_code == 401, path
    unverified = api.accounts.session(verified=False)
    refused = api.call("POST", "/jumps/batch", unverified, {"jumps": mine, "changes": {"aircraft": "x"}})  # fmt: skip
    assert refused.status_code == 403


def test_at_most_200_jumps_at_once_and_something_to_change(api: Api) -> None:
    owner = api.accounts.session()
    ids = [str(uuid.uuid4()) for _ in range(201)]
    too_many = api.preview(owner, ids, {"jump_type": "belly"})
    assert (too_many.status_code, too_many.json()) == (
        422,
        {"detail": "too_many_jumps"},
    )
    applied = api.call(
        "POST", "/jumps/batch", owner,
        {"jumps": [{"id": i, "version": 1} for i in ids], "changes": {"jump_type": "belly"}},
    )  # fmt: skip
    assert applied.json() == {"detail": "too_many_jumps"}
    fits = api.preview(owner, ids[:200], {"jump_type": "belly"})
    assert fits.status_code == 200 and fits.json()["missing"] == 200
    nothing = api.preview(owner, ids[:1], {})
    assert nothing.json() == {"detail": "nothing_to_change"}
    unknown = api.preview(owner, ids[:1], {"notes": "x"})
    assert unknown.status_code == 422
    half = api.preview(owner, ids[:1], {"venue_id": None, "place_id": None})
    assert half.json() == {"detail": "location_required"}


def test_jumps_that_already_have_the_values_are_left_alone(api: Api) -> None:
    owner = api.accounts.session()
    jumps = api.jumps(owner, api.place(owner), 2, jump_type="freefly")
    result = api.apply(owner, jumps, {"jump_type": "freefly"}).json()
    assert result == {
        "batch_id": None, "changed": [], "skipped": [],
        "unchanged": [j["id"] for j in jumps],
    }  # fmt: skip
    assert api.get(owner, jumps[0]["id"])["jump"]["version"] == 1
    assert api.ok("GET", "/jumps/batch/latest", owner) == {"latest": None}


def test_undo_checks_earlier_values_like_an_edit(api: Api) -> None:
    """A dropzone no longer listed is not put back; a merged one comes back as the
    venue it was merged into."""
    owner = api.accounts.session()
    place = api.place(owner)
    unlisted, merged, keep = api.venue(), api.venue(), api.venue()
    first = api.jumps(owner, place, 1, venue_id=unlisted, place_id=None)
    second = api.ok(
        "POST", "/jumps", owner,
        {"client_key": str(uuid.uuid4()), "jumped_on": "2026-10-20", "jump_type": "belly",
         "venue_id": merged},
        201,
    )["jump"]  # fmt: skip
    result = api.apply(owner, [*first, second], {"place_id": place, "venue_id": None})
    assert len(result.json()["changed"]) == 2

    with Session(engine) as session:  # taken off the directory by hand (no API does it)
        session.execute(
            update(SkydiverVenue)
            .where(col(SkydiverVenue.id) == uuid.UUID(unlisted))
            .values(status="draft")
        )
        session.commit()
    api.ok("POST", f"/directory/venues/{merged}/merge", api.reviewer, {"into": keep})

    undo = api.undo(owner, result.json()["batch_id"]).json()
    assert undo == {
        "restored": [second["id"]],
        "skipped": [{"id": first[0]["id"], "reason": "invalid"}],
    }
    assert api.get(owner, second["id"])["jump"]["location"]["id"] == keep
    assert api.get(owner, first[0]["id"])["jump"]["location"]["id"] == place


def test_a_jump_saved_elsewhere_during_the_undo_is_skipped_not_fatal(api: Api) -> None:
    owner = api.accounts.session()
    jumps = api.jumps(owner, api.place(owner), 2)
    batch = api.apply(owner, jumps, {"jump_type": "freefly"}).json()["batch_id"]
    target = uuid.UUID(jumps[0]["id"])

    class Racing(SqlLogbookStore):
        """Another tab saves the first jump between the undo's read and its update."""

        def update_jump(self, actor: Actor, jump_id: uuid.UUID, *args: Any, **kwargs: Any) -> None:  # fmt: skip
            if jump_id == target:
                with Session(engine) as other:
                    other.execute(
                        update(SkydiverJump)
                        .where(col(SkydiverJump.id) == target)
                        .values(version=SkydiverJump.version + 1)
                    )
                    other.commit()
            super().update_jump(actor, jump_id, *args, **kwargs)

    @contextmanager
    def stores() -> Iterator[SqlLogbookStore]:
        with Session(engine) as session:
            try:
                yield Racing(session)
            except BaseException:
                session.rollback()
                raise
            session.commit()

    directory = DirectoryService(stores=sql_directory_store_factory(engine), clock=lambda: NOW)  # fmt: skip
    service = LogbookService(stores=stores, clock=lambda: NOW, directory=directory)
    viewer = api.accounts.service.current_viewer(secret=owner)
    actor = Actor(
        account_id=viewer.account_id, person_id=viewer.person_id,
        email_verified=True, roles=frozenset(),
    )  # fmt: skip
    result = service.undo_batch(actor, uuid.UUID(batch))
    assert result.restored == [uuid.UUID(jumps[1]["id"])]
    assert result.skipped == [(target, "edited")]
    assert api.get(owner, jumps[1]["id"])["jump"]["jump_type"] == "belly"
    assert api.get(owner, jumps[0]["id"])["jump"]["jump_type"] == "freefly"


def test_a_jump_already_holding_the_earlier_values_is_left_alone(api: Api) -> None:
    """A merged dropzone resolves to the place the change set: nothing to put back."""
    owner = api.accounts.session()
    dupe, keep = api.venue(), api.venue()
    jump = api.ok(
        "POST", "/jumps", owner,
        {"client_key": str(uuid.uuid4()), "jumped_on": "2026-10-20", "jump_type": "belly",
         "venue_id": dupe},
        201,
    )["jump"]  # fmt: skip
    batch = api.apply(owner, [jump], {"venue_id": keep, "place_id": None}).json()
    api.ok("POST", f"/directory/venues/{dupe}/merge", api.reviewer, {"into": keep})
    undo = api.undo(owner, batch["batch_id"])
    assert undo.json() == {"restored": [], "skipped": []}
    after = api.get(owner, jump["id"])
    assert after["jump"]["version"] == 2  # not bumped by the undo
    assert all("undo_of" not in e["detail"] for e in after["events"])
