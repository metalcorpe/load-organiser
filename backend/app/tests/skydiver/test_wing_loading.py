"""Wing loading over HTTP against PostgreSQL: canopy sizes, exit weights, jumps."""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

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

    def ok(self, method: str, path: str, secret: str, body: Any = None, status: int = 200, **params: Any) -> Any:  # fmt: skip
        response = self.call(method, path, secret, body, **params)
        assert response.status_code == status, response.text
        return response.json() if response.content else None

    def refused(self, method: str, path: str, secret: str, body: Any) -> str:
        response = self.call(method, path, secret, body)
        assert response.status_code == 422, response.text
        return str(response.json()["detail"])

    def component(self, secret: str, kind: str = "main", **fields: Any) -> dict[str, Any]:  # fmt: skip
        body = {"client_key": str(uuid.uuid4()), "kind": kind, "label": f"{kind} {uuid.uuid4().hex[:4]}", **fields}  # fmt: skip
        return dict(self.ok("POST", "/gear/components", secret, body, 201)["component"])

    def jump(self, secret: str, on: str = "2026-10-01", **fields: Any) -> dict[str, Any]:  # fmt: skip
        place = self.ok("POST", "/places", secret, {"name": "Strip", "country": "PT"}, 201)  # fmt: skip
        body = {
            "client_key": str(uuid.uuid4()), "jumped_on": on, "jump_type": "belly",
            "place_id": place["id"], "confirm_distinct": True, **fields,
        }  # fmt: skip
        return dict(self.ok("POST", "/jumps", secret, body, 201)["jump"])


@pytest.fixture(scope="module")
def api() -> Iterator[Api]:
    accounts = Accounts.create()
    directory = DirectoryService(stores=sql_directory_store_factory(engine), clock=lambda: NOW)  # fmt: skip
    gear = GearService(stores=sql_gear_store_factory(engine), clock=lambda: NOW)
    logbook = LogbookService(stores=sql_logbook_store_factory(engine), clock=lambda: NOW, directory=directory)  # fmt: skip
    history = HistoryService(stores=sql_history_store_factory(engine), clock=lambda: NOW, directory=directory)  # fmt: skip
    access = AccessDependencies(lambda: accounts.service)
    app = FastAPI()
    app.include_router(create_gear_router(service=lambda: gear, access=access))
    app.include_router(create_logbook_router(service=lambda: logbook, access=access))
    app.include_router(create_history_router(service=lambda: history, access=access))
    app.include_router(
        create_directory_router(service=lambda: directory, access=access)
    )
    with TestClient(app) as client:
        yield Api(client, accounts)


def test_a_canopy_size_belongs_to_mains_and_reserves(api: Api) -> None:
    owner = api.accounts.session()
    main = api.component(owner, canopy_size_sqft=170)
    assert main["canopy_size_sqft"] == 170
    assert api.component(owner, "reserve", canopy_size_sqft=150)["canopy_size_sqft"] == 150  # fmt: skip
    assert api.component(owner, "container")["canopy_size_sqft"] is None
    body = {"client_key": str(uuid.uuid4()), "kind": "aad", "label": "AAD", "canopy_size_sqft": 170}  # fmt: skip
    assert api.refused("POST", "/gear/components", owner, body) == "canopy_size_not_a_canopy"  # fmt: skip
    # Changing the type away from a canopy needs the size cleared too.
    path = f"/gear/components/{main['id']}"
    change = {"kind": "container", "version": main["version"]}
    assert api.refused("PATCH", path, owner, change) == "canopy_size_not_a_canopy"
    edited = api.ok("PATCH", path, owner, change | {"canopy_size_sqft": None})
    assert edited["component"]["canopy_size_sqft"] is None
    # Out of range: refused by the request schema.
    too_big = {"client_key": str(uuid.uuid4()), "kind": "main", "label": "x", "canopy_size_sqft": 401}  # fmt: skip
    assert api.call("POST", "/gear/components", owner, too_big).status_code == 422


def test_the_usual_exit_weight_is_private_and_kept_in_its_unit(api: Api) -> None:
    owner, other = api.accounts.session(), api.accounts.session()
    assert api.ok("GET", "/me/exit-weight", owner) == {"exit_weight": None, "unit": "kg"}  # fmt: skip
    saved = api.ok("PUT", "/me/exit-weight", owner, {"value": 180, "unit": "lb"})
    assert saved == {"exit_weight": {"grams": 81_647, "value": 180.0, "unit": "lb"}, "unit": "lb"}  # fmt: skip
    assert api.ok("GET", "/me/exit-weight", owner) == saved
    kg = api.ok("PUT", "/me/exit-weight", owner, {"value": 81.6, "unit": "kg"})
    assert kg["exit_weight"] == {"grams": 81_600, "value": 81.6, "unit": "kg"}
    assert api.ok("GET", "/me/exit-weight", other)["exit_weight"] is None
    assert api.refused("PUT", "/me/exit-weight", owner, {"value": 29.9, "unit": "kg"}) == "exit_weight_invalid"  # fmt: skip
    assert api.refused("PUT", "/me/exit-weight", owner, {"value": 560, "unit": "lb"}) == "exit_weight_invalid"  # fmt: skip
    # Writes need a confirmed email; reads and writes need a session.
    unverified = api.accounts.session(verified=False)
    assert api.call("PUT", "/me/exit-weight", unverified, {"value": 80, "unit": "kg"}).status_code == 403  # fmt: skip
    assert api.call("GET", "/me/exit-weight").status_code == 401
    cleared = api.ok("PUT", "/me/exit-weight", owner, {"value": None, "unit": "kg"})
    assert cleared["exit_weight"] is None


def test_each_jump_has_a_wing_loading_or_says_what_is_missing(api: Api) -> None:
    owner = api.accounts.session()
    main = api.component(owner, canopy_size_sqft=170)
    unsized = api.component(owner)
    container = api.component(owner, "container")
    no_weight = api.jump(owner, component_ids=[main["id"], container["id"]])
    assert no_weight["wing_loading"] == {
        "value": None, "exit_weight_grams": None, "exit_weight_from_jump": False,
        "unit": "kg", "canopy_size_sqft": 170, "missing": ["exit_weight"],
    }  # fmt: skip
    api.ok("PUT", "/me/exit-weight", owner, {"value": 81.6, "unit": "kg"})
    found = api.ok("GET", f"/jumps/{no_weight['id']}", owner)["jump"]["wing_loading"]
    assert (found["value"], found["exit_weight_grams"], found["missing"]) == (1.06, 81_600, [])  # fmt: skip
    # The jump's own exit weight wins over the usual one.
    own = api.jump(owner, component_ids=[main["id"]], exit_weight_grams=90_000)
    assert own["exit_weight_grams"] == 90_000
    assert (own["wing_loading"]["value"], own["wing_loading"]["exit_weight_from_jump"]) == (1.17, True)  # fmt: skip
    assert api.jump(owner)["wing_loading"]["missing"] == ["main_canopy"]
    assert api.jump(owner, component_ids=[unsized["id"]])["wing_loading"]["missing"] == ["canopy_size"]  # fmt: skip
    both = api.jump(owner, component_ids=[main["id"], unsized["id"]])
    assert both["wing_loading"]["missing"] == ["several_mains"]
    # Logbook rows carry it too; a weight out of range is refused.
    rows = api.ok("GET", "/jumps", owner)["items"]
    assert sorted(r["wing_loading"]["value"] or 0 for r in rows) == [
        0,
        0,
        0,
        1.06,
        1.17,
    ]
    bad = {"client_key": str(uuid.uuid4()), "jumped_on": "2026-10-01", "jump_type": "belly", "place_id": api.ok("POST", "/places", owner, {"name": "S", "country": "PT"}, 201)["id"], "exit_weight_grams": 29_000}  # fmt: skip
    assert api.refused("POST", "/jumps", owner, bad) == "exit_weight_invalid"
    # A correction keeps the earlier weight in the jump's own history.
    edited = api.ok("PATCH", f"/jumps/{own['id']}", owner, {"exit_weight_grams": None, "version": own["version"]})  # fmt: skip
    assert edited["jump"]["wing_loading"]["value"] == 1.06
    assert edited["events"][-1]["detail"]["exit_weight_grams"] == {"from": 90_000, "to": None}  # fmt: skip


def test_the_highest_loading_so_far_leaves_out_the_jump_being_edited(api: Api) -> None:
    owner = api.accounts.session()
    empty = api.ok("GET", "/jumps/wing-loading", owner)
    assert empty == {"exit_weight": None, "unit": "kg", "highest": None}
    api.ok("PUT", "/me/exit-weight", owner, {"value": 180, "unit": "lb"})
    big = api.component(owner, canopy_size_sqft=190)
    small = api.component(owner, canopy_size_sqft=150)
    api.jump(owner, "2026-09-01", component_ids=[big["id"]])  # 0.95
    latest = api.jump(owner, "2026-10-01", component_ids=[small["id"]])  # 1.20
    api.jump(owner, "2026-10-02")  # unknown: no main recorded
    context = api.ok("GET", "/jumps/wing-loading", owner)
    assert context == {
        "exit_weight": {"grams": 81_647, "value": 180.0, "unit": "lb"},
        "unit": "lb", "highest": 1.2,
    }  # fmt: skip
    without = api.ok("GET", "/jumps/wing-loading", owner, exclude=latest["id"])
    assert without["highest"] == 0.95
    # Another person's jumps and weight never count.
    other = api.accounts.session()
    assert api.ok("GET", "/jumps/wing-loading", other)["highest"] is None
    assert api.call("GET", "/jumps/wing-loading").status_code == 401


def test_history_shows_the_highest_loading_by_month(api: Api) -> None:
    owner = api.accounts.session()
    main = api.component(owner, canopy_size_sqft=170)
    small = api.component(owner, canopy_size_sqft=150)
    history = api.ok("GET", "/history", owner)
    assert history["wing_loading_months"] == [] and history["exit_weight"] is None
    assert history["wing_loading"] == {"lowest": None, "highest": None, "known": 0, "unknown": 0, "missing": []}  # fmt: skip
    api.jump(owner, "2026-09-03", component_ids=[main["id"]])
    api.jump(owner, "2026-09-04")
    missing = api.ok("GET", "/history", owner)["wing_loading"]["missing"]
    assert missing == [{"missing": "exit_weight", "jumps": 2}, {"missing": "main_canopy", "jumps": 1}]  # fmt: skip
    api.ok("PUT", "/me/exit-weight", owner, {"value": 81.6, "unit": "kg"})
    api.jump(owner, "2026-09-20", component_ids=[small["id"]])
    api.jump(owner, "2026-10-05", component_ids=[main["id"]])
    history = api.ok("GET", "/history", owner)
    assert history["wing_loading_months"] == [
        {"month": "2026-09", "highest": 1.2, "jumps": 2},
        {"month": "2026-10", "highest": 1.06, "jumps": 1},
    ]
    r = history["wing_loading"]
    assert (r["lowest"], r["highest"], r["known"], r["unknown"]) == (1.06, 1.2, 3, 1)
    assert history["exit_weight"] == {"grams": 81_600, "value": 81.6, "unit": "kg"}
