"""#156 profiles, follows, blocks and profile reports over HTTP against PostgreSQL."""

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
from app.skydiver.logbook.api import create_router as create_logbook_router
from app.skydiver.logbook.service import LogbookService
from app.skydiver.logbook.store import sql_logbook_store_factory
from app.skydiver.social.api import create_router
from app.skydiver.social.service import SocialService
from app.skydiver.social.store import sql_social_store_factory
from app.tests.skydiver.support import Accounts

NOW = datetime(2026, 11, 4, 9, 0, tzinfo=UTC)
SOURCE = {"source_url": "https://example.org/dz", "checked_on": "2026-11-01"}
NOT_FOUND = {"detail": "not_found"}


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

    def ok(self, method: str, path: str, secret: str | None, body: Any = None, status: int = 200, **params: Any) -> Any:  # fmt: skip
        response = self.call(method, path, secret, body, **params)
        assert response.status_code == status, response.text
        return response.json() if response.content else None

    def person(self, *, discoverable: bool = True, name: str = "Alex Jumper") -> tuple[str, str]:  # fmt: skip
        """A verified account with a profile: (session, handle)."""
        secret = self.accounts.session()
        handle = "u" + uuid.uuid4().hex[:12]
        self.ok(
            "PUT", "/me/profile", secret,
            {"handle": handle, "display_name": name, "discoverable": discoverable},
        )  # fmt: skip
        return secret, handle

    def follow(self, secret: str, handle: str) -> str:
        return str(self.ok("PUT", f"/people/{handle}/follow", secret)["state"])

    def connected(self, follower: tuple[str, str], followee: tuple[str, str]) -> None:
        assert self.follow(follower[0], followee[1]) == "requested"
        self.ok("POST", f"/me/people/requests/{follower[1]}/approve", followee[0], status=204)  # fmt: skip


@pytest.fixture(scope="module")
def api() -> Iterator[Api]:
    accounts = Accounts.create()
    directory = DirectoryService(stores=sql_directory_store_factory(engine), clock=lambda: NOW)  # fmt: skip
    social = SocialService(stores=sql_social_store_factory(engine), clock=lambda: NOW, directory=directory)  # fmt: skip
    logbook = LogbookService(stores=sql_logbook_store_factory(engine), clock=lambda: NOW, directory=directory)  # fmt: skip
    gear = GearService(stores=sql_gear_store_factory(engine), clock=lambda: NOW)
    access = AccessDependencies(lambda: accounts.service)
    app = FastAPI()
    app.include_router(create_router(service=lambda: social, identity=lambda: accounts.service, access=access))  # fmt: skip
    app.include_router(
        create_directory_router(service=lambda: directory, access=access)
    )
    app.include_router(create_logbook_router(service=lambda: logbook, access=access))
    app.include_router(create_gear_router(service=lambda: gear, access=access))
    with TestClient(app) as client:
        yield Api(client, accounts)


def test_a_profile_is_opt_in_and_holds_only_what_was_chosen(api: Api) -> None:
    secret = api.accounts.session()
    assert api.ok("GET", "/me/profile", secret) is None
    handle = "a" + uuid.uuid4().hex[:10]
    own = api.ok(
        "PUT", "/me/profile", secret,
        {"handle": handle.upper(), "display_name": "  Sam   Flyer ", "bio": "Belly, mostly.",
         "disciplines": ["belly", "freefly", "belly"]},
    )  # fmt: skip
    assert own["handle"] == handle and own["display_name"] == "Sam Flyer"
    assert own["disciplines"] == ["belly", "freefly"]
    assert own["discoverable"] is False and own["hidden"] is False
    assert "email" not in str(own) and "@" not in str(own)
    # Not discoverable: absent for others, present for the owner.
    assert api.call("GET", f"/people/{handle}").json() == NOT_FOUND
    assert (
        api.call("GET", f"/people/{handle}", api.accounts.session()).json() == NOT_FOUND
    )
    assert api.ok("GET", f"/people/{handle}", secret)["is_self"] is True

    # The handle is fixed; other fields are compare-and-swap edits.
    fixed = api.call(
        "PUT", "/me/profile", secret,
        {"handle": "other" + handle, "display_name": "Sam", "version": own["version"]},
    )  # fmt: skip
    assert fixed.json() == {"detail": "handle_fixed"}
    edited = api.ok(
        "PUT", "/me/profile", secret,
        {"display_name": "Sam", "discoverable": True, "version": own["version"]},
    )  # fmt: skip
    assert edited["version"] == own["version"] + 1
    stale = api.call("PUT", "/me/profile", secret, {"display_name": "X", "version": own["version"]})  # fmt: skip
    assert stale.status_code == 409 and stale.json() == {"detail": "edit_conflict"}
    assert api.ok("GET", f"/people/{handle}", None)["display_name"] == "Sam"


@pytest.mark.parametrize(
    ("handle", "code"),
    [("ab", "handle_invalid"), ("9lives", "handle_invalid"), ("has-dash", "handle_invalid"),
     ("support", "handle_reserved")],
)  # fmt: skip
def test_handle_rules(api: Api, handle: str, code: str) -> None:
    response = api.call(
        "PUT",
        "/me/profile",
        api.accounts.session(),
        {"handle": handle, "display_name": "X"},
    )
    assert response.status_code == 422 and response.json() == {"detail": code}


def test_a_handle_is_unique_ignoring_case(api: Api) -> None:
    _, handle = api.person()
    taken = api.call(
        "PUT", "/me/profile", api.accounts.session(),
        {"handle": handle.upper(), "display_name": "Copy"},
    )  # fmt: skip
    assert taken.json() == {"detail": "handle_taken"}


def test_home_dropzone_must_be_listed(api: Api) -> None:
    body = {
        "name": f"Hm{uuid.uuid4().hex[:6]} DZ",
        "country": "ES",
        **SOURCE,
        "listed": True,
    }
    venue = api.ok("POST", "/directory/venues", api.reviewer, body, 201)
    secret = api.accounts.session()
    unknown = api.call(
        "PUT", "/me/profile", secret,
        {"handle": "h" + uuid.uuid4().hex[:8], "display_name": "H", "home_venue_id": str(uuid.uuid4())},
    )  # fmt: skip
    assert unknown.json() == {"detail": "venue_not_listed"}
    own = api.ok(
        "PUT", "/me/profile", secret,
        {"handle": "h" + uuid.uuid4().hex[:8], "display_name": "H", "home_venue_id": venue["id"]},
    )  # fmt: skip
    assert own["home_venue"]["name"] == body["name"]


def test_search_finds_only_discoverable_profiles(api: Api) -> None:
    tag = uuid.uuid4().hex[:6]
    viewer = api.accounts.session()
    api.person(name=f"Visible {tag}")
    api.person(discoverable=False, name=f"Hidden {tag}")
    found = api.ok("GET", "/people", viewer, q=tag)
    assert [p["display_name"] for p in found] == [f"Visible {tag}"]
    assert api.call("GET", "/people", None, q=tag).status_code == 401
    assert api.call("GET", "/people", viewer, q="x").json() == {
        "detail": "query_too_short"
    }


def test_follow_requests_need_approval_and_a_profile(api: Api) -> None:
    alex, sam = api.person(), api.person()
    no_profile = api.accounts.session()
    refused = api.call("PUT", f"/people/{sam[1]}/follow", no_profile)
    assert refused.status_code == 409 and refused.json() == {
        "detail": "profile_required"
    }
    assert api.call("PUT", f"/people/{alex[1]}/follow", alex[0]).json() == {"detail": "follow_self"}  # fmt: skip

    assert api.follow(alex[0], sam[1]) == "requested"
    assert api.follow(alex[0], sam[1]) == "requested"  # idempotent
    assert api.ok("GET", f"/people/{sam[1]}", alex[0])["follow_state"] == "requested"
    assert [p["handle"] for p in api.ok("GET", "/me/people/requests", sam[0])] == [
        alex[1]
    ]
    assert api.ok("GET", "/me/profile", sam[0])["pending_requests"] == 1

    api.ok("POST", f"/me/people/requests/{alex[1]}/approve", sam[0], status=204)
    assert api.ok("GET", f"/people/{sam[1]}", alex[0])["follow_state"] == "following"
    assert api.ok("GET", f"/people/{alex[1]}", sam[0])["follows_you"] == "following"
    assert [p["handle"] for p in api.ok("GET", "/me/people/following", alex[0])] == [
        sam[1]
    ]

    # Approved followers keep seeing a profile that stops being discoverable.
    own = api.ok("GET", "/me/profile", sam[0])
    api.ok("PUT", "/me/profile", sam[0], {"display_name": own["display_name"], "version": own["version"]})  # fmt: skip
    assert api.ok("GET", f"/people/{sam[1]}", alex[0])["handle"] == sam[1]
    assert api.call("GET", f"/people/{sam[1]}").json() == NOT_FOUND

    # Removing the follower removes that access.
    api.ok("DELETE", f"/me/people/followers/{alex[1]}", sam[0], status=204)
    assert api.call("GET", f"/people/{sam[1]}", alex[0]).json() == NOT_FOUND


def test_reject_and_cancel(api: Api) -> None:
    alex, sam = api.person(), api.person()
    api.follow(alex[0], sam[1])
    api.ok("DELETE", f"/me/people/requests/{alex[1]}", sam[0], status=204)
    assert api.ok("GET", f"/people/{sam[1]}", alex[0])["follow_state"] == "none"
    api.follow(alex[0], sam[1])
    api.ok("DELETE", f"/people/{sam[1]}/follow", alex[0], status=204)
    assert api.ok("GET", "/me/people/requests", sam[0]) == []


def test_a_follow_never_opens_private_records(api: Api) -> None:
    alex, sam = api.person(), api.person()
    api.connected(alex, sam)
    place = api.ok("POST", "/places", sam[0], {"name": "Strip", "country": "PT"}, 201)[
        "id"
    ]
    jump = api.ok(
        "POST", "/jumps", sam[0],
        {"client_key": str(uuid.uuid4()), "jumped_on": "2026-10-01", "jump_type": "belly",
         "place_id": place, "notes": "private"},
        201,
    )["jump"]  # fmt: skip
    assert api.call("GET", f"/jumps/{jump['id']}", alex[0]).status_code == 404
    assert api.ok("GET", "/jumps", alex[0])["items"] == []
    view = api.ok("GET", f"/people/{sam[1]}", alex[0])
    assert set(view) == {
        "handle", "display_name", "bio", "disciplines", "home_venue", "is_self",
        "follow_state", "follows_you",
    }  # fmt: skip


def test_a_block_removes_both_follows_and_denies_every_route(api: Api) -> None:
    alex, sam = api.person(name="Alex Blocked"), api.person(name="Sam Blocker")
    api.connected(alex, sam)
    api.connected(sam, alex)
    api.ok("PUT", f"/people/{alex[1]}/block", sam[0], status=204)

    assert api.ok("GET", "/me/people/followers", sam[0]) == []
    assert api.ok("GET", "/me/people/following", sam[0]) == []
    assert [p["handle"] for p in api.ok("GET", "/me/people/blocked", sam[0])] == [
        alex[1]
    ]
    # The blocked person: as if the profile did not exist, on every route.
    for method, path in (
        ("GET", f"/people/{sam[1]}"), ("PUT", f"/people/{sam[1]}/follow"),
        ("PUT", f"/people/{sam[1]}/block"), ("DELETE", f"/people/{sam[1]}/follow"),
    ):  # fmt: skip
        assert api.call(method, path, alex[0]).json() == NOT_FOUND, path
    report = api.call("POST", f"/people/{sam[1]}/reports", alex[0], {"reason": "spam"})
    assert report.json() == NOT_FOUND
    assert api.ok("GET", "/people", alex[0], q="Sam Blocker") == []
    # Public content stays public to anyone not signed in as the blocked account.
    assert api.ok("GET", f"/people/{sam[1]}", None)["handle"] == sam[1]
    # The blocker does not see the blocked person either, and cannot follow them.
    assert api.call("GET", f"/people/{alex[1]}", sam[0]).json() == NOT_FOUND
    assert api.call("PUT", f"/people/{alex[1]}/follow", sam[0]).json() == NOT_FOUND

    api.ok("DELETE", f"/people/{alex[1]}/block", sam[0], status=204)
    assert (
        api.ok("GET", f"/people/{alex[1]}", sam[0])["follow_state"] == "none"
    )  # not restored
    assert api.call("DELETE", f"/people/{alex[1]}/block", sam[0]).json() == NOT_FOUND


def test_a_pending_request_cannot_be_approved_after_a_block(api: Api) -> None:
    alex, sam = api.person(), api.person()
    api.follow(alex[0], sam[1])
    api.ok("PUT", f"/people/{alex[1]}/block", sam[0], status=204)
    approve = api.call("POST", f"/me/people/requests/{alex[1]}/approve", sam[0])
    assert approve.json() == NOT_FOUND
    assert api.ok("GET", "/me/people/requests", sam[0]) == []


def test_non_discoverable_profiles_cannot_be_probed(api: Api) -> None:
    _, hidden = api.person(discoverable=False)
    stranger = api.person()[0]
    unknown = "zz" + uuid.uuid4().hex[:10]
    for handle in (hidden, unknown):
        for method, path, body in (
            ("GET", f"/people/{handle}", None), ("PUT", f"/people/{handle}/follow", None),
            ("PUT", f"/people/{handle}/block", None),
            ("POST", f"/people/{handle}/reports", {"reason": "spam"}),
        ):  # fmt: skip
            response = api.call(method, path, stranger, body)
            assert (response.status_code, response.json()) == (404, NOT_FOUND), (
                handle,
                path,
            )


def test_writes_need_a_confirmed_email(api: Api) -> None:
    _, handle = api.person()
    unverified = api.accounts.session(verified=False)
    assert api.call("PUT", "/me/profile", unverified, {"handle": "abc", "display_name": "x"}).status_code == 403  # fmt: skip
    assert api.call("PUT", f"/people/{handle}/follow", unverified).status_code == 403
    assert api.ok("GET", f"/people/{handle}", unverified)["handle"] == handle


def test_reports_reach_reviewers_who_can_hide_a_profile(api: Api) -> None:
    reporter, target = api.person(), api.person(name="Fake Official")
    path = f"/people/{target[1]}/reports"
    first = api.call(
        "POST", path, reporter[0], {"reason": "impersonation", "note": "Not them."}
    )
    assert (first.status_code, first.json()) == (202, {"status": "received"})
    again = api.call("POST", path, reporter[0], {"reason": "spam"})
    assert again.status_code == 202
    assert api.call("POST", f"/people/{reporter[1]}/reports", reporter[0], {"reason": "spam"}).json() == {"detail": "report_self"}  # fmt: skip

    assert api.call("GET", "/social/reports", reporter[0]).status_code == 403
    mine = [r for r in api.ok("GET", "/social/reports", api.reviewer) if r["target"]["handle"] == target[1]]  # fmt: skip
    assert len(mine) == 1  # one open report per reporter and target
    report = mine[0]
    assert report["snapshot"]["display_name"] == "Fake Official"
    assert report["reporter"]["handle"] == reporter[1]

    decision = f"/social/reports/{report['id']}/decision"
    needs = api.call("POST", decision, api.reviewer, {"decision": "hide_profile"})
    assert needs.json() == {"detail": "reason_required"}
    decided = api.ok("POST", decision, api.reviewer, {"decision": "hide_profile", "reason": "Impersonation."})  # fmt: skip
    assert decided["status"] == "closed" and decided["target_hidden"] is True
    twice = api.call("POST", decision, api.reviewer, {"decision": "no_action"})
    assert twice.status_code == 409

    # Hidden: gone for everyone else, explained to the owner.
    assert api.call("GET", f"/people/{target[1]}").json() == NOT_FOUND
    assert api.call("GET", f"/people/{target[1]}", reporter[0]).json() == NOT_FOUND
    own = api.ok("GET", "/me/profile", target[0])
    assert own["hidden"] is True and own["moderation_reason"] == "Impersonation."
    # The reported person never learns who reported them.
    assert reporter[1] not in str(own)

    api.ok(
        "PUT", f"/social/profiles/{target[1]}/moderation", api.reviewer,
        {"hidden": False, "publishing_restricted": False, "reason": "Verified."},
        status=204,
    )  # fmt: skip
    assert api.ok("GET", f"/people/{target[1]}", None)["handle"] == target[1]


def test_a_hidden_profile_disappears_from_other_peoples_lists(api: Api) -> None:
    hidden, sam, third = api.person(), api.person(), api.person()
    api.connected(hidden, sam)  # hidden follows sam
    api.connected(sam, hidden)  # sam follows hidden
    assert api.follow(hidden[0], third[1]) == "requested"
    api.ok(
        "PUT", f"/social/profiles/{hidden[1]}/moderation", api.reviewer,
        {"hidden": True, "publishing_restricted": False, "reason": "Spam."},
        status=204,
    )  # fmt: skip
    for relation in ("followers", "following"):
        assert api.ok("GET", f"/me/people/{relation}", sam[0]) == [], relation
    assert api.ok("GET", "/me/people/requests", third[0]) == []
    assert api.ok("GET", "/me/profile", third[0])["pending_requests"] == 0
    # Nor can the old request be approved by handle.
    approve = api.call("POST", f"/me/people/requests/{hidden[1]}/approve", third[0])
    assert approve.json() == NOT_FOUND
    # A hidden profile cannot reappear to someone by asking to follow them.
    other = api.person()
    refused = api.call("PUT", f"/people/{other[1]}/follow", hidden[0])
    assert refused.status_code == 409 and refused.json() == {"detail": "profile_hidden"}


def test_a_reviewer_reason_fits_what_is_stored(api: Api) -> None:
    target = api.person()
    path = f"/social/profiles/{target[1]}/moderation"
    body = {"hidden": True, "publishing_restricted": False}
    long = api.call("PUT", path, api.reviewer, {**body, "reason": "x" * 281})
    assert (long.status_code, long.json()) == (422, {"detail": "reason_too_long"})
    api.ok("PUT", path, api.reviewer, {**body, "reason": "x" * 280}, status=204)
    assert api.ok("GET", "/me/profile", target[0])["moderation_reason"] == "x" * 280
