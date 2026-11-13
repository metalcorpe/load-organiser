"""Statistics over HTTP against PostgreSQL: one owner-scoped endpoint, bounded work."""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import event

from app.core.db import engine
from app.skydiver.access.http import AccessDependencies
from app.skydiver.directory.api import create_router as create_directory_router
from app.skydiver.directory.service import DirectoryService
from app.skydiver.directory.store import sql_directory_store_factory
from app.skydiver.gear.api import create_router as create_gear_router
from app.skydiver.gear.service import GearService
from app.skydiver.gear.store import sql_gear_store_factory
from app.skydiver.history.api import create_router as create_history_router
from app.skydiver.history.service import HistoryService
from app.skydiver.history.store import sql_history_store_factory
from app.skydiver.logbook.api import create_router as create_logbook_router
from app.skydiver.logbook.service import LogbookService
from app.skydiver.logbook.store import sql_logbook_store_factory
from app.tests.skydiver.support import Accounts

NOW = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)
SOURCE = {"source_url": "https://example.org/dz", "checked_on": "2026-11-01"}


class Api:
    def __init__(self, client: TestClient, accounts: Accounts) -> None:
        self.client = client
        self.accounts = accounts
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

    def ok(self, method: str, path: str, secret: str, body: Any = None, status: int = 200, **params: Any) -> Any:  # fmt: skip
        response = self.call(method, path, secret, body, **params)
        assert response.status_code == status, response.text
        return response.json() if response.content else None

    def venue(self, name: str) -> str:
        body = {"name": name, "country": "ES", **SOURCE}
        venue = self.ok("POST", "/directory/venues", self.reviewer, body, 201)
        self.ok(
            "POST", f"/directory/venues/{venue['id']}/status", self.reviewer,
            {"status": "listed"},
        )  # fmt: skip
        return str(venue["id"])

    def place(self, secret: str, name: str = "Farm strip") -> str:
        body = {"name": name, "country": "PT"}
        return str(self.ok("POST", "/places", secret, body, 201)["id"])

    def jump(self, secret: str, on: str, **fields: Any) -> None:
        body = {
            "client_key": str(uuid.uuid4()), "jumped_on": on, "jump_type": "belly",
            "confirm_distinct": True, **fields,
        }  # fmt: skip
        if "venue_id" not in fields and "place_id" not in fields:
            body["place_id"] = self.place(secret)
        self.ok("POST", "/jumps", secret, body, 201)

    def stats(self, secret: str, **params: Any) -> dict[str, Any]:
        return dict(self.ok("GET", "/history/stats", secret, **params))


@pytest.fixture(scope="module")
def api() -> Iterator[Api]:
    accounts = Accounts.create()
    directory = DirectoryService(stores=sql_directory_store_factory(engine), clock=lambda: NOW)  # fmt: skip
    gear = GearService(stores=sql_gear_store_factory(engine), clock=lambda: NOW)
    logbook = LogbookService(stores=sql_logbook_store_factory(engine), clock=lambda: NOW, directory=directory)  # fmt: skip
    history = HistoryService(stores=sql_history_store_factory(engine), clock=lambda: NOW, directory=directory)  # fmt: skip
    access = AccessDependencies(lambda: accounts.service)
    app = FastAPI()
    app.include_router(create_history_router(service=lambda: history, access=access))
    app.include_router(create_logbook_router(service=lambda: logbook, access=access))
    app.include_router(create_gear_router(service=lambda: gear, access=access))
    app.include_router(create_directory_router(service=lambda: directory, access=access))  # fmt: skip
    with TestClient(app) as client:
        yield Api(client, accounts)


def test_an_empty_logbook_has_empty_statistics(api: Api) -> None:
    s = api.stats(api.accounts.session())
    assert s["total"] == {"recorded": 0, "reported": None, "prior_jumps": None}
    assert (s["years"], s["per_year"], s["by_type"], s["freefall"]) == ([], [], [], [])
    assert len(s["per_month"]) == 24 and s["per_month"][-1] == {"month": "2026-11", "jumps": 0}  # fmt: skip
    assert s["by_place"] == {"items": [], "others": 0, "other_places": 0}
    assert s["by_aircraft"] == {"items": [], "others": 0, "other_aircraft": 0, "not_recorded": 0}  # fmt: skip
    assert (s["altitudes"], s["altitude_not_recorded"]) == ([], 0)
    assert s["wing_loading"] == {"lowest": None, "highest": None, "known": 0, "unknown": 0, "missing": []}  # fmt: skip


def test_counts_types_years_and_the_prior_count_only_in_the_total(api: Api) -> None:
    owner = api.accounts.session()
    place = api.place(owner)
    for on, kind in (("2025-06-01", "belly"), ("2026-09-01", "freefly"), ("2026-09-02", "freefly"), ("2026-10-01", "belly")):  # fmt: skip
        api.jump(owner, on, jump_type=kind, place_id=place)
    s = api.stats(owner)
    assert s["total"] == {"recorded": 4, "reported": None, "prior_jumps": None}
    assert s["years"] == [2026, 2025]
    assert s["per_year"] == [{"year": 2025, "jumps": 1}, {"year": 2026, "jumps": 3}]
    assert s["by_type"] == [{"jump_type": "belly", "jumps": 2}, {"jump_type": "freefly", "jumps": 2}]  # fmt: skip
    months = {m["month"]: m["jumps"] for m in s["per_month"]}
    assert (months["2026-09"], months["2026-10"], months["2025-06"]) == (2, 1, 1)
    # The declared prior jump count adds to the total only, and only while it holds.
    api.ok("PUT", "/history/baseline", owner, {"prior_jumps": 100, "before_on": "2025-01-01"})  # fmt: skip
    total = api.stats(owner)["total"]
    assert total == {"recorded": 4, "reported": 104, "prior_jumps": 100}
    assert api.stats(owner)["by_type"][0]["jumps"] == 2  # never in the breakdowns
    # A year narrows everything but the years; the prior count has no year.
    y = api.stats(owner, year=2026)
    assert y["total"] == {"recorded": 3, "reported": None, "prior_jumps": None}
    assert y["per_year"] == s["per_year"] and y["year"] == 2026
    assert [m["month"] for m in y["per_month"]] == [
        f"2026-{m:02d}" for m in range(1, 13)
    ]
    assert y["by_type"] == [{"jump_type": "freefly", "jumps": 2}, {"jump_type": "belly", "jumps": 1}]  # fmt: skip
    # A year with no jumps is empty, not an error; one in the future is refused.
    assert api.stats(owner, year=2020)["total"]["recorded"] == 0
    refused = api.call("GET", "/history/stats", owner, year=2027)
    assert refused.status_code == 422 and refused.json() == {"detail": "year_invalid"}


def test_the_top_ten_places_and_aircraft_with_the_others(api: Api) -> None:
    owner = api.accounts.session()
    venue = api.venue(f"St{uuid.uuid4().hex[:8]} DZ")
    for _ in range(3):
        api.jump(owner, "2026-10-01", venue_id=venue, aircraft="Caravan SX-1")
    api.jump(owner, "2026-10-01", venue_id=venue, aircraft="  caravan   sx-1 ")
    for i in range(11):
        api.jump(owner, "2026-10-02", place_id=api.place(owner, f"Strip {i:02d}"), aircraft=f"Plane {i:02d}")  # fmt: skip
    api.jump(owner, "2026-10-03", venue_id=venue)
    s = api.stats(owner)
    places = s["by_place"]
    assert len(places["items"]) == 10
    assert places["items"][0]["location"]["kind"] == "venue"
    assert places["items"][0]["jumps"] == 5
    # Ties by name: Strip 00..Strip 08 named, Strip 09 and Strip 10 are the others.
    assert [p["location"]["name"] for p in places["items"][1:]] == [f"Strip {i:02d}" for i in range(9)]  # fmt: skip
    assert (places["others"], places["other_places"]) == (2, 2)
    aircraft = s["by_aircraft"]
    # The same aircraft however spaced or capitalised, under its most used spelling.
    assert aircraft["items"][0] == {"aircraft": "Caravan SX-1", "jumps": 4}
    assert (aircraft["others"], aircraft["other_aircraft"], aircraft["not_recorded"]) == (2, 2, 1)  # fmt: skip


def test_freefall_altitudes_and_wing_loading_count_what_was_recorded(api: Api) -> None:
    owner = api.accounts.session()
    api.jump(owner, "2025-05-01", freefall_seconds=60, exit_altitude=4000, altitude_unit="m")  # fmt: skip
    api.jump(owner, "2026-05-01", freefall_seconds=45, exit_altitude=13000, altitude_unit="ft")  # fmt: skip
    api.jump(owner, "2026-05-02", exit_altitude=12001, altitude_unit="ft")
    api.ok("PUT", "/me/exit-weight", owner, {"value": 81.6, "unit": "kg"})
    main = api.ok("POST", "/gear/components", owner, {"client_key": str(uuid.uuid4()), "kind": "main", "label": "Main", "canopy_size_sqft": 150}, 201)["component"]  # fmt: skip
    api.jump(owner, "2026-06-01", component_ids=[main["id"]])
    s = api.stats(owner)
    assert s["freefall"] == [
        {"year": 2025, "seconds": 60, "with_freefall": 1, "without_freefall": 0},
        {"year": 2026, "seconds": 45, "with_freefall": 1, "without_freefall": 2},
    ]
    # Feet and metres are summarised apart, never converted.
    assert s["altitudes"] == [
        {"unit": "ft", "jumps": 2, "average": 12501, "highest": 13000},
        {"unit": "m", "jumps": 1, "average": 4000, "highest": 4000},
    ]
    assert s["altitude_not_recorded"] == 1
    assert s["wing_loading"] == {
        "lowest": 1.2, "highest": 1.2, "known": 1, "unknown": 3,
        "missing": [{"missing": "main_canopy", "jumps": 3}],
    }  # fmt: skip
    assert api.stats(owner, year=2025)["altitudes"] == [{"unit": "m", "jumps": 1, "average": 4000, "highest": 4000}]  # fmt: skip


def test_statistics_are_the_owners_alone(api: Api) -> None:
    owner, other = api.accounts.session(), api.accounts.session()
    api.jump(owner, "2026-10-01", aircraft="Owner's plane")
    assert api.stats(other)["total"]["recorded"] == 0
    assert "Owner" not in api.call("GET", "/history/stats", other).text
    assert api.call("GET", "/history/stats").status_code == 401


def test_the_work_does_not_grow_with_the_logbook(api: Api) -> None:
    """The same number of queries for one jump as for thirty at thirty places."""

    def queries(secret: str) -> int:
        seen: list[str] = []

        def count(*args: Any) -> None:
            seen.append(str(args[2]))

        event.listen(engine, "before_cursor_execute", count)
        try:
            api.stats(secret)
        finally:
            event.remove(engine, "before_cursor_execute", count)
        return len(seen)

    small, large = api.accounts.session(), api.accounts.session()
    api.jump(small, "2026-10-01")
    for i in range(30):
        api.jump(large, f"2026-{(i % 9) + 1:02d}-01", aircraft=f"Plane {i}")
    assert queries(small) == queries(large)
