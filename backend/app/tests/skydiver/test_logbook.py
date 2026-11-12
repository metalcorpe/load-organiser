"""#153 private jump logbook over HTTP against the real PostgreSQL store."""

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
from app.skydiver.directory.api import create_router as create_directory_router
from app.skydiver.directory.service import DirectoryService
from app.skydiver.directory.store import sql_directory_store_factory
from app.skydiver.gear.api import create_router as create_gear_router
from app.skydiver.gear.service import GearService
from app.skydiver.gear.store import sql_gear_store_factory
from app.skydiver.logbook.api import create_router
from app.skydiver.logbook.service import LogbookService
from app.skydiver.logbook.store import SqlLogbookStore, sql_logbook_store_factory
from app.tests.skydiver.support import Accounts

NOW = datetime(2026, 11, 3, 12, 0, tzinfo=UTC)
SOURCE = {"source_url": "https://example.org/dz", "checked_on": "2026-11-01"}


class Api:
    def __init__(
        self, client: TestClient, accounts: Accounts, directory: DirectoryService
    ) -> None:
        self.client = client
        self.accounts = accounts
        self.directory = directory
        self.reviewer = accounts.session(reviewer=True)

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

    def venue(self) -> dict[str, Any]:
        body = {"name": f"Lb{uuid.uuid4().hex[:8]} DZ", "country": "ES", **SOURCE}
        venue = self.ok("POST", "/directory/venues", self.reviewer, body, 201)
        self.ok(
            "POST", f"/directory/venues/{venue['id']}/status", self.reviewer,
            {"status": "listed"},
        )  # fmt: skip
        return dict(venue)

    def place(self, secret: str) -> dict[str, Any]:
        body = {"name": "Farm strip", "country": "PT"}
        return dict(self.ok("POST", "/places", secret, body, 201))

    def component(self, secret: str, label: str = "Main") -> dict[str, Any]:
        body = {"client_key": str(uuid.uuid4()), "kind": "main", "label": label}
        return dict(self.ok("POST", "/gear/components", secret, body, 201)["component"])

    def jump(self, secret: str, **fields: Any) -> httpx2.Response:
        body = {
            "client_key": str(uuid.uuid4()),
            "jumped_on": "2026-10-10",
            "jump_type": "belly",
            **fields,
        }
        return self.call("POST", "/jumps", secret, body)


def _actor(viewer: Any) -> Actor:
    return Actor(
        account_id=viewer.account_id,
        person_id=viewer.person_id,
        email_verified=viewer.email_verified,
        roles=actor_roles(viewer.roles),
    )


@pytest.fixture(scope="module")
def api() -> Iterator[Api]:
    accounts = Accounts.create()
    directory = DirectoryService(
        stores=sql_directory_store_factory(engine), clock=lambda: NOW
    )
    gear = GearService(stores=sql_gear_store_factory(engine), clock=lambda: NOW)
    logbook = LogbookService(
        stores=sql_logbook_store_factory(engine), clock=lambda: NOW, directory=directory
    )
    access = AccessDependencies(lambda: accounts.service)
    app = FastAPI()
    app.include_router(create_router(service=lambda: logbook, access=access))
    app.include_router(
        create_directory_router(service=lambda: directory, access=access)
    )
    app.include_router(create_gear_router(service=lambda: gear, access=access))
    with TestClient(app) as client:
        yield Api(client, accounts, directory)


def test_jump_at_a_listed_dz_keeps_what_was_entered(api: Api) -> None:
    owner = api.accounts.session()
    venue = api.venue()
    sent = api.jump(
        owner, venue_id=venue["id"], jump_number=412, exit_time="14:05",
        time_zone="Europe/Madrid", exit_altitude=13500, deployment_altitude=3500,
        altitude_unit="ft", altitude_datum="agl", freefall_seconds=60,
        notes="  Four-way, good exit. ", links=["https://example.org/video"],
    )  # fmt: skip
    assert sent.status_code == 201, sent.text
    jump = sent.json()["jump"]
    assert jump["jumped_on"] == "2026-10-10"  # a calendar date, never shifted
    assert jump["location"] == {
        "kind": "venue", "id": venue["id"], "name": venue["name"], "country": "ES",
        "closed": False,
    }  # fmt: skip
    assert (jump["exit_time"], jump["time_zone"]) == ("14:05:00", "Europe/Madrid")
    assert (jump["exit_altitude"], jump["altitude_unit"], jump["altitude_datum"]) == (
        13500, "ft", "agl",
    )  # fmt: skip
    assert jump["notes"] == "Four-way, good exit."
    assert (jump["source"], jump["provenance"]) == ("manual", "self_reported")
    assert sent.json()["events"][0]["kind"] == "created"

    page = api.ok("GET", "/jumps", owner)
    assert page["recorded_total"] == 1
    assert [i["id"] for i in page["items"]] == [jump["id"]]
    assert "notes" not in page["items"][0]  # lists carry no private text


def test_minimal_jump_needs_no_gear_and_invents_nothing(api: Api) -> None:
    owner = api.accounts.session()
    place = api.place(owner)
    jump = api.jump(owner, place_id=place["id"], jump_type="unspecified")
    assert jump.status_code == 201, jump.text
    body = jump.json()["jump"]
    assert body["location"]["kind"] == "place"
    assert body["location"]["name"] == "Farm strip"
    for name in (
        "jump_number", "exit_time", "time_zone", "exit_altitude",
        "deployment_altitude", "altitude_unit", "freefall_seconds", "other_gear",
        "notes",
    ):  # fmt: skip
        assert body[name] is None, name
    assert body["altitude_datum"] == "unspecified"
    assert body["components"] == [] and body["links"] == []

    # A place a jump uses cannot be deleted; the jump keeps its location.
    refused = api.call("DELETE", f"/places/{place['id']}", owner)
    assert refused.status_code == 422
    assert refused.json() == {"detail": "place_in_use"}


@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        ({"jumped_on": "2026-11-05"}, "jump_date_in_future"),
        ({"exit_time": "10:00"}, "time_zone_required"),
        ({"exit_time": "10:00", "time_zone": "Mars/Base"}, "time_zone_invalid"),
        ({"exit_altitude": 4000}, "altitude_unit_required"),
        (
            {"exit_altitude": 3000, "deployment_altitude": 4000, "altitude_unit": "m"},
            "deployment_above_exit",
        ),
        ({"links": ["https://a.example"] * 6}, "too_many_links"),
        ({"links": ["javascript:alert(1)"]}, "link_invalid"),
        ({"venue_id": None}, "location_required"),
    ],
)
def test_validation(api: Api, fields: dict[str, Any], expected: str) -> None:
    owner = api.accounts.session()
    base = {"place_id": api.place(owner)["id"]} if "venue_id" not in fields else {}
    response = api.jump(owner, **base, **fields)
    assert response.status_code == 422, response.text
    assert response.json() == {"detail": expected}


def test_jump_date_may_be_today_anywhere(api: Api) -> None:
    owner = api.accounts.session()
    place = api.place(owner)
    # NOW is 2026-11-03 12:00 UTC; it is already 2026-11-04 in Kiribati.
    assert api.jump(owner, place_id=place["id"], jumped_on="2026-11-04").status_code == 201  # fmt: skip


def test_equipment_actually_used_is_the_owners_own(api: Api) -> None:
    owner = api.accounts.session()
    place = api.place(owner)
    main = api.component(owner)
    other = api.accounts.session()
    foreign = api.component(other, "Their main")

    refused = api.jump(owner, place_id=place["id"], component_ids=[foreign["id"]])
    assert refused.json() == {"detail": "component_unknown"}

    used = api.jump(
        owner, place_id=place["id"], component_ids=[main["id"], main["id"]],
        other_gear="Rented reserve",
    )  # fmt: skip
    assert used.status_code == 201
    assert [c["id"] for c in used.json()["jump"]["components"]] == [main["id"]]
    assert used.json()["jump"]["other_gear"] == "Rented reserve"

    # Gear a jump used cannot be deleted; archiving keeps the jump's reference.
    gone = api.call("DELETE", f"/gear/components/{main['id']}", owner)
    assert gone.status_code == 422 and gone.json() == {"detail": "component_in_use"}
    api.ok("POST", f"/gear/components/{main['id']}/archive", owner, {"archived": True})
    jump_id = used.json()["jump"]["id"]
    kept = api.ok("GET", f"/jumps/{jump_id}", owner)["jump"]["components"]
    assert kept == [
        {"id": main["id"], "kind": "main", "label": "Main", "archived": True}
    ]


def test_create_is_retry_safe_and_never_resurrects(api: Api) -> None:
    owner = api.accounts.session()
    place = api.place(owner)
    body = {
        "client_key": str(uuid.uuid4()), "jumped_on": "2026-10-10",
        "jump_type": "freefly", "place_id": place["id"],
    }  # fmt: skip
    first = api.call("POST", "/jumps", owner, body)
    again = api.call("POST", "/jumps", owner, body)
    assert (first.status_code, again.status_code) == (201, 200)
    assert first.json()["jump"]["id"] == again.json()["jump"]["id"]
    assert api.ok("GET", "/jumps", owner)["recorded_total"] == 1

    reused = api.call("POST", "/jumps", owner, {**body, "jump_type": "angle"})
    assert reused.status_code == 409
    assert reused.json() == {"detail": "client_key_reused"}

    jump = first.json()["jump"]
    deleted = api.call("DELETE", f"/jumps/{jump['id']}", owner, version=jump["version"])
    assert deleted.status_code == 204
    replay = api.call("POST", "/jumps", owner, body)
    assert replay.status_code == 410 and replay.json() == {"detail": "jump_deleted"}
    assert api.ok("GET", "/jumps", owner)["recorded_total"] == 0


def test_likely_duplicates_warn_and_two_real_jumps_save(api: Api) -> None:
    owner = api.accounts.session()
    place = api.place(owner)
    first = api.jump(owner, place_id=place["id"]).json()["jump"]

    same_day = api.jump(owner, place_id=place["id"])
    assert same_day.status_code == 409
    assert same_day.json() == {
        "detail": "likely_duplicate", "duplicate_of": first["id"]
    }  # fmt: skip
    distinct = api.jump(owner, place_id=place["id"], confirm_distinct=True)
    assert distinct.status_code == 201

    # A different exit time on the same day is not a likely duplicate.
    later = api.jump(
        owner, place_id=place["id"], exit_time="16:00", time_zone="Europe/Lisbon"
    )
    assert later.status_code == 201

    numbered = api.jump(owner, place_id=place["id"], jumped_on="2026-10-11",
                        jump_number=7).json()["jump"]  # fmt: skip
    clash = api.jump(owner, place_id=place["id"], jumped_on="2026-10-12", jump_number=7)
    assert clash.json()["duplicate_of"] == numbered["id"]
    kept = api.jump(
        owner, place_id=place["id"], jumped_on="2026-10-12", jump_number=7,
        confirm_distinct=True,
    ).json()  # fmt: skip
    assert kept["same_number"] == [numbered["id"]]
    assert api.ok("GET", "/jumps", owner)["recorded_total"] == 5


def test_edits_compare_and_swap_and_keep_corrections(api: Api) -> None:
    owner = api.accounts.session()
    place = api.place(owner)
    venue = api.venue()
    jump = api.jump(owner, place_id=place["id"], notes="secret note").json()["jump"]
    path = f"/jumps/{jump['id']}"

    edited = api.ok(
        "PATCH", path, owner,
        {"jumped_on": "2026-10-09", "venue_id": venue["id"], "place_id": None,
         "notes": "another secret", "version": jump["version"]},
    )  # fmt: skip
    assert edited["jump"]["location"]["kind"] == "venue"
    assert edited["jump"]["version"] == jump["version"] + 1
    corrected = edited["events"][-1]
    assert corrected["kind"] == "corrected"
    assert corrected["detail"]["jumped_on"] == {
        "from": "2026-10-10",
        "to": "2026-10-09",
    }
    assert corrected["detail"]["notes"] == "changed"
    assert "secret" not in json.dumps(edited["events"])

    stale = api.call("PATCH", path, owner, {"jump_type": "angle", "version": 1})
    assert stale.status_code == 409 and stale.json() == {"detail": "edit_conflict"}
    stale_delete = api.call("DELETE", path, owner, version=1)
    assert stale_delete.status_code == 409

    # The place is free again once no jump uses it.
    assert api.call("DELETE", f"/places/{place['id']}", owner).status_code == 204


def test_owner_only_and_writes_need_a_confirmed_email(api: Api) -> None:
    owner = api.accounts.session()
    place = api.place(owner)
    jump = api.jump(owner, place_id=place["id"]).json()["jump"]
    path = f"/jumps/{jump['id']}"
    other = api.accounts.session()
    assert api.call("GET", path, other).status_code == 404
    assert api.call("PATCH", path, other, {"jump_type": "angle"}).status_code == 404
    assert api.call("DELETE", path, other).status_code == 404
    assert api.ok("GET", "/jumps", other)["recorded_total"] == 0
    # Someone else's private place is not usable either.
    assert api.jump(other, place_id=place["id"]).json() == {"detail": "place_unknown"}

    assert api.call("GET", "/jumps").status_code == 401
    unverified = api.accounts.session(verified=False)
    assert api.call("GET", "/jumps", unverified).status_code == 200
    assert api.jump(unverified, place_id=place["id"]).status_code == 403


def test_pages_newest_activity_first(api: Api) -> None:
    owner = api.accounts.session()
    place = api.place(owner)
    ids = [
        api.jump(owner, place_id=place["id"], jumped_on=day).json()["jump"]["id"]
        for day in ("2026-01-01", "2026-03-01", "2026-02-01")
    ]
    first = api.call("GET", "/jumps", owner, limit=2).json()
    assert [i["id"] for i in first["items"]] == [ids[1], ids[2]]
    assert first["recorded_total"] == 3
    rest = api.call("GET", "/jumps", owner, limit=2, cursor=first["next_cursor"])
    assert [i["id"] for i in rest.json()["items"]] == [ids[0]]
    assert rest.json()["next_cursor"] is None
    bad = api.call("GET", "/jumps", owner, cursor="nonsense")
    assert bad.status_code == 422


def test_in_order_reads_full_entries_oldest_first_within_dates(api: Api) -> None:
    owner = api.accounts.session()
    place = api.place(owner)
    gear = api.component(owner, "Sabre 170")
    made = {
        day: api.jump(
            owner,
            place_id=place["id"],
            jumped_on=day,
            freefall_seconds=seconds,
            notes=f"note {day}",
            component_ids=[gear["id"]],
        ).json()["jump"]["id"]  # fmt: skip
        for day, seconds in (
            ("2026-01-01", 40),
            ("2026-02-01", None),
            ("2026-03-01", 55),
            ("2026-04-01", 60),
        )  # fmt: skip
    }
    first = api.call(
        "GET", "/jumps/in-order", owner, from_on="2026-02-01", until_on="2026-04-01",
        limit=2,
    ).json()  # fmt: skip
    assert [i["id"] for i in first["items"]] == [
        made["2026-02-01"],
        made["2026-03-01"],
    ]
    item = first["items"][1]
    assert (item["notes"], item["freefall_seconds"]) == ("note 2026-03-01", 55)
    assert [c["label"] for c in item["components"]] == ["Sabre 170"]
    assert item["location"]["name"] == "Farm strip"
    # Entries before the range carry forward as a count and freefall time.
    assert first["brought_forward"] == {"jumps": 1, "freefall_seconds": 40}
    rest = api.call(
        "GET", "/jumps/in-order", owner, from_on="2026-02-01", until_on="2026-04-01",
        limit=2, cursor=first["next_cursor"],
    ).json()  # fmt: skip
    assert [i["id"] for i in rest["items"]] == [made["2026-04-01"]]
    assert rest["next_cursor"] is None

    everything = api.ok("GET", "/jumps/in-order", owner)
    assert [i["id"] for i in everything["items"]] == list(made.values())
    assert everything["brought_forward"] == {"jumps": 0, "freefall_seconds": 0}

    backwards = api.call(
        "GET", "/jumps/in-order", owner, from_on="2026-04-01", until_on="2026-01-01"
    )
    assert backwards.json() == {"detail": "date_range_invalid"}
    assert api.call("GET", "/jumps/in-order", owner, limit=201).status_code == 422
    # Owner-only: another person reads nothing, anonymous is refused.
    other = api.accounts.session()
    assert api.ok("GET", "/jumps/in-order", other)["items"] == []
    assert api.call("GET", "/jumps/in-order").status_code == 401


class _LateStore(SqlLogbookStore):
    """Misses the first receipt read, as a request racing a same-key retry would."""

    missed = False

    def receipt(self, actor: Actor, client_key: uuid.UUID) -> Any:
        found = super().receipt(actor, client_key)
        if not _LateStore.missed:
            _LateStore.missed = True
            return None
        return found


def test_a_lost_same_key_race_returns_the_winner(api: Api) -> None:
    owner = api.accounts.session()
    actor = _actor(api.accounts.service.current_viewer(secret=owner))
    place = api.place(owner)
    key = uuid.uuid4()
    fields = {
        "jumped_on": datetime(2026, 10, 1).date(),
        "place_id": uuid.UUID(place["id"]),
        "jump_type": "belly",
    }
    real = LogbookService(
        stores=sql_logbook_store_factory(engine), clock=lambda: NOW,
        directory=api.directory,
    )  # fmt: skip
    first, _ = real.create_jump(actor, key, fields)

    @contextmanager
    def late_stores() -> Iterator[SqlLogbookStore]:
        with Session(engine) as session:
            yield _LateStore(session)
            session.commit()

    _LateStore.missed = False
    late = LogbookService(
        stores=late_stores, clock=lambda: NOW, directory=api.directory
    )
    again, created = late.create_jump(actor, key, fields)
    assert (again.view.jump.id, created) == (first.view.jump.id, False)
    # Confirmed as distinct, it reaches the insert, loses on the key and still
    # returns the winner rather than a second jump.
    _LateStore.missed = False
    again, created = late.create_jump(actor, key, fields, confirm_distinct=True)
    assert (again.view.jump.id, created) == (first.view.jump.id, False)
    assert real.list_jumps(actor).recorded_total == 1


def _ids(page: dict[str, Any]) -> list[str]:
    return [i["id"] for i in page["items"]]


def test_filters_narrow_the_owners_own_jumps(api: Api) -> None:
    owner, other = api.accounts.session(), api.accounts.session()
    venue = api.venue()
    place = api.place(owner)

    def jump(secret: str, **fields: Any) -> str:
        sent = api.jump(secret, **fields)
        assert sent.status_code == 201, sent.text
        return str(sent.json()["jump"]["id"])

    a = jump(owner, venue_id=venue["id"], jumped_on="2026-01-05", jump_type="belly",
             jump_number=10, freefall_seconds=50, notes="Sunset 4-way")  # fmt: skip
    b = jump(owner, venue_id=venue["id"], jumped_on="2026-02-05", jump_type="freefly",
             jump_number=11, notes="100% fun")  # fmt: skip
    c = jump(owner, place_id=place["id"], jumped_on="2026-03-05", jump_type="belly",
             jump_number=12, freefall_seconds=40)  # fmt: skip
    d = jump(owner, place_id=place["id"], jumped_on="2026-04-05", jump_type="canopy")
    # Another jumper's matching jump never appears, whatever the filter.
    jump(other, venue_id=venue["id"], jumped_on="2026-01-05", jump_type="belly",
         jump_number=10, notes="Sunset 4-way")  # fmt: skip

    def search(**params: Any) -> dict[str, Any]:
        response = api.call("GET", "/jumps", owner, **params)
        assert response.status_code == 200, response.text
        return dict(response.json())

    everything = search()
    assert _ids(everything) == [d, c, b, a]
    assert everything["matched"] == {
        "jumps": 4, "freefall_seconds": 90, "freefall_recorded": 2,
        "first_on": "2026-01-05", "last_on": "2026-04-05",
    }  # fmt: skip
    assert _ids(search(jump_type="belly")) == [c, a]
    assert _ids(search(venue_id=venue["id"])) == [b, a]
    assert _ids(search(place_id=place["id"])) == [d, c]
    assert _ids(search(from_date="2026-02-01", to_date="2026-03-31")) == [c, b]
    assert _ids(search(number_from=11)) == [c, b]  # unnumbered jumps drop out
    assert _ids(search(number_from=10, number_to=10)) == [a]
    # Text: private notes (case-insensitive, wildcards literal) and place names.
    assert _ids(search(q="sunset")) == [a]
    assert _ids(search(q="100%")) == [b]
    assert _ids(search(q="%")) == [b]
    assert _ids(search(q="farm")) == [d, c]
    assert _ids(search(q=venue["name"][:6].lower())) == [b, a]
    # Combined filters all apply.
    combined = search(jump_type="belly", from_date="2026-02-01", q="farm")
    assert _ids(combined) == [c]
    assert combined["matched"] == {
        "jumps": 1, "freefall_seconds": 40, "freefall_recorded": 1,
        "first_on": "2026-03-05", "last_on": "2026-03-05",
    }  # fmt: skip
    assert combined["recorded_total"] == 4  # the whole logbook, unfiltered
    none = search(jump_type="wingsuit")
    assert none["items"] == [] and none["matched"] == {
        "jumps": 0, "freefall_seconds": None, "freefall_recorded": 0,
        "first_on": None, "last_on": None,
    }  # fmt: skip
    # Another person's place filters to nothing rather than to their jumps.
    assert search(place_id=api.place(other)["id"])["items"] == []


def test_filtered_pages_keep_their_order(api: Api) -> None:
    owner = api.accounts.session()
    place = api.place(owner)
    ids = [
        api.jump(owner, place_id=place["id"], jumped_on=f"2026-05-{day:02d}",
                 jump_type=kind).json()["jump"]["id"]
        for day, kind in ((1, "belly"), (2, "canopy"), (3, "belly"), (4, "belly"))
    ]  # fmt: skip
    expected = [ids[3], ids[2], ids[0]]
    first = api.call("GET", "/jumps", owner, limit=2, jump_type="belly").json()
    assert _ids(first) == expected[:2]
    rest = api.call(
        "GET", "/jumps", owner, limit=2, jump_type="belly", cursor=first["next_cursor"]
    ).json()
    assert _ids(rest) == expected[2:] and rest["next_cursor"] is None
    assert first["matched"]["jumps"] == rest["matched"]["jumps"] == 3


def test_a_merged_dropzone_filters_with_its_survivor(api: Api) -> None:
    owner = api.accounts.session()
    old, survivor = api.venue(), api.venue()
    before = api.jump(owner, venue_id=old["id"]).json()["jump"]["id"]
    api.ok(
        "POST", f"/directory/venues/{old['id']}/merge", api.reviewer,
        {"into": survivor["id"]},
    )  # fmt: skip
    after = api.jump(owner, venue_id=survivor["id"], jumped_on="2026-10-11")
    page = api.call("GET", "/jumps", owner, venue_id=survivor["id"]).json()
    assert _ids(page) == [after.json()["jump"]["id"], before]
    # The old name stays searchable: it is an alias of the survivor now.
    assert before in _ids(api.call("GET", "/jumps", owner, q=old["name"]).json())


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        ({"from_date": "2026-03-01", "to_date": "2026-02-01"}, "date_range_invalid"),
        ({"number_from": 20, "number_to": 10}, "number_range_invalid"),
        (
            {"venue_id": str(uuid.uuid4()), "place_id": str(uuid.uuid4())},
            "location_filter_invalid",
        ),
    ],
)
def test_filter_validation(api: Api, params: dict[str, Any], expected: str) -> None:
    owner = api.accounts.session()
    response = api.call("GET", "/jumps", owner, **params)
    assert (response.status_code, response.json()) == (422, {"detail": expected})
    for bad in ({"jump_type": "skysurf"}, {"number_from": 0}, {"q": "x" * 101}):
        assert api.call("GET", "/jumps", owner, **bad).status_code == 422
    assert api.call("GET", "/jumps", None, jump_type="belly").status_code == 401


def test_jumps_at_one_dropzone_count_only_the_readers_own(api: Api) -> None:
    """What a dropzone page shows a signed-in reader: their own count and last date."""
    owner, other, newcomer = (api.accounts.session() for _ in range(3))
    venue, elsewhere = api.venue(), api.venue()
    for day in ("2026-03-01", "2026-06-15"):
        assert api.jump(owner, venue_id=venue["id"], jumped_on=day).status_code == 201
    assert api.jump(owner, venue_id=elsewhere["id"], jumped_on="2026-07-01").status_code == 201  # fmt: skip
    assert api.jump(other, venue_id=venue["id"], jumped_on="2026-09-09").status_code == 201  # fmt: skip

    def here(secret: str | None) -> httpx2.Response:
        return api.call("GET", "/jumps", secret, venue_id=venue["id"], limit=1)

    mine = here(owner).json()["matched"]
    assert (mine["jumps"], mine["last_on"]) == (2, "2026-06-15")
    theirs = here(other).json()["matched"]
    assert (theirs["jumps"], theirs["last_on"]) == (1, "2026-09-09")
    none = here(newcomer).json()
    assert (none["matched"]["jumps"], none["matched"]["last_on"], none["items"]) == (
        0, None, [],
    )  # fmt: skip
    assert here(None).status_code == 401  # guests get nothing


def test_numbering_is_the_owners_own(api: Api) -> None:
    owner, other = api.accounts.session(), api.accounts.session()
    assert api.ok("GET", "/jumps/numbering", owner) == {
        "highest": None, "gaps": [], "gap_count": 0, "repeats": [], "repeat_count": 0,
    }  # fmt: skip
    place = api.place(owner)

    def jump(number: int | None, day: str) -> str:
        sent = api.jump(
            owner, place_id=place["id"], jumped_on=day, jump_number=number,
            confirm_distinct=True,
        )  # fmt: skip
        assert sent.status_code == 201, sent.text
        return str(sent.json()["jump"]["id"])

    j120 = jump(120, "2026-10-01")
    j125 = jump(125, "2026-10-02")
    first130 = jump(130, "2026-10-03")
    second130 = jump(130, "2026-10-04")
    jump(None, "2026-10-05")  # unnumbered jumps are ignored
    # Another jumper's higher number changes nothing here.
    api.jump(other, place_id=api.place(other)["id"], jump_number=999)

    found = api.ok("GET", "/jumps/numbering", owner)
    assert found["highest"] == 130
    assert [(g["first"], g["last"]) for g in found["gaps"]] == [(121, 124), (126, 129)]
    assert found["gaps"][0]["before"] == {
        "id": j120, "jumped_on": "2026-10-01", "jump_number": 120,
    }  # fmt: skip
    assert found["gaps"][0]["after"]["id"] == j125
    assert found["repeats"] == [
        {
            "jump_number": 130, "uses": 2,
            "jumps": [
                {"id": first130, "jumped_on": "2026-10-03", "jump_number": 130},
                {"id": second130, "jumped_on": "2026-10-04", "jump_number": 130},
            ],
        }
    ]  # fmt: skip
    assert api.ok("GET", "/jumps/numbering", other)["highest"] == 999
    assert api.call("GET", "/jumps/numbering").status_code == 401
