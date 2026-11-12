"""Gear limits by jump count over HTTP against PostgreSQL."""

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
from app.skydiver.directory.service import DirectoryService
from app.skydiver.directory.store import sql_directory_store_factory
from app.skydiver.gear.api import create_router as create_gear_router
from app.skydiver.gear.service import GearService
from app.skydiver.gear.store import sql_gear_store_factory
from app.skydiver.logbook.api import create_router as create_logbook_router
from app.skydiver.logbook.service import LogbookService
from app.skydiver.logbook.store import sql_logbook_store_factory
from app.tests.skydiver.support import Accounts

NOW = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)


class Api:
    def __init__(self, client: TestClient, accounts: Accounts) -> None:
        self.client = client
        self.accounts = accounts

    def call(self, method: str, path: str, secret: str | None = None, body: Any = None) -> httpx2.Response:  # fmt: skip
        headers = {"authorization": f"Bearer {secret}"} if secret else {}
        return self.client.request(method, f"/api/skydiver/v1{path}", json=body, headers=headers)  # fmt: skip

    def ok(self, method: str, path: str, secret: str, body: Any = None, status: int = 200) -> Any:  # fmt: skip
        response = self.call(method, path, secret, body)
        assert response.status_code == status, response.text
        return response.json() if response.content else None

    def component(self, secret: str, label: str, **fields: Any) -> dict[str, Any]:
        body = {
            "client_key": str(uuid.uuid4()),
            "kind": "main",
            "label": label,
            **fields,
        }
        return dict(self.ok("POST", "/gear/components", secret, body, 201)["component"])

    def jumps(self, secret: str, component: str, days: list[str]) -> None:
        place = self.ok(
            "POST", "/places", secret, {"name": "Strip", "country": "PT"}, 201
        )
        for day in days:
            self.ok(
                "POST", "/jumps", secret,
                {"client_key": str(uuid.uuid4()), "jumped_on": day, "jump_type": "belly",
                 "place_id": place["id"], "component_ids": [component],
                 "confirm_distinct": True},
                201,
            )  # fmt: skip

    def service(self, secret: str, component: str, kind: str, done_on: str) -> None:
        body = {"client_key": str(uuid.uuid4()), "kind": kind, "done_on": done_on}
        self.ok("POST", f"/gear/components/{component}/service", secret, body, 201)

    def limits(self, secret: str) -> list[dict[str, Any]]:
        due = self.ok("GET", "/gear/due", secret)
        return [d for d in due if d["kind"] == "jump_limit"]


@pytest.fixture(scope="module")
def api() -> Iterator[Api]:
    from app.skydiver.directory.api import create_router as create_directory_router

    accounts = Accounts.create()
    directory = DirectoryService(stores=sql_directory_store_factory(engine), clock=lambda: NOW)  # fmt: skip
    gear = GearService(stores=sql_gear_store_factory(engine), clock=lambda: NOW)
    logbook = LogbookService(stores=sql_logbook_store_factory(engine), clock=lambda: NOW, directory=directory)  # fmt: skip
    access = AccessDependencies(lambda: accounts.service)
    app = FastAPI()
    app.include_router(create_gear_router(service=lambda: gear, access=access))
    app.include_router(create_logbook_router(service=lambda: logbook, access=access))
    app.include_router(create_directory_router(service=lambda: directory, access=access))  # fmt: skip
    with TestClient(app) as client:
        yield Api(client, accounts)


def test_a_limit_counts_jumps_since_the_latest_matching_service(api: Api) -> None:
    owner = api.accounts.session()
    main = api.component(
        owner, "Main canopy", jump_limit=10, jump_limit_label="Reline",
        jump_limit_service_kind="maintenance",
    )  # fmt: skip
    assert (main["jump_limit"], main["jump_limit_label"], main["jump_limit_service_kind"]) == (10, "Reline", "maintenance")  # fmt: skip
    days = [f"2026-10-{d:02d}" for d in range(1, 10)]
    api.jumps(owner, main["id"], days)
    # Nine jumps and no service yet: every linked jump counts, one is left.
    (item,) = api.limits(owner)
    assert item == {
        "component": {"id": main["id"], "kind": "main", "label": "Main canopy"},
        "kind": "jump_limit", "service_kind": "maintenance", "due_on": None,
        "basis": "entered", "interval_days": None, "interval_source": None,
        "status": "soon", "label": "Reline", "jump_limit": 10, "jumps_used": 9,
        "jumps_left": 1, "counted_since": None,
    }  # fmt: skip
    # Another kind of service does not restart the count.
    api.service(owner, main["id"], "inspection", "2026-10-05")
    assert api.limits(owner)[0]["jumps_used"] == 9
    # The matching kind does: only jumps after its day count.
    api.service(owner, main["id"], "maintenance", "2026-10-05")
    (item,) = api.limits(owner)
    assert (item["jumps_used"], item["status"], item["counted_since"]) == (4, "later", "2026-10-05")  # fmt: skip


def test_over_the_limit_is_overdue_and_listed_first(api: Api) -> None:
    owner = api.accounts.session()
    worn = api.component(owner, "Old main", jump_limit=2, jump_limit_label="Replace")
    fresh = api.component(owner, "New main", jump_limit=500, jump_limit_label="Reline")
    api.jumps(owner, worn["id"], ["2026-10-01", "2026-10-02", "2026-10-03"])
    api.jumps(owner, fresh["id"], ["2026-10-04"])
    first, second = api.limits(owner)
    assert (first["component"]["id"], first["status"], first["jumps_left"]) == (worn["id"], "overdue", -1)  # fmt: skip
    assert (second["component"]["id"], second["status"], second["jumps_left"]) == (fresh["id"], "later", 499)  # fmt: skip
    # The default restarting service is maintenance.
    assert first["service_kind"] == "maintenance"


def test_limits_are_empty_by_default_owner_scoped_and_can_be_cleared(api: Api) -> None:
    owner, other = api.accounts.session(), api.accounts.session()
    plain = api.component(owner, "Plain main")
    assert plain["jump_limit"] is None and api.limits(owner) == []
    limited = api.component(owner, "Limited", jump_limit=10, jump_limit_label="Reline")
    api.jumps(owner, limited["id"], ["2026-10-01"])
    assert len(api.limits(owner)) == 1
    assert api.limits(other) == []
    refused = api.call(
        "PATCH", f"/gear/components/{limited['id']}", owner,
        {"jump_limit_label": "Reline", "jump_limit": None, "version": limited["version"]},
    )  # fmt: skip
    assert (refused.status_code, refused.json()) == (422, {"detail": "jump_limit_required"})  # fmt: skip
    cleared = api.ok(
        "PATCH", f"/gear/components/{limited['id']}", owner,
        {"jump_limit": None, "jump_limit_label": None, "version": limited["version"]},
    )["component"]  # fmt: skip
    assert (cleared["jump_limit"], cleared["jump_limit_label"], cleared["jump_limit_service_kind"]) == (None, None, None)  # fmt: skip
    assert api.limits(owner) == []
    # An archived component's limit is not listed.
    again = api.ok(
        "PATCH", f"/gear/components/{limited['id']}", owner,
        {"jump_limit": 1, "jump_limit_label": "Reline", "version": cleared["version"]},
    )["component"]  # fmt: skip
    assert api.limits(owner)[0]["status"] == "soon"
    api.ok("POST", f"/gear/components/{limited['id']}/archive", owner, {"archived": True, "version": again["version"]})  # fmt: skip
    assert api.limits(owner) == []
