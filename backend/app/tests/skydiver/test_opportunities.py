"""#149 providers and dated opportunities over HTTP against the real PostgreSQL store."""

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
from app.skydiver.opportunities.api import create_router
from app.skydiver.opportunities.service import OpportunityService
from app.skydiver.opportunities.store import sql_listing_store_factory
from app.tests.skydiver.support import Accounts

NOW = datetime(2026, 11, 3, 12, 0, tzinfo=UTC)
SOURCE = {"source_url": "https://example.org/events", "checked_on": "2026-11-01"}
PUBLIC_FIELDS = {
    "id", "title", "category", "status", "ended", "provider", "venue", "country",
    "location_note", "starts_on", "ends_on", "time_zone", "disciplines", "audience",
    "languages", "summary", "prerequisites", "price_amount", "price_currency",
    "price_basis", "price_note", "registration_url", "source_url", "source_note",
    "checked_on",
}  # fmt: skip
PROVIDER_FIELDS = {
    "id", "name", "kind", "country", "website_url", "source_url", "source_note",
    "checked_on",
}  # fmt: skip


class Clock:
    def __init__(self) -> None:
        self.now = NOW

    def __call__(self) -> datetime:
        return self.now


class Api:
    def __init__(self, client: TestClient, accounts: Accounts, clock: Clock) -> None:
        self.client = client
        self.clock = clock
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

    def ok(self, method: str, path: str, body: Any = None, status: int = 200) -> Any:
        response = self.call(method, path, self.reviewer, body)
        assert response.status_code == status, response.text
        return response.json()

    def provider(self, name: str, *, publish: bool = True, **extra: Any) -> Any:
        body = {"name": name, "kind": "organization", **SOURCE, **extra}
        return self.ok(
            "POST", "/directory/providers", {**body, "publish": publish}, 201
        )

    def draft(self, title: str, provider_id: str, **extra: Any) -> Any:
        body = {
            "title": title,
            "category": "boogie",
            "provider_id": provider_id,
            "country": "ES",
            "location_note": "Airfield to be confirmed by the organiser",
            "starts_on": "2026-12-04",
            "ends_on": "2026-12-08",
            "time_zone": "Europe/Madrid",
            "registration_url": "https://example.org/register",
            **SOURCE,
            **extra,
        }
        return self.ok("POST", "/directory/opportunities", body, 201)

    def status(self, opportunity_id: str, status: str) -> httpx2.Response:
        return self.call(
            "POST",
            f"/directory/opportunities/{opportunity_id}/status",
            self.reviewer,
            {"status": status},
        )

    def publish(self, opportunity_id: str) -> Any:
        assert self.status(opportunity_id, "review").status_code == 200
        response = self.status(opportunity_id, "published")
        assert response.status_code == 200, response.text
        return response.json()

    def listed(self, title: str, provider_id: str, **extra: Any) -> Any:
        return self.publish(self.draft(title, provider_id, **extra)["id"])

    def search(self, **params: Any) -> list[dict[str, Any]]:
        response = self.call("GET", "/opportunities", **params)
        assert response.status_code == 200, response.text
        return list(response.json()["items"])

    def titles(self, **params: Any) -> list[str]:
        return [item["title"] for item in self.search(**params)]


@pytest.fixture(scope="module")
def api() -> Iterator[Api]:
    accounts = Accounts.create()
    clock = Clock()
    directory = DirectoryService(
        stores=sql_directory_store_factory(engine), clock=lambda: datetime.now(UTC)
    )
    opportunities = OpportunityService(
        stores=sql_listing_store_factory(engine),
        clock=clock,
    )
    access = AccessDependencies(lambda: accounts.service)
    app = FastAPI()
    app.include_router(create_router(service=lambda: opportunities, access=access))
    app.include_router(
        create_directory_router(service=lambda: directory, access=access)
    )
    with TestClient(app) as client:
        yield Api(client, accounts, clock)


@pytest.fixture(autouse=True)
def reset_clock(api: Api) -> None:
    api.clock.now = NOW


def token() -> str:
    """A unique search token so tests sharing the database stay independent."""
    return "Zq" + uuid.uuid4().hex[:10]


def test_draft_listing_is_not_public_until_reviewed_and_published(api: Api) -> None:
    base = token()
    provider = api.provider(f"{base} Org")
    draft = api.draft(f"{base} Boogie", provider["id"])
    assert draft["status"] == "draft"
    assert api.call("GET", f"/opportunities/{draft['id']}").status_code == 404
    assert api.titles(q=base) == []

    # Publication goes through review.
    skipped = api.status(draft["id"], "published")
    assert skipped.json() == {"detail": "status_change_invalid"}
    api.publish(draft["id"])
    assert api.titles(q=base) == [f"{base} Boogie"]


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ({"registration_url": None}, "registration_url_required"),
        ({"source_url": None}, "source_required"),
        ({"location_note": None}, "location_required"),
        ({"starts_on": None, "ends_on": None}, "schedule_required"),
    ],
)
def test_publication_requires_source_registration_location_and_dates(
    api: Api, change: dict[str, Any], expected: str
) -> None:
    provider = api.provider(f"{token()} Org")
    draft = api.draft(token(), provider["id"])
    api.ok("PATCH", f"/directory/opportunities/{draft['id']}", change)
    assert api.status(draft["id"], "review").status_code == 200
    response = api.status(draft["id"], "published")
    assert response.status_code == 422
    assert response.json() == {"detail": expected}


def test_publication_requires_a_published_provider(api: Api) -> None:
    provider = api.provider(f"{token()} Draft org", publish=False)
    draft = api.draft(token(), provider["id"])
    api.status(draft["id"], "review")
    assert api.status(draft["id"], "published").json() == {
        "detail": "provider_not_published"
    }


def test_public_listing_shape_hides_reviewer_and_history(api: Api) -> None:
    base = token()
    provider = api.provider(
        f"{base} Coaching Co", kind="person", website_url="https://coach.example"
    )
    item = api.listed(
        f"{base} Freefly camp",
        provider["id"],
        category="camp",
        disciplines=["freefly", "belly"],
        audience=["licensed"],
        languages=["en", "ES"],
        prerequisites="B licence and 200 jumps",
        price_amount="1250.50",
        price_currency="eur",
        price_basis="per_person",
        price_note="Jump tickets not included",
    )
    found = api.search(q=base)
    assert len(found) == 1
    public = found[0]
    assert set(public) == PUBLIC_FIELDS
    assert public["provider"] == {
        "id": provider["id"],
        "name": f"{base} Coaching Co",
        "kind": "person",
    }
    assert public["disciplines"] == ["belly", "freefly"]
    assert public["languages"] == ["en", "es"]
    assert (public["price_amount"], public["price_currency"]) == ("1250.50", "EUR")
    assert public["status"] == "published" and public["ended"] is False

    detail = api.call("GET", f"/opportunities/{item['id']}")
    assert detail.headers["cache-control"] == "no-store"
    assert set(detail.json()["opportunity"]) == PUBLIC_FIELDS
    provider_page = api.call("GET", f"/providers/{provider['id']}").json()
    assert set(provider_page["provider"]) == PROVIDER_FIELDS

    # Nothing about the reviewer or the change history leaks into public bodies.
    reviewer_id = api.accounts.service.current_viewer(secret=api.reviewer).account_id
    for body in (found, detail.json(), provider_page):
        text = json.dumps(body)
        assert str(reviewer_id) not in text
        assert '"events"' not in text and "@example.com" not in text

    # The reviewer sees the history.
    review = api.ok("GET", f"/directory/opportunities/{item['id']}")
    assert [e["kind"] for e in review["events"]] == [
        "created",
        "status_changed",
        "status_changed",
    ]


def test_reviewer_operations_require_the_role(api: Api) -> None:
    provider = api.provider(f"{token()} Org")
    member = api.accounts.session()
    body = {"name": "x", "kind": "person"}
    assert api.call("POST", "/directory/providers", None, body).status_code == 401
    assert api.call("POST", "/directory/providers", member, body).status_code == 403
    path = f"/directory/providers/{provider['id']}"
    assert api.call("GET", path, member).status_code == 403
    assert api.call("GET", "/directory/opportunities/" + str(uuid.uuid4()), member).status_code == 403  # fmt: skip


def test_ended_listings_leave_upcoming_results_by_their_own_time_zone(
    api: Api,
) -> None:
    base = token()
    provider = api.provider(f"{base} Org")
    today_madrid = api.listed(
        f"{base} A Madrid today", provider["id"],
        starts_on="2026-11-01", ends_on="2026-11-03", time_zone="Europe/Madrid",
    )  # fmt: skip
    api.listed(
        f"{base} B Madrid yesterday", provider["id"],
        starts_on="2026-11-01", ends_on="2026-11-02", time_zone="Europe/Madrid",
    )  # fmt: skip
    kiritimati = api.listed(
        f"{base} C Kiritimati today", provider["id"], country="KI",
        starts_on="2026-11-01", ends_on="2026-11-03", time_zone="Pacific/Kiritimati",
    )  # fmt: skip

    # 12:00 UTC on 3 November: still the 3rd in Madrid, already the 4th in Kiritimati.
    assert api.titles(q=base) == [f"{base} A Madrid today"]
    detail = api.call("GET", f"/opportunities/{kiritimati['id']}").json()
    assert detail["opportunity"]["ended"] is True  # still readable by ID

    api.clock.now = datetime(2026, 11, 3, 23, 0, tzinfo=UTC)
    assert api.titles(q=base) == []
    ended = api.call("GET", f"/opportunities/{today_madrid['id']}").json()
    assert ended["opportunity"]["ended"] is True


def test_postponed_without_dates_stays_public_and_cancelled_shows_status(
    api: Api,
) -> None:
    base = token()
    provider = api.provider(f"{base} Org")
    early = api.listed(f"{base} Early", provider["id"])
    moved = api.listed(f"{base} Moved", provider["id"], starts_on="2026-11-20", ends_on="2026-11-21")  # fmt: skip
    path = f"/directory/opportunities/{moved['id']}"

    # Dates can only be cleared once postponed.
    cleared = api.call(
        "PATCH", path, api.reviewer, {"starts_on": None, "ends_on": None}
    )
    assert cleared.json() == {"detail": "schedule_required"}
    # Postponing clears the announced dates; history keeps them.
    postponed = api.status(moved["id"], "postponed").json()
    assert (postponed["starts_on"], postponed["ends_on"]) == (None, None)
    assert postponed["time_zone"] == "Europe/Madrid"
    old = [e for e in api.ok("GET", path)["events"] if e["kind"] == "rescheduled"]
    assert old[-1]["detail"]["starts_on"] == {"from": "2026-11-20", "to": None}
    # The old end date passing does not expire a postponed listing.
    api.clock.now = datetime(2026, 11, 25, tzinfo=UTC)
    assert f"{base} Moved" in api.titles(q=base)
    api.clock.now = NOW

    items = api.search(q=base)
    assert [(i["title"], i["status"], i["starts_on"]) for i in items] == [
        (f"{base} Early", "published", "2026-12-04"),
        (f"{base} Moved", "postponed", None),  # unknown dates are listed last
    ]
    # Unknown dates are not matched by a date filter.
    assert api.titles(q=base, **{"from": "2026-12-01"}) == [f"{base} Early"]

    # New dates and republication are recorded as a schedule revision.
    api.ok("PATCH", path, {"starts_on": "2027-01-10", "ends_on": "2027-01-12"})
    assert api.status(moved["id"], "published").status_code == 200
    history = api.ok("GET", path)["events"]
    rescheduled = [e for e in history if e["kind"] == "rescheduled"]
    assert rescheduled[-1]["detail"]["starts_on"] == {"from": None, "to": "2027-01-10"}

    assert api.status(early["id"], "cancelled").status_code == 200
    public = api.call("GET", f"/opportunities/{early['id']}").json()
    assert public["opportunity"]["status"] == "cancelled"
    assert api.status(early["id"], "archived").status_code == 200
    assert api.call("GET", f"/opportunities/{early['id']}").status_code == 404
    assert api.titles(q=base) == [f"{base} Moved"]


def test_duplicate_listing_resolves_to_the_kept_one(api: Api) -> None:
    base = token()
    provider = api.provider(f"{base} Org")
    keep = api.listed(f"{base} Keep", provider["id"])
    dupe = api.listed(
        f"{base} Copy", provider["id"], source_url="https://other.example/same-event"
    )
    draft = api.draft(f"{base} Draft", provider["id"])

    # A public listing cannot be consolidated into a non-public one.
    refused = api.call(
        "POST", f"/directory/opportunities/{dupe['id']}/duplicate", api.reviewer,
        {"of": draft["id"]},
    )  # fmt: skip
    assert refused.json() == {"detail": "duplicate_target_not_public"}

    api.ok(
        "POST", f"/directory/opportunities/{dupe['id']}/duplicate", {"of": keep["id"]}
    )
    assert api.titles(q=base) == [f"{base} Keep"]
    resolved = api.call("GET", f"/opportunities/{dupe['id']}").json()
    assert resolved["opportunity"]["id"] == keep["id"]
    assert resolved["replaced_id"] == dupe["id"]
    # The consolidated listing's source stays in the kept listing's history.
    history = api.ok("GET", f"/directory/opportunities/{keep['id']}")["events"]
    assert history[-1]["kind"] == "duplicate_absorbed"
    assert history[-1]["detail"]["source_url"] == "https://other.example/same-event"
    # Consolidation is final.
    again = api.status(dupe["id"], "draft")
    assert again.status_code == 422


def test_provider_merge_moves_listings_and_redirects(api: Api) -> None:
    base = token()
    keep = api.provider(f"{base} Travelling Coach")
    dupe = api.provider(f"{base} T. Coach")
    listing = api.listed(f"{base} Clinic", dupe["id"])

    # A provider with live public listings cannot be withdrawn.
    archived = api.call(
        "POST", f"/directory/providers/{dupe['id']}/status", api.reviewer,
        {"status": "archived"},
    )  # fmt: skip
    assert archived.json() == {"detail": "provider_in_use"}

    api.ok("POST", f"/directory/providers/{dupe['id']}/merge", {"into": keep["id"]})
    moved = api.search(q=base)
    assert [i["provider"]["id"] for i in moved] == [keep["id"]]
    redirected = api.call("GET", f"/providers/{dupe['id']}").json()
    assert redirected["provider"]["id"] == keep["id"]
    assert redirected["replaced_id"] == dupe["id"]
    assert api.titles(provider=keep["id"]) == [f"{base} Clinic"]
    # A filter by the merged provider's old ID finds the survivor's listings too.
    assert api.titles(provider=dupe["id"]) == [f"{base} Clinic"]
    events = api.ok("GET", f"/directory/opportunities/{listing['id']}")["events"]
    assert events[-1]["kind"] == "provider_merged"
    # New listings for the merged provider attach to the survivor.
    created = api.draft(f"{base} Later", dupe["id"])
    assert created["provider_id"] == keep["id"]


def test_venue_link_requires_a_public_venue_and_survives_a_venue_merge(
    api: Api,
) -> None:
    base = token()
    provider = api.provider(f"{base} Org")
    venue_body = {"country": "ES", **SOURCE}
    old = api.ok("POST", "/directory/venues", {"name": f"{base} Old DZ", **venue_body}, 201)  # fmt: skip
    new = api.ok("POST", "/directory/venues", {"name": f"{base} New DZ", **venue_body}, 201)  # fmt: skip
    hidden = api.ok(
        "POST", "/directory/venues",
        {"name": f"{base} Draft DZ", **venue_body, "listed": False}, 201,
    )  # fmt: skip

    refused = api.call(
        "POST", "/directory/opportunities", api.reviewer,
        {"title": base, "category": "event", "provider_id": provider["id"],
         "country": "ES", "venue_id": hidden["id"]},
    )  # fmt: skip
    assert refused.json() == {"detail": "venue_not_listed"}

    item = api.listed(f"{base} At old", provider["id"], venue_id=old["id"], location_note=None)  # fmt: skip
    assert item["venue_id"] == old["id"]
    api.ok("POST", f"/directory/venues/{old['id']}/merge", {"into": new["id"]})

    public = api.call("GET", f"/opportunities/{item['id']}").json()["opportunity"]
    assert public["venue"]["id"] == new["id"]
    # Filtering by the surviving venue, or the merged one, finds it.
    assert api.titles(venue=new["id"]) == [f"{base} At old"]
    assert api.titles(venue=old["id"]) == [f"{base} At old"]


def test_filters_and_pagination(api: Api) -> None:
    base = token()
    org = api.provider(f"{base} Org")
    school = api.provider(f"{base} Academy {token()}")
    api.listed(
        f"{base} 1 Student course", school["id"], category="course",
        audience=["students"], starts_on="2026-12-01", ends_on="2026-12-02",
    )  # fmt: skip
    api.listed(
        f"{base} 2 Wingsuit camp", org["id"], category="camp", country="FR",
        disciplines=["wingsuit"], audience=["experienced"],
        starts_on="2026-12-10", ends_on="2026-12-12", time_zone="Europe/Paris",
    )  # fmt: skip
    api.listed(
        f"{base} 3 Boogie", org["id"], starts_on="2027-02-01", ends_on="2027-02-03"
    )

    assert api.titles(q=base, category="course") == [f"{base} 1 Student course"]
    assert api.titles(q=base, audience="students") == [f"{base} 1 Student course"]
    assert api.titles(q=base, discipline="wingsuit") == [f"{base} 2 Wingsuit camp"]
    assert api.titles(q=base, country="FR") == [f"{base} 2 Wingsuit camp"]
    assert api.titles(q=base, **{"from": "2026-12-05", "to": "2027-01-31"}) == [
        f"{base} 2 Wingsuit camp"
    ]
    # The search also matches the organiser's name.
    assert api.titles(q=school["name"]) == [f"{base} 1 Student course"]

    first = api.call("GET", "/opportunities", q=base, limit=2).json()
    assert [i["title"] for i in first["items"]] == [
        f"{base} 1 Student course",
        f"{base} 2 Wingsuit camp",
    ]
    second = api.call(
        "GET", "/opportunities", q=base, limit=2, cursor=first["next_cursor"]
    ).json()
    assert [i["title"] for i in second["items"]] == [f"{base} 3 Boogie"]
    assert second["next_cursor"] is None


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        ({"cursor": "not-a-cursor"}, "cursor_invalid"),
        ({"country": "XX"}, "country_invalid"),
        ({"from": "2026-12-10", "to": "2026-12-01"}, "dates_out_of_order"),
    ],
)
def test_search_rejects_bad_filters(
    api: Api, params: dict[str, str], expected: str
) -> None:
    response = api.call("GET", "/opportunities", **params)
    assert response.status_code == 422
    assert response.json() == {"detail": expected}


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        ({"time_zone": "Mars/Base"}, "time_zone_invalid"),
        ({"ends_on": "2026-12-01"}, "dates_out_of_order"),
        ({"price_amount": "10"}, "price_incomplete"),
        ({"languages": ["zz"]}, "languages_invalid"),
        ({"registration_url": "javascript:alert(1)"}, "source_url_invalid"),
        ({"checked_on": "2026-11-04"}, "checked_on_in_future"),
    ],
)
def test_reviewer_input_is_validated(
    api: Api, change: dict[str, Any], expected: str
) -> None:
    provider = api.provider(f"{token()} Org")
    draft = api.draft(token(), provider["id"])
    response = api.call(
        "PATCH", f"/directory/opportunities/{draft['id']}", api.reviewer, change
    )
    assert response.status_code == 422
    assert response.json() == {"detail": expected}


def test_unknown_ids_are_not_found(api: Api) -> None:
    missing = str(uuid.uuid4())
    assert api.call("GET", f"/opportunities/{missing}").status_code == 404
    assert api.call("GET", f"/providers/{missing}").status_code == 404
    draft_provider = api.provider(f"{token()} Hidden", publish=False)
    assert api.call("GET", f"/providers/{draft_provider['id']}").status_code == 404
    assert (
        api.call(
            "POST", "/directory/opportunities", api.reviewer,
            {"title": "x", "category": "event", "provider_id": missing, "country": "ES"},
        ).json()
        == {"detail": "provider_unknown"}
    )  # fmt: skip


def test_reassigning_provider_and_venue_is_recorded(api: Api) -> None:
    base = token()
    first = api.provider(f"{base} First")
    second = api.provider(f"{base} Second")
    venue = api.ok(
        "POST", "/directory/venues", {"name": f"{base} DZ", "country": "ES", **SOURCE}, 201
    )  # fmt: skip
    item = api.listed(f"{base} Event", first["id"])
    path = f"/directory/opportunities/{item['id']}"
    api.ok("PATCH", path, {"provider_id": second["id"], "venue_id": venue["id"]})
    updated = [e for e in api.ok("GET", path)["events"] if e["kind"] == "updated"]
    assert updated[-1]["detail"] == {
        "provider_id": {"from": first["id"], "to": second["id"]},
        "venue_id": {"from": None, "to": venue["id"]},
    }
    # Moving a public listing to an unpublished organizer is refused.
    hidden = api.provider(f"{base} Hidden", publish=False)
    refused = api.call("PATCH", path, api.reviewer, {"provider_id": hidden["id"]})
    assert refused.json() == {"detail": "provider_not_published"}


def test_ended_listing_omits_an_organizer_that_is_no_longer_published(
    api: Api,
) -> None:
    base = token()
    provider = api.provider(f"{base} Org")
    item = api.listed(f"{base} Past", provider["id"], starts_on="2026-11-03", ends_on="2026-11-03")  # fmt: skip
    api.clock.now = datetime(2026, 11, 5, tzinfo=UTC)
    api.ok(
        "POST", f"/directory/providers/{provider['id']}/status", {"status": "archived"}
    )
    ended = api.call("GET", f"/opportunities/{item['id']}").json()["opportunity"]
    assert ended["ended"] is True
    assert ended["provider"] is None
    assert f"{base} Org" not in json.dumps(ended)
