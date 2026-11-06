"""#157 published jump summaries over HTTP against PostgreSQL."""

import json
import uuid
from collections.abc import Iterator
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
from app.skydiver.logbook.api import create_router as create_logbook_router
from app.skydiver.logbook.service import LogbookService
from app.skydiver.logbook.store import sql_logbook_store_factory
from app.skydiver.posts.api import create_router as create_posts_router
from app.skydiver.posts.service import PostService
from app.skydiver.posts.store import sql_post_store_factory
from app.skydiver.social.api import create_router as create_social_router
from app.skydiver.social.service import SocialService
from app.skydiver.social.store import sql_social_store_factory
from app.tests.skydiver.support import Accounts
from app.tests.skydiver.test_social import NOW, SOURCE
from app.tests.skydiver.test_social import Api as SocialApi

NOT_FOUND = {"detail": "not_found"}


class Api(SocialApi):
    def venue(self) -> dict[str, Any]:
        body = {"name": f"Po{uuid.uuid4().hex[:8]} DZ", "country": "ES", **SOURCE}
        venue = self.ok("POST", "/directory/venues", self.reviewer, body, 201)
        self.ok(
            "POST", f"/directory/venues/{venue['id']}/status", self.reviewer,
            {"status": "listed"},
        )  # fmt: skip
        return dict(venue)

    def jump(self, secret: str, **fields: Any) -> dict[str, Any]:
        if "venue_id" not in fields and "place_id" not in fields:
            fields["venue_id"] = self.venue()["id"]
        body = {
            "client_key": str(uuid.uuid4()),
            "jumped_on": "2026-10-10",
            "jump_type": "belly",
            **fields,
        }
        return dict(self.ok("POST", "/jumps", secret, body, 201)["jump"])

    def publish(self, secret: str, jump: dict[str, Any], **fields: Any) -> httpx2.Response:  # fmt: skip
        body = {"jump_version": jump["version"], "audience": "public", **fields}
        return self.call("POST", f"/me/jumps/{jump['id']}/post", secret, body)

    def published(self, secret: str, jump: dict[str, Any], **fields: Any) -> dict[str, Any]:  # fmt: skip
        response = self.publish(secret, jump, **fields)
        assert response.status_code == 201, response.text
        return dict(response.json())

    def events(self, secret: str, jump_id: str) -> list[dict[str, Any]]:
        return list(self.ok("GET", f"/jumps/{jump_id}", secret)["events"])

    def edit(self, secret: str, jump_id: str, **fields: Any) -> dict[str, Any]:
        current = self.ok("GET", f"/jumps/{jump_id}", secret)["jump"]
        body = {**fields, "version": current["version"]}
        return dict(self.ok("PATCH", f"/jumps/{jump_id}", secret, body)["jump"])


@pytest.fixture(scope="module")
def api() -> Iterator[Api]:
    accounts = Accounts.create()
    directory = DirectoryService(stores=sql_directory_store_factory(engine), clock=lambda: NOW)  # fmt: skip
    social = SocialService(stores=sql_social_store_factory(engine), clock=lambda: NOW, directory=directory)  # fmt: skip
    logbook = LogbookService(stores=sql_logbook_store_factory(engine), clock=lambda: NOW, directory=directory)  # fmt: skip
    posts = PostService(stores=sql_post_store_factory(engine), clock=lambda: NOW, directory=directory, social=social)  # fmt: skip
    access = AccessDependencies(lambda: accounts.service)
    app = FastAPI()
    app.include_router(create_social_router(service=lambda: social, identity=lambda: accounts.service, access=access))  # fmt: skip
    app.include_router(create_posts_router(service=lambda: posts, identity=lambda: accounts.service, access=access))  # fmt: skip
    app.include_router(
        create_directory_router(service=lambda: directory, access=access)
    )
    app.include_router(create_logbook_router(service=lambda: logbook, access=access))
    with TestClient(app) as client:
        yield Api(client, accounts)


def test_a_post_copies_only_the_selected_values(api: Api) -> None:
    owner, handle = api.person(name="Alex Jumper")
    jump = api.jump(
        owner, jump_number=812, exit_altitude=4000, altitude_unit="ft",
        freefall_seconds=55, notes="secret note", links=["https://private.example"],
        other_gear="borrowed rig",
    )  # fmt: skip

    sharing = api.ok("GET", f"/me/jumps/{jump['id']}/sharing", owner)
    assert sharing["post"] is None and sharing["profile"]["handle"] == handle
    assert sharing["jump"]["listed_venue"]["id"] == jump["location"]["id"]
    assert sharing["jump"]["exit_altitude"] == {"value": 4000, "unit": "ft", "datum": "unspecified"}  # fmt: skip

    post = api.published(
        owner, jump, shares=["type", "venue"], caption="Sunset load.",
        link="https://video.example/1",
    )  # fmt: skip
    assert post["jumped_on"] == "2026-10-10" and post["jump_type"] == "belly"
    assert post["venue"]["id"] == jump["location"]["id"]
    assert post["exit_altitude"] is None and post["freefall_seconds"] is None
    assert post["is_owner"] is True and post["jump_id"] == jump["id"]

    seen = api.ok("GET", f"/posts/{post['id']}", None)
    assert seen["author"] == {"handle": handle, "display_name": "Alex Jumper"}
    assert seen["is_owner"] is False and seen["version"] is None
    assert seen["jump_id"] is None
    text = json.dumps(seen)
    for private in ("secret note", "private.example", "borrowed rig", "812"):
        assert private not in text, private

    # A post is not another jump, and publishing is in the owner's history.
    assert len(api.ok("GET", "/jumps", owner)["items"]) == 1
    assert api.events(owner, jump["id"])[-1]["kind"] == "post_published"
    # A second publication of the same jump is refused.
    again = api.publish(owner, api.ok("GET", f"/jumps/{jump['id']}", owner)["jump"])
    assert again.json() == {"detail": "already_published"}


def test_follower_audience_and_blocks(api: Api) -> None:
    owner, stranger, follower, late = api.person(), api.person(), api.person(), api.person()  # fmt: skip
    api.connected(follower, owner)
    post = api.published(owner[0], api.jump(owner[0]), audience="followers")
    path = f"/posts/{post['id']}"

    assert api.call("GET", path).json() == NOT_FOUND
    assert api.call("GET", path, stranger[0]).json() == NOT_FOUND
    assert api.ok("GET", path, follower[0])["audience"] == "followers"
    # A pending request is not enough; people approved later see existing posts.
    assert api.follow(late[0], owner[1]) == "requested"
    assert api.call("GET", path, late[0]).json() == NOT_FOUND
    api.ok("POST", f"/me/people/requests/{late[1]}/approve", owner[0], status=204)
    assert api.ok("GET", path, late[0])["id"] == post["id"]
    listed = api.ok("GET", f"/people/{owner[1]}/posts", late[0])["items"]
    assert [p["id"] for p in listed] == [post["id"]]
    assert api.ok("GET", f"/people/{owner[1]}/posts", None)["items"] == []

    # Removing a follower and blocking revoke access on every route.
    api.ok("DELETE", f"/me/people/followers/{late[1]}", owner[0], status=204)
    assert api.call("GET", path, late[0]).json() == NOT_FOUND
    api.ok("PUT", f"/people/{owner[1]}/block", follower[0], status=204)
    assert api.call("GET", path, follower[0]).json() == NOT_FOUND
    assert api.call("GET", f"/people/{owner[1]}/posts", follower[0]).json() == NOT_FOUND  # fmt: skip
    # A guessed id answers exactly like a post the reader may not see.
    assert api.call("GET", f"/posts/{uuid.uuid7()}", stranger[0]).json() == NOT_FOUND


def test_public_posts_need_a_discoverable_profile(api: Api) -> None:
    owner, handle = api.person(discoverable=False)
    jump = api.jump(owner)
    refused = api.publish(owner, jump)
    assert refused.json() == {"detail": "public_needs_discoverable"}

    profile = api.ok("GET", "/me/profile", owner)
    body = {"display_name": profile["display_name"], "discoverable": True}
    api.ok("PUT", "/me/profile", owner, {**body, "version": profile["version"]})
    public = api.published(owner, jump)
    follower = api.person()
    api.connected(follower, (owner, handle))
    shared = api.published(owner, api.jump(owner), audience="followers")
    assert api.ok("GET", f"/posts/{public['id']}", None)["id"] == public["id"]

    # Turning discoverability off withdraws public posts in the same change;
    # follower-only posts stay for approved followers.
    profile = api.ok("GET", "/me/profile", owner)
    api.ok("PUT", "/me/profile", owner, {**body, "discoverable": False, "version": profile["version"]})  # fmt: skip
    assert api.call("GET", f"/posts/{public['id']}", owner).json() == NOT_FOUND
    assert api.ok("GET", f"/posts/{shared['id']}", follower[0])["id"] == shared["id"]
    withdrawn = api.events(owner, jump["id"])[-1]
    assert withdrawn == {**withdrawn, "kind": "post_withdrawn", "detail": {"reason": "profile_not_discoverable"}}  # fmt: skip


def test_only_edits_to_shared_values_withdraw_a_post(api: Api) -> None:
    owner, _ = api.person()
    jump = api.jump(owner, exit_altitude=4000, altitude_unit="ft", freefall_seconds=50)
    post = api.published(owner, jump, shares=["type", "freefall"])
    path = f"/posts/{post['id']}"

    for unshared in (
        {"notes": "new note"},
        {"exit_altitude": 4200, "deployment_altitude": None, "altitude_unit": "ft"},
        {"jump_number": 9},
    ):
        api.edit(owner, jump["id"], **unshared)
        assert api.ok("GET", path, None)["freefall_seconds"] == 50, unshared

    edited = api.edit(owner, jump["id"], freefall_seconds=60)
    assert api.call("GET", path, owner).json() == NOT_FOUND
    assert api.events(owner, jump["id"])[-1]["kind"] == "post_withdrawn"
    assert api.ok("GET", f"/me/jumps/{jump['id']}/sharing", owner)["post"] is None

    # Republishing needs a fresh preview of the current version.
    assert api.publish(owner, jump).json() == {"detail": "edit_conflict"}
    again = api.published(owner, edited, shares=["freefall"])
    assert again["freefall_seconds"] == 60 and again["jump_type"] is None

    # The activity date is always shared; changing it withdraws too.
    api.edit(owner, jump["id"], jumped_on="2026-10-11")
    assert api.call("GET", f"/posts/{again['id']}", owner).json() == NOT_FOUND

    # Deleting the jump deletes its post.
    third = api.published(owner, api.jump(owner))
    current = api.ok("GET", f"/jumps/{third['jump_id']}", owner)["jump"]
    api.ok("DELETE", f"/jumps/{third['jump_id']}?version={current['version']}", owner, status=204)  # fmt: skip
    assert api.call("GET", f"/posts/{third['id']}", None).json() == NOT_FOUND


@pytest.mark.parametrize(
    ("fields", "shares", "expected"),
    [
        ({"jump_type": "unspecified"}, ["type"], "type_not_recorded"),
        ({}, ["altitude"], "altitude_not_recorded"),
        ({}, ["freefall"], "freefall_not_recorded"),
        ({"place": True}, ["venue"], "venue_not_listed"),
    ],
)
def test_nothing_unrecorded_or_private_is_shared(
    api: Api, fields: dict[str, Any], shares: list[str], expected: str
) -> None:
    owner, _ = api.person()
    if fields.pop("place", False):
        place = api.ok("POST", "/places", owner, {"name": "Farm strip", "country": "PT"}, 201)  # fmt: skip
        fields["place_id"] = place["id"]
    refused = api.publish(owner, api.jump(owner, **fields), shares=shares)
    assert (refused.status_code, refused.json()) == (422, {"detail": expected})


def test_who_may_publish(api: Api) -> None:
    nobody = api.accounts.session()
    jump = api.jump(nobody)
    assert api.publish(nobody, jump).json() == {"detail": "profile_required"}

    owner, handle = api.person()
    other, _ = api.person()
    mine = api.jump(owner)
    assert api.publish(other, mine).json() == NOT_FOUND  # someone else's jump
    assert api.publish(owner, {**mine, "version": 9}).json() == {"detail": "edit_conflict"}  # fmt: skip
    long = api.publish(owner, mine, caption="x" * 281)
    assert long.json() == {"detail": "caption_too_long"}
    bad_link = api.publish(owner, mine, link="javascript:alert(1)")
    assert bad_link.json() == {"detail": "link_invalid"}

    api.ok(
        "PUT", f"/social/profiles/{handle}/moderation", api.reviewer,
        {"hidden": False, "publishing_restricted": True, "reason": "Spam posts."},
        status=204,
    )  # fmt: skip
    assert api.publish(owner, mine).json() == {"detail": "publishing_restricted"}

    unverified = api.accounts.session(verified=False)
    response = api.call("POST", f"/me/jumps/{uuid.uuid7()}/post", unverified, {"jump_version": 1, "audience": "public"})  # fmt: skip
    assert response.status_code == 403


def test_a_hidden_profile_hides_its_posts(api: Api) -> None:
    owner, handle = api.person()
    post = api.published(owner, api.jump(owner))
    api.ok(
        "PUT", f"/social/profiles/{handle}/moderation", api.reviewer,
        {"hidden": True, "publishing_restricted": False, "reason": "Spam."},
        status=204,
    )  # fmt: skip
    assert api.call("GET", f"/posts/{post['id']}", None).json() == NOT_FOUND
    assert api.ok("GET", f"/posts/{post['id']}", owner)["is_owner"] is True
    assert api.publish(owner, api.jump(owner)).json() == {"detail": "profile_hidden"}


def test_audience_changes_and_unpublishing(api: Api) -> None:
    owner, handle = api.person()
    post = api.published(owner, api.jump(owner))
    audience = f"/me/posts/{post['id']}/audience"

    api.ok("PUT", audience, owner, {"audience": "followers", "version": 1}, status=204)
    assert api.call("GET", f"/posts/{post['id']}", None).json() == NOT_FOUND
    stale = api.call("PUT", audience, owner, {"audience": "public", "version": 1})
    assert stale.json() == {"detail": "edit_conflict"}
    other, _ = api.person()
    assert api.call("PUT", audience, other, {"audience": "public", "version": 2}).json() == NOT_FOUND  # fmt: skip
    api.ok("PUT", audience, owner, {"audience": "public", "version": 2}, status=204)
    assert api.ok("GET", f"/posts/{post['id']}", None)["audience"] == "public"

    assert api.call("DELETE", f"/me/posts/{post['id']}", other).json() == NOT_FOUND
    api.ok("DELETE", f"/me/posts/{post['id']}?version=3", owner, status=204)
    assert api.call("GET", f"/posts/{post['id']}", owner).json() == NOT_FOUND
    kinds = [e["kind"] for e in api.events(owner, post["jump_id"])]
    assert kinds[-3:] == ["post_audience", "post_audience", "post_unpublished"]
    # Unpublishing keeps the private jump.
    assert api.ok("GET", f"/jumps/{post['jump_id']}", owner)["jump"]["id"] == post["jump_id"]  # fmt: skip


def test_a_person_lists_newest_publication_first(api: Api) -> None:
    owner, handle = api.person()
    # Activity dates in the opposite order to publication.
    first = api.published(owner, api.jump(owner, jumped_on="2026-10-20"))
    second = api.published(owner, api.jump(owner, jumped_on="2026-09-01"))
    page = api.ok("GET", f"/people/{handle}/posts", None)
    assert [p["id"] for p in page["items"]] == [second["id"], first["id"]]
    older = api.ok("GET", f"/people/{handle}/posts", None, before=second["id"])
    assert [p["id"] for p in older["items"]] == [first["id"]]
    assert page["next_before"] is None


def test_post_reports_reach_reviewers_who_can_remove_the_post(api: Api) -> None:
    owner, handle = api.person()
    reporter, _ = api.person()
    post = api.published(owner, api.jump(owner), caption="Buy my rig!!")
    path = f"/posts/{post['id']}/reports"

    first = api.call("POST", path, reporter, {"reason": "spam", "note": "Advert."})
    assert first.status_code == 202
    assert api.call("POST", path, reporter, {"reason": "spam"}).status_code == 202
    assert api.call("POST", path, owner, {"reason": "spam"}).json() == {"detail": "report_self"}  # fmt: skip
    # A profile report by the same person is a separate report.
    api.ok("POST", f"/people/{handle}/reports", reporter, {"reason": "spam"}, status=202)  # fmt: skip

    open_ = [r for r in api.ok("GET", "/social/reports", api.reviewer) if r["target"]["handle"] == handle]  # fmt: skip
    assert len(open_) == 2
    about_post = next(r for r in open_ if r["post_id"] == post["id"])
    about_profile = next(r for r in open_ if r["post_id"] is None)
    assert about_post["post_live"] is True
    assert about_post["snapshot"]["post"]["caption"] == "Buy my rig!!"

    wrong = api.call(
        "POST", f"/social/reports/{about_profile['id']}/decision", api.reviewer,
        {"decision": "remove_post", "reason": "Advert."},
    )  # fmt: skip
    assert wrong.json() == {"detail": "decision_invalid"}
    decided = api.ok(
        "POST", f"/social/reports/{about_post['id']}/decision", api.reviewer,
        {"decision": "remove_post", "reason": "Advertising is not allowed."},
    )  # fmt: skip
    assert decided["post_live"] is False and decided["status"] == "closed"
    assert api.call("GET", f"/posts/{post['id']}", owner).json() == NOT_FOUND
    removed = api.events(owner, post["jump_id"])[-1]
    assert removed["kind"] == "post_removed"
    assert removed["detail"] == {"reason": "Advertising is not allowed."}
    assert "Advert." not in json.dumps(removed)  # the reporter's note stays private


# -- #158 following feed and dropzone activity ------------------------------------------


def _ids(page: dict[str, Any]) -> list[str]:
    return [p["id"] for p in page["items"]]


def test_the_feed_holds_only_followed_peoples_readable_posts(api: Api) -> None:
    me, followed, pending, stranger = api.person(), api.person(), api.person(), api.person()  # fmt: skip
    api.connected(me, followed)
    assert api.follow(me[0], pending[1]) == "requested"
    older = api.published(followed[0], api.jump(followed[0]), audience="followers")
    newer = api.published(followed[0], api.jump(followed[0], jumped_on="2026-01-02"))
    api.published(pending[0], api.jump(pending[0]))
    api.published(stranger[0], api.jump(stranger[0]))
    api.published(me[0], api.jump(me[0]))

    # Newest publication first, whatever the activity dates; nothing else mixed in.
    feed = api.ok("GET", "/me/feed", me[0])
    assert _ids(feed) == [newer["id"], older["id"]] and feed["next_before"] is None
    assert feed["items"][0]["jumped_on"] == "2026-01-02"
    assert _ids(api.ok("GET", "/me/feed", me[0], before=newer["id"])) == [older["id"]]
    assert api.call("GET", "/me/feed").status_code == 401

    # Unpublishing, narrowing nothing, removal of approval and blocks all apply.
    api.ok("DELETE", f"/me/posts/{newer['id']}", followed[0], status=204)
    assert _ids(api.ok("GET", "/me/feed", me[0])) == [older["id"]]
    api.ok("DELETE", f"/me/people/followers/{me[1]}", followed[0], status=204)
    assert api.ok("GET", "/me/feed", me[0])["items"] == []
    api.connected(me, followed)
    assert _ids(api.ok("GET", "/me/feed", me[0])) == [older["id"]]
    api.ok("PUT", f"/people/{me[1]}/block", followed[0], status=204)
    assert api.ok("GET", "/me/feed", me[0])["items"] == []


def test_dropzone_activity_respects_audience_blocks_and_merges(api: Api) -> None:
    owner, follower, blocked, hidden = api.person(), api.person(), api.person(), api.person()  # fmt: skip
    api.connected(follower, owner)
    venue = api.venue()
    at = {"venue_id": venue["id"]}
    public = api.published(owner[0], api.jump(owner[0], **at), shares=["venue"])
    shared = api.published(owner[0], api.jump(owner[0], **at, jumped_on="2026-10-11"), shares=["venue"], audience="followers")  # fmt: skip
    # Logged at the dropzone but the venue was not shared: not dropzone activity.
    api.published(owner[0], api.jump(owner[0], **at, jumped_on="2026-10-12"))
    api.published(hidden[0], api.jump(hidden[0], **at), shares=["venue"])
    api.ok(
        "PUT", f"/social/profiles/{hidden[1]}/moderation", api.reviewer,
        {"hidden": True, "publishing_restricted": False, "reason": "Spam."},
        status=204,
    )  # fmt: skip
    path = f"/venues/{venue['id']}/posts"

    assert _ids(api.ok("GET", path, None)) == [public["id"]]  # guests: public only
    assert _ids(api.ok("GET", path, follower[0])) == [shared["id"], public["id"]]
    api.ok("PUT", f"/people/{owner[1]}/block", blocked[0], status=204)
    assert api.ok("GET", path, blocked[0])["items"] == []

    # A post saved under a venue later merged into this one still shows here.
    dupe = api.venue()
    moved = api.published(owner[0], api.jump(owner[0], venue_id=dupe["id"]), shares=["venue"])  # fmt: skip
    api.ok("POST", f"/directory/venues/{dupe['id']}/merge", api.reviewer, {"into": venue["id"]})  # fmt: skip
    assert moved["id"] in _ids(api.ok("GET", path, None))
    assert api.ok("GET", f"/posts/{moved['id']}", None)["venue"]["id"] == venue["id"]

    # Unknown or unlisted dropzones answer not found.
    assert api.call("GET", f"/venues/{uuid.uuid7()}/posts").json() == NOT_FOUND
