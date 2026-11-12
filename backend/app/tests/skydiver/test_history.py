"""#154 personal history and prior-history baseline over HTTP against PostgreSQL."""

import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from typing import Any

import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.db import engine
from app.skydiver.access.http import AccessDependencies
from app.skydiver.directory.api import create_router as create_directory_router
from app.skydiver.directory.service import DirectoryService
from app.skydiver.directory.store import sql_directory_store_factory
from app.skydiver.gear.api import create_router as create_gear_router
from app.skydiver.gear.service import GearService
from app.skydiver.gear.store import sql_gear_store_factory
from app.skydiver.history.api import create_router
from app.skydiver.history.service import HistoryService
from app.skydiver.history.store import SqlHistoryStore, sql_history_store_factory
from app.skydiver.logbook.api import create_router as create_logbook_router
from app.skydiver.logbook.service import LogbookService
from app.skydiver.logbook.store import sql_logbook_store_factory
from app.tests.skydiver.support import Accounts

NOW = datetime(2026, 11, 3, 12, 0, tzinfo=UTC)
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

    def venue(self) -> dict[str, Any]:
        body = {"name": f"Hs{uuid.uuid4().hex[:8]} DZ", "country": "ES", **SOURCE}
        venue = self.ok("POST", "/directory/venues", self.reviewer, body, 201)
        self.ok(
            "POST", f"/directory/venues/{venue['id']}/status", self.reviewer,
            {"status": "listed"},
        )  # fmt: skip
        return dict(venue)

    def place(self, secret: str) -> str:
        body = {"name": "Farm strip", "country": "PT"}
        return str(self.ok("POST", "/places", secret, body, 201)["id"])

    def component(self, secret: str, label: str) -> str:
        body = {"client_key": str(uuid.uuid4()), "kind": "main", "label": label}
        return str(self.ok("POST", "/gear/components", secret, body, 201)["component"]["id"])  # fmt: skip

    def jump(self, secret: str, on: str, **fields: Any) -> dict[str, Any]:
        body = {
            "client_key": str(uuid.uuid4()),
            "jumped_on": on,
            "jump_type": "belly",
            "confirm_distinct": True,
            **fields,
        }
        if "venue_id" not in fields and "place_id" not in fields:
            body["place_id"] = self.place(secret)
        return dict(self.ok("POST", "/jumps", secret, body, 201)["jump"])

    def history(self, secret: str) -> dict[str, Any]:
        return dict(self.ok("GET", "/history", secret))


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
    history = HistoryService(
        stores=sql_history_store_factory(engine), clock=lambda: NOW, directory=directory
    )
    access = AccessDependencies(lambda: accounts.service)
    app = FastAPI()
    app.include_router(create_router(service=lambda: history, access=access))
    app.include_router(create_logbook_router(service=lambda: logbook, access=access))
    app.include_router(
        create_directory_router(service=lambda: directory, access=access)
    )
    app.include_router(create_gear_router(service=lambda: gear, access=access))
    with TestClient(app) as client:
        yield Api(client, accounts)


def test_without_a_baseline_only_recorded_entries_are_reported(api: Api) -> None:
    owner = api.accounts.session()
    empty = api.history(owner)
    assert empty["totals"] == {
        "recorded": 0, "prior_jumps": None, "before_on": None,
        "recorded_before": None, "recorded_since": None, "lifetime": None,
        "inconsistent": False,
    }  # fmt: skip
    assert empty["baseline"] is None and empty["last_jump_on"] is None
    assert [m["month"] for m in empty["months"]][-1] == "2026-11"
    assert len(empty["months"]) == 12

    # A high jump number is not a lifetime total.
    api.jump(owner, "2026-10-10", jump_number=900)
    totals = api.history(owner)["totals"]
    assert (totals["recorded"], totals["lifetime"]) == (1, None)


def test_decision_fixture_b200_and_a_pre_cutoff_entry(api: Api) -> None:
    owner = api.accounts.session()
    for on in ("2026-06-01", "2026-07-04", "2026-10-30"):  # on/after D
        api.jump(owner, on)
    base = api.ok(
        "PUT", "/history/baseline", owner,
        {"prior_jumps": 200, "before_on": "2026-06-01"},
    )  # fmt: skip
    assert base["totals"]["lifetime"] == 203
    assert base["baseline"]["version"] == 1 and base["baseline"]["source"] == "manual"

    pre = api.jump(owner, "2026-05-31")  # already represented by B
    t = api.history(owner)["totals"]
    assert (t["recorded"], t["recorded_before"], t["recorded_since"]) == (4, 1, 3)
    assert t["lifetime"] == 203 and not t["inconsistent"]

    # Deleting the old entry does not rewrite the declared B.
    api.ok("DELETE", f"/jumps/{pre['id']}", owner, status=204, version=pre["version"])
    after = api.history(owner)
    assert after["totals"]["lifetime"] == 203
    assert after["baseline"]["prior_jumps"] == 200


def test_too_many_entries_before_the_cutoff_are_flagged_not_rejected(
    api: Api,
) -> None:
    owner = api.accounts.session()
    api.ok("PUT", "/history/baseline", owner, {"prior_jumps": 1, "before_on": "2026-06-01"})  # fmt: skip
    api.jump(owner, "2026-01-01")
    api.jump(owner, "2026-02-01")  # saved, even though B says only one came before D
    api.jump(owner, "2026-08-01")
    t = api.history(owner)["totals"]
    assert t["inconsistent"] and t["lifetime"] is None
    assert (t["prior_jumps"], t["recorded_before"], t["recorded_since"]) == (1, 2, 1)

    # The preview shows the correction's effect before anything is saved.
    preview = api.ok(
        "GET", "/history/baseline/preview", owner,
        prior_jumps=40, before_on="2026-06-01",
    )  # fmt: skip
    assert preview["current"]["inconsistent"]
    assert preview["proposed"]["lifetime"] == 41
    assert api.history(owner)["baseline"]["prior_jumps"] == 1


def test_corrections_compare_and_swap_and_keep_provenance(api: Api) -> None:
    owner = api.accounts.session()
    body = {"prior_jumps": 50, "before_on": "2025-01-01"}
    first = api.ok("PUT", "/history/baseline", owner, body)["baseline"]
    # A second "first declaration" (an older tab) does not overwrite.
    again = api.call("PUT", "/history/baseline", owner, body)
    assert again.status_code == 409 and again.json() == {"detail": "edit_conflict"}

    corrected = api.ok(
        "PUT", "/history/baseline", owner,
        {"prior_jumps": 55, "before_on": "2025-02-01", "version": first["version"]},
    )  # fmt: skip
    assert corrected["baseline"]["version"] == 2
    stale = api.call(
        "PUT", "/history/baseline", owner,
        {"prior_jumps": 60, "before_on": "2025-02-01", "version": 1},
    )  # fmt: skip
    assert stale.status_code == 409

    # Saving the same values again records nothing.
    same = api.ok(
        "PUT", "/history/baseline", owner,
        {"prior_jumps": 55, "before_on": "2025-02-01", "version": 2},
    )  # fmt: skip
    assert same["baseline"]["version"] == 2

    assert api.call("DELETE", "/history/baseline", owner, version=1).status_code == 409
    api.ok("DELETE", "/history/baseline", owner, status=204, version=2)
    gone = api.history(owner)
    assert gone["baseline"] is None and gone["totals"]["lifetime"] is None
    assert [(e["kind"], e["detail"]) for e in gone["baseline_events"]] == [
        ("declared", {"prior_jumps": 50, "before_on": "2025-01-01", "source": "manual"}),
        ("corrected", {
            "from": {"prior_jumps": 50, "before_on": "2025-01-01"},
            "to": {"prior_jumps": 55, "before_on": "2025-02-01"},
        }),
        ("removed", {"from": {"prior_jumps": 55, "before_on": "2025-02-01"}}),
    ]  # fmt: skip
    # A correction based on the removed declaration conflicts; a new one is fine.
    late = api.call(
        "PUT", "/history/baseline", owner,
        {"prior_jumps": 1, "before_on": "2025-02-01", "version": 2},
    )  # fmt: skip
    assert late.status_code == 409
    api.ok("PUT", "/history/baseline", owner, {"prior_jumps": 1, "before_on": "2025-02-01"})  # fmt: skip


def test_baseline_rules(api: Api) -> None:
    owner = api.accounts.session()
    future = api.call(
        "PUT", "/history/baseline", owner, {"prior_jumps": 1, "before_on": "2026-11-05"}
    )
    assert future.status_code == 422
    assert future.json() == {"detail": "baseline_date_in_future"}
    # Today anywhere (UTC+14) is accepted.
    api.ok("PUT", "/history/baseline", owner, {"prior_jumps": 1, "before_on": "2026-11-04"})  # fmt: skip
    too_many = api.call(
        "GET", "/history/baseline/preview", owner, prior_jumps=100_001, before_on="2026-01-01"
    )  # fmt: skip
    assert too_many.status_code == 422


def test_breakdowns_derive_only_from_detailed_entries(api: Api) -> None:
    owner = api.accounts.session()
    venue, merged = api.venue(), api.venue()
    place = api.place(owner)
    main = api.component(owner, "Navigator")
    api.component(owner, "Never jumped")
    api.jump(owner, "2026-10-01", venue_id=venue["id"], jump_type="freefly",
             component_ids=[main])  # fmt: skip
    api.jump(owner, "2026-10-02", venue_id=merged["id"], jump_type="freefly")
    api.jump(owner, "2025-03-02", place_id=place, component_ids=[main])
    # A baseline adds no gear use or dated activity.
    api.ok("PUT", "/history/baseline", owner, {"prior_jumps": 300, "before_on": "2026-01-01"})  # fmt: skip
    api.ok(
        "POST", f"/directory/venues/{merged['id']}/merge", api.reviewer,
        {"into": venue["id"]},
    )  # fmt: skip

    h = api.history(owner)
    assert (h["first_jump_on"], h["last_jump_on"]) == ("2025-03-02", "2026-10-02")
    assert {t["jump_type"]: t["jumps"] for t in h["by_type"]} == {
        "freefly": 2,
        "belly": 1,
    }
    assert [(x["location"]["kind"], x["location"]["id"], x["jumps"]) for x in h["by_location"]] == [
        ("venue", venue["id"], 2),  # the merged venue counts under the one that remains
        ("place", place, 1),
    ]  # fmt: skip
    assert [(u["component"]["label"], u["jumps"], u["last_on"]) for u in h["by_component"]] == [
        ("Navigator", 2, "2026-10-01"),
    ]  # fmt: skip
    months = {m["month"]: m["jumps"] for m in h["months"]}
    assert months["2026-10"] == 2 and sum(months.values()) == 2  # 2025-03 is older
    assert h["totals"]["lifetime"] == 302


def test_owner_only_and_writes_need_a_confirmed_email(api: Api) -> None:
    owner, other = api.accounts.session(), api.accounts.session()
    api.jump(owner, "2026-10-01")
    api.ok("PUT", "/history/baseline", owner, {"prior_jumps": 9, "before_on": "2026-01-01"})  # fmt: skip
    seen = api.history(other)
    assert seen["totals"]["recorded"] == 0 and seen["baseline"] is None
    assert seen["baseline_events"] == []

    unverified = api.accounts.session(verified=False)
    assert api.history(unverified)["totals"]["recorded"] == 0
    refused = api.call(
        "PUT",
        "/history/baseline",
        unverified,
        {"prior_jumps": 1, "before_on": "2026-01-01"},
    )
    assert refused.status_code == 403
    assert api.call("GET", "/history").status_code == 401


def test_currency_guidance_from_the_stated_licence_and_dated_entries(
    api: Api,
) -> None:
    owner = api.accounts.session()
    assert api.ok("GET", "/me/licence", owner) == {"licence": "none"}
    # No licence, no jumps: nothing to judge.
    assert api.history(owner)["currency"] == {
        "licence": "none", "threshold_days": None, "last_jump_on": None,
        "current_until": None, "source": "USPA SIM 5-2",
    }  # fmt: skip

    assert api.ok("PUT", "/me/licence", owner, {"licence": "b"}) == {"licence": "b"}
    no_jumps = api.history(owner)["currency"]
    assert (no_jumps["threshold_days"], no_jumps["current_until"]) == (90, None)

    # A prior jump count has no dates: it adds no currency.
    api.ok("PUT", "/history/baseline", owner, {"prior_jumps": 300, "before_on": "2026-10-01"})  # fmt: skip
    assert api.history(owner)["currency"]["current_until"] is None

    api.jump(owner, "2026-08-01")
    api.jump(owner, "2026-10-10", jump_type="tandem")  # every type counts
    c = api.history(owner)["currency"]
    assert (c["last_jump_on"], c["current_until"]) == ("2026-10-10", "2027-01-08")

    api.ok("PUT", "/me/licence", owner, {"licence": "a"})
    assert api.history(owner)["currency"]["current_until"] == "2026-12-09"
    api.ok("PUT", "/me/licence", owner, {"licence": "none"})
    assert api.ok("GET", "/me/licence", owner) == {"licence": "none"}
    assert api.history(owner)["currency"]["threshold_days"] is None

    bad = api.call("PUT", "/me/licence", owner, {"licence": "e"})
    assert bad.status_code == 422


def test_progress_to_the_next_licence_from_own_entries(api: Api) -> None:
    owner = api.accounts.session()
    assert (
        api.history(owner)["progress"] is None
    )  # no licence: nothing beyond the prompt
    api.ok("PUT", "/me/licence", owner, {"licence": "b"})
    api.ok("PUT", "/history/baseline", owner, {"prior_jumps": 40, "before_on": "2026-01-01"})  # fmt: skip
    api.jump(owner, "2025-12-01", freefall_seconds=600)  # within the prior count
    api.jump(owner, "2026-02-01", freefall_seconds=500)
    api.jump(owner, "2026-03-01")  # no freefall time recorded
    assert api.history(owner)["progress"] == {
        "licence": "b", "next_licence": "c",
        # The prior count is in the jump total (40 + 2 since the cutoff) ...
        "jumps": 42, "jumps_required": 200, "jumps_include_prior": True,
        # ... but freefall time comes only from entries that record one.
        "freefall_seconds": 1100, "freefall_required_seconds": 3600,
        "entries_with_freefall": 2, "entries_without_freefall": 1,
        "source": "USPA SIM 3-1",
    }  # fmt: skip

    # Student to A lists no freefall time; D has no next licence.
    api.ok("PUT", "/me/licence", owner, {"licence": "student"})
    student = api.history(owner)["progress"]
    assert (student["next_licence"], student["jumps_required"], student["freefall_required_seconds"]) == ("a", 25, None)  # fmt: skip
    api.ok("PUT", "/me/licence", owner, {"licence": "d"})
    d = api.history(owner)["progress"]
    assert (d["next_licence"], d["jumps_required"], d["freefall_required_seconds"]) == (None, None, None)  # fmt: skip

    # An inconsistent prior count is left out: only the entries count.
    other = api.accounts.session()
    api.ok("PUT", "/me/licence", other, {"licence": "a"})
    api.ok("PUT", "/history/baseline", other, {"prior_jumps": 0, "before_on": "2026-06-01"})  # fmt: skip
    api.jump(other, "2026-05-01", freefall_seconds=60)
    p = api.history(other)["progress"]
    assert (p["jumps"], p["jumps_include_prior"], p["freefall_seconds"]) == (
        1,
        False,
        60,
    )


def test_milestones_derive_from_own_entries_and_the_prior_count(api: Api) -> None:
    owner = api.accounts.session()
    empty = api.ok("GET", "/history/milestones", owner)
    assert empty == {"items": [], "counted": "entries"}
    venue = api.venue()
    api.jump(owner, "2026-01-10", venue_id=venue["id"], jump_type="wingsuit", freefall_seconds=600)  # fmt: skip
    place = api.place(owner)
    start = date(2026, 1, 11)
    for i in range(24):  # 11 January to 3 February
        api.jump(owner, (start + timedelta(days=i)).isoformat(), place_id=place)

    found = api.ok("GET", "/history/milestones", owner)
    assert found["counted"] == "entries"
    items = found["items"]
    assert [(m["kind"], m["on"], m["number"]) for m in items if m["kind"] == "jump_count"] == [
        ("jump_count", "2026-02-03", 25), ("jump_count", "2026-01-10", 1),
    ]  # fmt: skip
    assert (items[0]["kind"], items[0]["number"]) == ("jump_count", 25)  # newest first
    assert [(m["jump_type"], m["on"]) for m in items if m["kind"] == "jump_type"] == [
        ("belly", "2026-01-11"), ("wingsuit", "2026-01-10"),
    ]  # fmt: skip
    firsts = [(m["location"]["kind"], m["location"]["name"], m["on"]) for m in items if m["kind"] == "place"]  # fmt: skip
    assert firsts == [
        ("place", "Farm strip", "2026-01-11"), ("venue", venue["name"], "2026-01-10"),
    ]  # fmt: skip
    assert not [m for m in items if m["kind"] == "freefall"]  # 600 s: under an hour

    # 10 declared before 15 January (5 entries before it are within them): the 25th
    # jump is the 15th entry from 15 January; the 1st is before this logbook.
    api.ok("PUT", "/history/baseline", owner, {"prior_jumps": 10, "before_on": "2026-01-15"})  # fmt: skip
    found = api.ok("GET", "/history/milestones", owner)
    assert found["counted"] == "with_prior"
    assert [(m["number"], m["on"], m["jump_id"] is None) for m in found["items"] if m["kind"] == "jump_count"] == [  # fmt: skip
        (25, "2026-01-29", False), (1, None, True),
    ]  # fmt: skip

    # A prior count below the entries before its date dates no jump count.
    base = api.history(owner)["baseline"]
    api.ok("PUT", "/history/baseline", owner, {"prior_jumps": 2, "before_on": "2026-01-15", "version": base["version"]})  # fmt: skip
    found = api.ok("GET", "/history/milestones", owner)
    assert found["counted"] == "unchecked"
    assert not [m for m in found["items"] if m["kind"] == "jump_count"]

    # Owner-scoped: nobody else sees any of it; no session, no answer.
    other = api.ok("GET", "/history/milestones", api.accounts.session())
    assert other == {"items": [], "counted": "entries"}
    assert api.call("GET", "/history/milestones").status_code == 401


def test_the_licence_is_owner_only_and_needs_a_confirmed_email(api: Api) -> None:
    owner, other = api.accounts.session(), api.accounts.session()
    api.ok("PUT", "/me/licence", owner, {"licence": "c"})
    assert api.ok("GET", "/me/licence", other) == {"licence": "none"}
    assert api.history(other)["currency"]["licence"] == "none"
    unverified = api.accounts.session(verified=False)
    assert api.ok("GET", "/me/licence", unverified) == {"licence": "none"}
    refused = api.call("PUT", "/me/licence", unverified, {"licence": "a"})
    assert refused.status_code == 403
    assert api.call("GET", "/me/licence").status_code == 401
    assert api.call("PUT", "/me/licence", None, {"licence": "a"}).status_code == 401
    assert api.ok("GET", "/me/licence", owner) == {"licence": "c"}


def test_summaries_read_one_snapshot_and_the_pool_is_left_as_it_was() -> None:
    stores = sql_history_store_factory(engine)
    with stores() as store:
        assert isinstance(store, SqlHistoryStore)
        store.snapshot()
        level = store._s.execute(text("SHOW transaction_isolation")).scalar_one()
        assert level == "repeatable read"
    with stores() as store:
        assert isinstance(store, SqlHistoryStore)
        level = store._s.execute(text("SHOW transaction_isolation")).scalar_one()
        assert level == "read committed"
