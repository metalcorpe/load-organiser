"""#148 directory and provisional places over HTTP against the real PostgreSQL store."""

import uuid
from collections.abc import Iterator
from datetime import UTC, date, datetime
from typing import Any

import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlmodel import Session, col

from app.core.db import engine
from app.skydiver.access.http import AccessDependencies
from app.skydiver.directory import service as directory_service
from app.skydiver.directory.api import create_router
from app.skydiver.directory.service import DirectoryService
from app.skydiver.directory.store import sql_directory_store_factory
from app.skydiver.directory.tables import SkydiverProvisionalPlace
from app.tests.skydiver.support import Accounts

SOURCE = {"source_url": "https://example.org/dz-list", "checked_on": "2026-11-01"}
PUBLIC_FIELDS = {
    "id", "name", "country", "locality", "latitude", "longitude", "status",
    "aliases", "source_url", "source_note", "checked_on",
}  # fmt: skip


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

    def venue(self, name: str, *, country: str = "ES", **extra: Any) -> dict[str, Any]:
        body = {"name": name, "country": country, **SOURCE, **extra}
        response = self.call("POST", "/directory/venues", self.reviewer, body)
        assert response.status_code == 201, response.text
        return dict(response.json())

    def search(self, q: str, **params: Any) -> list[dict[str, Any]]:
        response = self.call("GET", "/venues", q=q, **params)
        assert response.status_code == 200, response.text
        return list(response.json()["items"])


@pytest.fixture(scope="module")
def api() -> Iterator[Api]:
    accounts = Accounts.create()
    directory = DirectoryService(
        stores=sql_directory_store_factory(engine), clock=lambda: datetime.now(UTC)
    )
    app = FastAPI()
    app.include_router(
        create_router(
            service=lambda: directory,
            access=AccessDependencies(lambda: accounts.service),
        )
    )
    with TestClient(app) as client:
        yield Api(client, accounts)


def token() -> str:
    """A unique search token so tests sharing the database stay independent."""
    return "Zq" + uuid.uuid4().hex[:10]


# ------------------------------------------------------------------- listing


def test_listed_venues_must_be_source_backed(api: Api) -> None:
    missing = api.call(
        "POST", "/directory/venues", api.reviewer, {"name": token(), "country": "ES"}
    )
    assert missing.status_code == 422
    assert missing.json() == {"detail": "source_required"}
    future = api.call(
        "POST",
        "/directory/venues",
        api.reviewer,
        {"name": token(), "country": "ES", **SOURCE, "checked_on": "2999-01-01"},
    )
    assert future.json() == {"detail": "checked_on_in_future"}


def test_drafts_are_invisible_to_the_public(api: Api) -> None:
    name = token()
    created = api.call(
        "POST",
        "/directory/venues",
        api.reviewer,
        {"name": name, "country": "FR", "listed": False},
    )
    assert created.status_code == 201 and created.json()["status"] == "draft"
    draft_id = created.json()["id"]
    assert api.call("GET", f"/venues/{draft_id}").status_code == 404
    assert (
        api.call("GET", f"/venues/{uuid.uuid4()}").json()
        == api.call("GET", f"/venues/{draft_id}").json()
    )
    assert api.search(name) == []


def test_public_venue_exposes_only_source_backed_identity(api: Api) -> None:
    venue = api.venue(token(), locality="Empuriabrava", latitude=42.25, longitude=3.13)
    detail = api.call("GET", f"/venues/{venue['id']}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["replaced_id"] is None
    # No operator, endorsement, verification, counts or linked private records.
    assert set(body["venue"]) == PUBLIC_FIELDS
    assert body["venue"]["status"] == "listed"
    assert detail.headers["cache-control"] == "no-store"


def test_search_by_name_alias_accents_and_country(api: Api) -> None:
    base = token()
    spain = api.venue(f"{base} Ampuriabrava", country="ES")
    api.call("POST", f"/directory/venues/{spain['id']}/aliases", api.reviewer,
             {"name": f"{base} Empúriabrava"})  # fmt: skip
    api.venue(f"{base} Ampuriabrava", country="PT")  # same name, distinct place

    assert {v["id"] for v in api.search(f"{base.upper()} ampuriabrava")} >= {
        spain["id"]
    }
    assert [v["id"] for v in api.search(f"{base} empuriabrava")] == [spain["id"]]
    assert len(api.search(base)) == 2  # never merged by matching names
    assert [v["country"] for v in api.search(base, country="pt")] == ["PT"]
    assert api.call("GET", "/venues", country="XX").json() == {
        "detail": "country_invalid"
    }


def test_like_wildcards_in_queries_are_not_wildcards(api: Api) -> None:
    base = token()
    api.venue(f"{base} Alpha")
    # As a LIKE wildcard, "%" would match " A"; normalised, it is a word break.
    assert api.search(f"{base}%lpha") == []
    assert len(api.search(f"{base} alpha")) == 1


def test_pagination_is_stable_and_complete(api: Api) -> None:
    base = token()
    created = {api.venue(f"{base} {i:02d}")["id"] for i in range(7)}
    seen: list[str] = []
    cursor = None
    while True:
        params: dict[str, Any] = {"limit": 3}
        if cursor:
            params["cursor"] = cursor
        page = api.call("GET", "/venues", q=base, **params).json()
        seen += [v["id"] for v in page["items"]]
        cursor = page["next_cursor"]
        if not cursor:
            break
    assert len(seen) == len(set(seen)) == 7 and set(seen) == created
    bad = api.call("GET", "/venues", q=base, cursor="!!!")
    assert bad.status_code == 422 and bad.json() == {"detail": "cursor_invalid"}


# ---------------------------------------------------------------- map points


def points(api: Api, **params: Any) -> dict[str, Any]:
    response = api.call("GET", "/venue-points", **params)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    return dict(response.json())


def test_map_points_are_the_public_venues_with_coordinates(api: Api) -> None:
    base = token()
    here: dict[str, Any] = {"latitude": 42.258571, "longitude": 3.137}
    listed = api.venue(f"{base} Listed", locality="Field", **here)
    closed = api.venue(f"{base} Closed", **here)
    api.call("POST", f"/directory/venues/{closed['id']}/status", api.reviewer,
             {"status": "closed"})  # fmt: skip
    api.venue(f"{base} Nowhere")  # no coordinates: in the list, not on the map
    api.call("POST", "/directory/venues", api.reviewer,
             {"name": f"{base} Draft", "country": "ES", "listed": False, **here})  # fmt: skip
    merged = api.venue(f"{base} Merged", **here)
    api.call("POST", f"/directory/venues/{merged['id']}/merge", api.reviewer,
             {"into": listed["id"]})  # fmt: skip

    page = points(api, q=base)
    assert page["next_cursor"] is None
    assert page["items"] == [
        {"id": closed["id"], "name": f"{base} Closed", "locality": None,
         "country": "ES", "lat": 42.258571, "lon": 3.137, "closed": True},
        {"id": listed["id"], "name": f"{base} Listed", "locality": "Field",
         "country": "ES", "lat": 42.258571, "lon": 3.137, "closed": False},
    ]  # fmt: skip
    # Exactly what the list shows, less the venue without coordinates.
    assert {v["id"] for v in api.search(base)} - {p["id"] for p in page["items"]} == {
        v["id"] for v in api.search(f"{base} Nowhere")
    }


def test_map_points_filter_like_the_list(api: Api) -> None:
    base = token()
    here: dict[str, Any] = {"latitude": 50.0, "longitude": 4.0}
    spain = api.venue(f"{base} Field", country="ES", **here)
    api.call("POST", f"/directory/venues/{spain['id']}/aliases", api.reviewer,
             {"name": f"{base} Alias Ñame"})  # fmt: skip
    belgium = api.venue(f"{base} Field", country="BE", **here)

    assert [p["id"] for p in points(api, q=f"{base} alias name")["items"]] == [
        spain["id"]
    ]
    assert [p["id"] for p in points(api, q=base, country="be")["items"]] == [
        belgium["id"]
    ]
    assert {p["id"] for p in points(api, q=base)["items"]} == {
        spain["id"], belgium["id"]
    }  # fmt: skip
    bad = api.call("GET", "/venue-points", country="XX")
    assert bad.status_code == 422 and bad.json() == {"detail": "country_invalid"}


def test_map_points_are_bounded_and_paged(api: Api) -> None:
    base = token()
    created = {
        api.venue(f"{base} {i}", latitude=10.0 + i, longitude=20.0)["id"]
        for i in range(5)
    }
    seen: list[str] = []
    cursor = None
    while True:
        params: dict[str, Any] = {"q": base, "limit": 2}
        if cursor:
            params["cursor"] = cursor
        page = points(api, **params)
        assert len(page["items"]) <= 2
        seen += [p["id"] for p in page["items"]]
        cursor = page["next_cursor"]
        if not cursor:
            break
    assert len(seen) == len(set(seen)) == 5 and set(seen) == created
    assert api.call("GET", "/venue-points", limit=1001).status_code == 422
    assert api.call("GET", "/venue-points", cursor="!!!").json() == {
        "detail": "cursor_invalid"
    }


# ----------------------------------------------------------------- identity


def test_rename_keeps_identity_and_old_name(api: Api) -> None:
    old, new = token(), token()
    venue = api.venue(old)
    renamed = api.call(
        "PATCH", f"/directory/venues/{venue['id']}", api.reviewer, {"name": new}
    ).json()
    assert renamed["id"] == venue["id"] and renamed["name"] == new
    assert {"name": old, "kind": "former"} in renamed["aliases"]
    assert [v["id"] for v in api.search(old)] == [venue["id"]]
    assert [e["kind"] for e in renamed["events"]] == ["created", "renamed"]


def test_relocation_is_recorded_separately_from_rename(api: Api) -> None:
    venue = api.venue(token(), locality="Old field")
    moved = api.call(
        "PATCH",
        f"/directory/venues/{venue['id']}",
        api.reviewer,
        {"locality": "New field", "latitude": 41.0, "longitude": 2.0},
    ).json()
    assert moved["id"] == venue["id"]
    assert [e["kind"] for e in moved["events"]] == ["created", "relocated"]
    assert moved["events"][-1]["detail"]["locality"] == "New field"
    incomplete = api.call(
        "PATCH", f"/directory/venues/{venue['id']}", api.reviewer, {"latitude": 1.0}
    )
    assert incomplete.json() == {"detail": "coordinates_incomplete"}


def test_closed_venues_stay_public_and_selectable(api: Api) -> None:
    name = token()
    venue = api.venue(name)
    closed = api.call(
        "POST", f"/directory/venues/{venue['id']}/status", api.reviewer,
        {"status": "closed"},
    )  # fmt: skip
    assert closed.json()["status"] == "closed"
    assert api.search(name)[0]["status"] == "closed"
    owner = api.accounts.session()
    linked = api.call(
        "POST",
        "/places",
        owner,
        {"name": "x", "country": "ES", "venue_id": venue["id"]},
    )
    assert linked.status_code == 201
    assert linked.json()["venue"]["status"] == "closed"
    unlist = api.call(
        "POST", f"/directory/venues/{venue['id']}/status", api.reviewer,
        {"status": "draft"},
    )  # fmt: skip
    assert unlist.json() == {"detail": "status_change_invalid"}


def test_reviewed_merge_preserves_references(api: Api) -> None:
    base = token()
    keep = api.venue(f"{base} Keep")
    dupe = api.venue(f"{base} Duplicate")
    owner = api.accounts.session()
    place = api.call(
        "POST", "/places", owner,
        {"name": "My DZ", "country": "ES", "venue_id": dupe["id"]},
    ).json()  # fmt: skip

    merged = api.call(
        "POST", f"/directory/venues/{dupe['id']}/merge", api.reviewer,
        {"into": keep["id"]},
    )  # fmt: skip
    assert merged.status_code == 200
    assert {"name": f"{base} Duplicate", "kind": "merged"} in merged.json()["aliases"]

    # The old ID still resolves, to the surviving venue.
    old = api.call("GET", f"/venues/{dupe['id']}").json()
    assert old["venue"]["id"] == keep["id"] and old["replaced_id"] == dupe["id"]
    # The duplicate's name finds the survivor; the duplicate is no longer listed.
    assert [v["id"] for v in api.search(f"{base} Duplicate")] == [keep["id"]]
    # The owner's private reference resolves without its stored row being rewritten.
    places = api.call("GET", "/places", owner).json()
    assert [p["venue"]["id"] for p in places if p["id"] == place["id"]] == [keep["id"]]
    with Session(engine) as session:
        stored = session.execute(
            select(col(SkydiverProvisionalPlace.venue_id)).where(
                col(SkydiverProvisionalPlace.id) == uuid.UUID(place["id"])
            )
        ).scalar_one()
    assert str(stored) == dupe["id"]

    again = api.call(
        "POST", f"/directory/venues/{dupe['id']}/merge", api.reviewer,
        {"into": keep["id"]},
    )  # fmt: skip
    assert again.json() == {"detail": "merge_already_merged"}
    to_self = api.call(
        "POST", f"/directory/venues/{keep['id']}/merge", api.reviewer,
        {"into": keep["id"]},
    )  # fmt: skip
    assert to_self.json() == {"detail": "merge_into_self"}


def test_public_venue_cannot_merge_into_a_draft(api: Api) -> None:
    listed = api.venue(token())
    draft = api.call(
        "POST", "/directory/venues", api.reviewer,
        {"name": token(), "country": "ES", "listed": False},
    ).json()  # fmt: skip
    refused = api.call(
        "POST", f"/directory/venues/{listed['id']}/merge", api.reviewer,
        {"into": draft["id"]},
    )  # fmt: skip
    assert refused.json() == {"detail": "merge_target_not_public"}


# ------------------------------------------------------------ authorization


REVIEWER_CALLS = [
    ("POST", "/directory/venues", {"name": "x", "country": "ES", **SOURCE}),
    ("GET", "/directory/venues/{id}", None),
    ("PATCH", "/directory/venues/{id}", {"name": "x"}),
    ("POST", "/directory/venues/{id}/aliases", {"name": "x"}),
    ("POST", "/directory/venues/{id}/status", {"status": "closed"}),
    ("POST", "/directory/venues/{id}/merge", {"into": str(uuid.uuid4())}),
]


def test_only_reviewers_maintain_the_directory(api: Api) -> None:
    venue = api.venue(token())
    ordinary = api.accounts.session()
    superuser = api.accounts.session(superuser=True)
    for method, path, body in REVIEWER_CALLS:
        url = path.format(id=venue["id"])
        assert api.call(method, url, None, body).status_code == 401, (method, url)
        for secret in (ordinary, superuser):
            denied = api.call(method, url, secret, body)
            assert denied.status_code == 403, (method, url)
    # Nothing changed.
    assert (
        api.call("GET", f"/venues/{venue['id']}").json()["venue"]["name"]
        == venue["name"]
    )


# -------------------------------------------------------- provisional places


def test_provisional_place_needs_no_listing(api: Api) -> None:
    owner = api.accounts.session()
    created = api.call(
        "POST", "/places", owner, {"name": "  Farm strip  ", "country": "nz"}
    )
    assert created.status_code == 201
    assert created.json()["name"] == "Farm strip"
    assert created.json()["country"] == "NZ" and created.json()["venue"] is None
    # A private place never becomes public.
    assert all(v["name"] != "Farm strip" for v in api.search("Farm strip"))


def test_places_are_owner_scoped(api: Api) -> None:
    owner, other = api.accounts.session(), api.accounts.session()
    place = api.call(
        "POST", "/places", owner, {"name": "Secret field", "country": "IT"}
    ).json()
    for method, body in (("PATCH", {"name": "x"}), ("DELETE", None)):
        foreign = api.call(method, f"/places/{place['id']}", other, body)
        absent = api.call(method, f"/places/{uuid.uuid4()}", other, body)
        assert foreign.status_code == absent.status_code == 404
        assert foreign.json() == absent.json()
    assert place["id"] not in [
        p["id"] for p in api.call("GET", "/places", other).json()
    ]
    assert api.call("GET", "/places", owner).json()[0]["name"] == "Secret field"
    assert api.call("GET", "/places").status_code == 401


def test_unverified_accounts_cannot_create_places(api: Api) -> None:
    unverified = api.accounts.session(verified=False)
    assert api.call("GET", "/places", unverified).status_code == 200
    denied = api.call("POST", "/places", unverified, {"name": "x", "country": "ES"})
    assert denied.status_code == 403 and denied.json() == {"detail": "email_unverified"}


def test_places_link_only_to_public_venues(api: Api) -> None:
    owner = api.accounts.session()
    draft = api.call(
        "POST", "/directory/venues", api.reviewer,
        {"name": token(), "country": "ES", "listed": False},
    ).json()  # fmt: skip
    for venue_id in (draft["id"], str(uuid.uuid4())):
        refused = api.call(
            "POST",
            "/places",
            owner,
            {"name": "x", "country": "ES", "venue_id": venue_id},
        )
        # A draft and a missing venue are indistinguishable.
        assert refused.json() == {"detail": "venue_not_listed"}

    listed = api.venue(token())
    place = api.call("POST", "/places", owner, {"name": "x", "country": "ES"}).json()
    linked = api.call(
        "PATCH", f"/places/{place['id']}", owner, {"venue_id": listed["id"]}
    )
    assert linked.json()["venue"]["id"] == listed["id"]
    cleared = api.call("PATCH", f"/places/{place['id']}", owner, {"venue_id": None})
    assert cleared.json()["venue"] is None
    assert api.call("DELETE", f"/places/{place['id']}", owner).status_code == 204


def test_place_limit(api: Api, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(directory_service, "MAX_PLACES_PER_PERSON", 2)
    owner = api.accounts.session()
    for i in range(2):
        assert (
            api.call(
                "POST", "/places", owner, {"name": f"p{i}", "country": "ES"}
            ).status_code
            == 201
        )
    over = api.call("POST", "/places", owner, {"name": "p3", "country": "ES"})
    assert over.status_code == 409 and over.json() == {"detail": "place_limit_reached"}


def test_venue_listing_is_not_a_claim_of_jumps(api: Api) -> None:
    # The checked date is a source check, not a confirmation of anyone's activity.
    venue = api.venue(token())
    assert api.call("GET", f"/venues/{venue['id']}").json()["venue"]["checked_on"] == (
        date(2026, 11, 1).isoformat()
    )


# ------------------------------------------------------- compare-and-swap (#151)


def test_stale_venue_edits_are_refused_not_overwritten(api: Api) -> None:
    venue = api.venue(f"{token()} DZ")
    path = f"/directory/venues/{venue['id']}"
    assert venue["version"] == 1
    first = api.call("PATCH", path, api.reviewer, {"locality": "A", "version": 1})
    assert first.status_code == 200 and first.json()["version"] == 2
    # A second reviewer still looking at version 1 is told, not silently overwritten.
    stale = api.call("PATCH", path, api.reviewer, {"locality": "B", "version": 1})
    assert stale.status_code == 409 and stale.json() == {"detail": "edit_conflict"}
    current = api.call("GET", path, api.reviewer).json()
    assert (current["locality"], current["version"]) == ("A", 2)
    for method, suffix, body in (
        ("POST", "/status", {"status": "closed", "version": 1}),
        ("POST", "/aliases", {"name": "Old", "version": 1}),
    ):
        refused = api.call(method, path + suffix, api.reviewer, body)
        assert refused.status_code == 409, suffix
    # Without a version the change applies to whatever is current.
    assert api.call("POST", path + "/status", api.reviewer, {"status": "closed"}).status_code == 200  # fmt: skip


def test_merge_compares_both_venues(api: Api) -> None:
    keep, dupe = api.venue(f"{token()} Keep"), api.venue(f"{token()} Dupe")
    path = f"/directory/venues/{dupe['id']}/merge"
    stale = api.call("POST", path, api.reviewer, {"into": keep["id"], "version": 9})
    assert stale.status_code == 409
    merged = api.call("POST", path, api.reviewer, {"into": keep["id"], "version": 1})
    assert merged.status_code == 200
    # The surviving venue's version moved too, so an edit based on its old view fails.
    target = f"/directory/venues/{keep['id']}"
    assert api.call("GET", target, api.reviewer).json()["version"] == 2
    old_view = api.call("PATCH", target, api.reviewer, {"locality": "X", "version": 1})
    assert old_view.status_code == 409


def test_venue_review_queue_and_due_checks(api: Api) -> None:
    base = token()
    draft = api.venue(f"{base} Draft", listed=False)
    old = api.venue(f"{base} Old", checked_on="2020-01-01")
    api.venue(f"{base} Fresh", checked_on=date.today().isoformat())
    every = api.call("GET", f"/directory/venues?q={base}", api.reviewer).json()["items"]
    assert len(every) == 3 and draft["id"] in {v["id"] for v in every}
    due = api.call("GET", f"/directory/venues?q={base}&due=true", api.reviewer).json()
    assert [v["id"] for v in due["items"]] == [old["id"]]
    member = api.accounts.session()
    assert api.call("GET", "/directory/venues", member).status_code == 403
