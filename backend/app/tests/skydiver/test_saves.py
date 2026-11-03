"""#150 private saves and visit plans over HTTP against the real PostgreSQL store."""

import json
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
from app.skydiver.opportunities.api import create_router as create_opportunity_router
from app.skydiver.opportunities.service import OpportunityService
from app.skydiver.opportunities.store import sql_listing_store_factory
from app.skydiver.saves import service as saves_service
from app.skydiver.saves.api import create_router
from app.skydiver.saves.service import SavesService
from app.skydiver.saves.store import sql_saves_store_factory
from app.tests.skydiver.support import Accounts

NOW = datetime(2026, 11, 3, 12, 0, tzinfo=UTC)
SOURCE = {"source_url": "https://example.org/events", "checked_on": "2026-11-01"}


class Api:
    def __init__(self, client: TestClient, accounts: Accounts) -> None:
        self.client = client
        self.accounts = accounts
        self.reviewer = accounts.session(reviewer=True)

    def call(
        self, method: str, path: str, secret: str | None = None, body: Any = None
    ) -> httpx2.Response:
        headers = {"authorization": f"Bearer {secret}"} if secret else {}
        return self.client.request(
            method, f"/api/skydiver/v1{path}", json=body, headers=headers
        )

    def ok(
        self, method: str, path: str, secret: str, body: Any = None, status: int = 200
    ) -> Any:
        response = self.call(method, path, secret, body)
        assert response.status_code == status, response.text
        return response.json() if response.content else None

    def listing(self, title: str, **extra: Any) -> dict[str, Any]:
        provider = self.ok(
            "POST", "/directory/providers", self.reviewer,
            {"name": f"{title} Org", "kind": "organization", **SOURCE, "publish": True},
            201,
        )  # fmt: skip
        body = {
            "title": title, "category": "boogie", "provider_id": provider["id"],
            "country": "ES", "location_note": "Airfield", "starts_on": "2026-12-04",
            "ends_on": "2026-12-08", "time_zone": "Europe/Madrid",
            "registration_url": "https://example.org/register", **SOURCE, **extra,
        }  # fmt: skip
        item = self.ok("POST", "/directory/opportunities", self.reviewer, body, 201)
        for status in ("review", "published"):
            self.status(item["id"], status)
        return dict(item)

    def status(self, opportunity_id: str, status: str) -> None:
        self.ok(
            "POST", f"/directory/opportunities/{opportunity_id}/status", self.reviewer,
            {"status": status},
        )  # fmt: skip


@pytest.fixture(scope="module")
def api() -> Iterator[Api]:
    accounts = Accounts.create()
    directory = DirectoryService(
        stores=sql_directory_store_factory(engine), clock=lambda: NOW
    )
    opportunities = OpportunityService(
        stores=sql_listing_store_factory(engine), clock=lambda: NOW
    )
    saves = SavesService(
        stores=sql_saves_store_factory(engine),
        clock=lambda: NOW,
        opportunities=opportunities,
        directory=directory,
    )
    access = AccessDependencies(lambda: accounts.service)
    app = FastAPI()
    app.include_router(create_router(service=lambda: saves, access=access))
    app.include_router(
        create_opportunity_router(service=lambda: opportunities, access=access)
    )
    app.include_router(
        create_directory_router(service=lambda: directory, access=access)
    )
    with TestClient(app) as client:
        yield Api(client, accounts)


def name() -> str:
    return "Zs" + uuid.uuid4().hex[:10]


def test_saving_needs_an_account_and_a_confirmed_email(api: Api) -> None:
    item = api.listing(name())
    path = f"/saved/{item['id']}"
    assert api.call("PUT", path).status_code == 401
    assert api.call("GET", "/saved").status_code == 401
    unverified = api.accounts.session(verified=False)
    denied = api.call("PUT", path, unverified)
    assert denied.status_code == 403 and denied.json() == {"detail": "email_unverified"}
    assert api.call("GET", "/saved", unverified).json() == []


def test_save_is_idempotent_private_and_reversible(api: Api) -> None:
    title = name()
    item = api.listing(title)
    owner, other = api.accounts.session(), api.accounts.session()
    path = f"/saved/{item['id']}"

    first = api.call("PUT", path, owner)
    assert first.status_code == 201 and first.headers["cache-control"] == "no-store"
    again = api.call("PUT", path, owner)
    assert again.status_code == 200 and again.json() == first.json()
    saved = api.ok("GET", "/saved", owner)
    assert [s["opportunity_id"] for s in saved] == [item["id"]]
    assert saved[0]["opportunity"]["title"] == title
    assert api.ok("GET", path, owner)["opportunity_id"] == item["id"]

    # Nobody else sees it, and the public listing does not count or reveal saves.
    assert api.call("GET", path, other).status_code == 404
    assert api.ok("GET", "/saved", other) == []
    public = api.call("GET", f"/opportunities/{item['id']}").json()
    assert "saved" not in json.dumps(public)

    assert api.call("DELETE", path, owner).status_code == 204
    assert api.call("DELETE", path, owner).status_code == 204  # idempotent
    assert api.ok("GET", "/saved", owner) == []


def test_only_public_listings_can_be_saved(api: Api) -> None:
    owner = api.accounts.session()
    assert api.call("PUT", f"/saved/{uuid.uuid4()}", owner).status_code == 404
    provider = api.ok(
        "POST", "/directory/providers", api.reviewer,
        {"name": name(), "kind": "person", **SOURCE, "publish": True}, 201,
    )  # fmt: skip
    draft = api.ok(
        "POST", "/directory/opportunities", api.reviewer,
        {"title": name(), "category": "camp", "provider_id": provider["id"],
         "country": "ES"}, 201,
    )  # fmt: skip
    assert api.call("PUT", f"/saved/{draft['id']}", owner).json() == {
        "detail": "not_found"
    }


def test_withdrawn_listing_stays_in_saves_without_its_details(api: Api) -> None:
    title = name()
    item = api.listing(title)
    owner = api.accounts.session()
    api.ok("PUT", f"/saved/{item['id']}", owner, status=201)
    api.status(item["id"], "cancelled")
    cancelled = api.ok("GET", "/saved", owner)[0]
    assert cancelled["opportunity"]["status"] == "cancelled"
    api.status(item["id"], "archived")
    withdrawn = api.ok("GET", "/saved", owner)[0]
    assert withdrawn["opportunity"] is None
    assert withdrawn["title"] == title


def test_saved_duplicate_resolves_to_the_kept_listing(api: Api) -> None:
    keep, dupe = api.listing(name()), api.listing(name())
    owner = api.accounts.session()
    api.ok("PUT", f"/saved/{dupe['id']}", owner, status=201)
    api.ok(
        "POST", f"/directory/opportunities/{dupe['id']}/duplicate", api.reviewer,
        {"of": keep["id"]},
    )  # fmt: skip
    saved = api.ok("GET", "/saved", owner)[0]
    assert saved["opportunity_id"] == dupe["id"]
    assert saved["opportunity"]["id"] == keep["id"]
    # Saving the duplicate's ID now stores the kept listing.
    other = api.accounts.session()
    assert (
        api.ok("PUT", f"/saved/{dupe['id']}", other, status=201)["opportunity_id"]
        == keep["id"]
    )


def test_saved_limit(api: Api, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(saves_service, "MAX_SAVED", 1)
    owner = api.accounts.session()
    first, second = api.listing(name()), api.listing(name())
    api.ok("PUT", f"/saved/{first['id']}", owner, status=201)
    over = api.call("PUT", f"/saved/{second['id']}", owner)
    assert over.status_code == 409 and over.json() == {"detail": "saved_limit_reached"}
    # Re-saving an existing bookmark is not blocked by the limit.
    assert api.call("PUT", f"/saved/{first['id']}", owner).status_code == 200


def test_plan_lifecycle_and_links(api: Api) -> None:
    item = api.listing(name())
    owner = api.accounts.session()
    plan = api.ok(
        "POST", "/plans", owner,
        {"title": "Boogie trip", "starts_on": "2026-12-03", "ends_on": "2026-12-08",
         "opportunity_id": item["id"], "note": "  share a car  "}, 201,
    )  # fmt: skip
    assert plan["note"] == "share a car"
    assert plan["opportunity"]["id"] == item["id"]
    # The plan keeps its own dates when the listing is rescheduled.
    api.ok(
        "PATCH", f"/directory/opportunities/{item['id']}", api.reviewer,
        {"starts_on": "2026-12-11", "ends_on": "2026-12-13"},
    )  # fmt: skip
    listed = api.ok("GET", "/plans", owner)[0]
    assert (listed["starts_on"], listed["opportunity"]["starts_on"]) == (
        "2026-12-03",
        "2026-12-11",
    )

    venue = api.ok(
        "POST", "/directory/venues", api.reviewer,
        {"name": name(), "country": "ES", **SOURCE}, 201,
    )  # fmt: skip
    both = api.call("PATCH", f"/plans/{plan['id']}", owner, {"venue_id": venue["id"]})
    assert both.json() == {"detail": "plan_link_conflict"}
    moved = api.ok(
        "PATCH", f"/plans/{plan['id']}", owner,
        {"venue_id": venue["id"], "opportunity_id": None,
         "starts_on": "2026-12-10", "ends_on": "2026-12-13"},
    )  # fmt: skip
    assert moved["venue"]["id"] == venue["id"] and moved["opportunity"] is None

    place = api.ok("POST", "/places", owner, {"name": "Farm strip", "country": "ES"}, 201)  # fmt: skip
    at_place = api.ok(
        "PATCH", f"/plans/{plan['id']}", owner,
        {"place_id": place["id"], "venue_id": None},
    )  # fmt: skip
    assert at_place["place"] == {
        "id": place["id"],
        "name": "Farm strip",
        "country": "ES",
    }
    # Deleting the private place keeps the plan.
    assert api.call("DELETE", f"/places/{place['id']}", owner).status_code == 204
    kept = api.ok("GET", "/plans", owner)[0]
    assert kept["place_id"] is None and kept["title"] == "Boogie trip"

    assert api.call("DELETE", f"/plans/{plan['id']}", owner).status_code == 204
    assert api.ok("GET", "/plans", owner) == []


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ({"starts_on": "2026-12-08", "ends_on": "2026-12-03"}, "dates_out_of_order"),
        ({"starts_on": "2026-01-01", "ends_on": "2027-01-02"}, "dates_span_too_long"),
        ({"title": "   "}, "title_required"),
        ({"venue_id": str(uuid.uuid4())}, "venue_not_listed"),
        ({"opportunity_id": str(uuid.uuid4())}, "opportunity_unavailable"),
        ({"place_id": str(uuid.uuid4())}, "place_unknown"),
    ],
)
def test_plan_validation(api: Api, body: dict[str, Any], expected: str) -> None:
    owner = api.accounts.session()
    full = {"title": "Trip", "starts_on": "2026-12-03", "ends_on": "2026-12-04", **body}
    response = api.call("POST", "/plans", owner, full)
    assert response.status_code == 422 and response.json() == {"detail": expected}


def test_plans_are_owner_scoped(api: Api) -> None:
    owner, other = api.accounts.session(), api.accounts.session()
    plan = api.ok(
        "POST", "/plans", owner,
        {"title": "Private", "starts_on": "2026-12-03", "ends_on": "2026-12-03"}, 201,
    )  # fmt: skip
    path = f"/plans/{plan['id']}"
    assert api.call("PATCH", path, other, {"title": "Mine"}).status_code == 404
    assert api.call("DELETE", path, other).status_code == 404
    assert api.ok("GET", "/plans", other) == []
    # Another person's private place cannot be linked.
    place = api.ok("POST", "/places", owner, {"name": "Strip", "country": "ES"}, 201)
    theirs = api.call(
        "POST", "/plans", other,
        {"title": "x", "starts_on": "2026-12-03", "ends_on": "2026-12-03",
         "place_id": place["id"]},
    )  # fmt: skip
    assert theirs.json() == {"detail": "place_unknown"}


def test_plan_limit(api: Api, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(saves_service, "MAX_PLANS", 1)
    owner = api.accounts.session()
    body = {"title": "Trip", "starts_on": "2026-12-03", "ends_on": "2026-12-03"}
    api.ok("POST", "/plans", owner, body, 201)
    over = api.call("POST", "/plans", owner, body)
    assert over.status_code == 409 and over.json() == {"detail": "plan_limit_reached"}
