"""#160 cross-user boundary over every parameterised beta route of the real app.

One person (the owner) creates one of everything private. Every route that takes
an id or handle is then called with the owner's identifiers by another verified
user, by a reviewer and anonymously, each write with a valid body (so input
validation cannot answer before the ownership check does). None may succeed or
echo private content, each answer must equal the answer for an id that does not
exist (no existence leak), and the owner's records must be unchanged afterwards.
New routes are covered automatically; a route this test cannot fill, or a write
without a mapped body, fails it until it is mapped.
"""

import json
import re
import uuid
from collections.abc import Iterator
from typing import Any

import httpx2
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.tests.skydiver.support import Accounts

PREFIX = "/api/skydiver/v1"
SECRET = "matrix-private-note"
SOURCE = {"source_url": "https://example.org/dz", "checked_on": "2026-11-01"}

# Public catalogue and per-person keyed routes: nothing private of the owner's to
# reach through them (a saved opportunity is keyed by a public listing id).
NOT_OWNER_SCOPED = (
    "/opportunities/{opportunity_id}",
    "/providers/{provider_id}",
    "/venues/{venue_id}",
    "/saved/{opportunity_id}",
    "/me/people/{relation}",  # the caller's own lists; no other person's id
    "/venues/{venue_id}/posts",  # public listing: checked separately below
)
# Reviewer tools act on public directory/moderation records by design.
REVIEWER_TOOLS = ("/directory/", "/social/")


class World:
    def __init__(self, client: TestClient, accounts: Accounts) -> None:
        self.client, self.accounts = client, accounts

    def call(self, method: str, path: str, secret: str | None, body: Any = None) -> httpx2.Response:  # fmt: skip
        headers = {"authorization": f"Bearer {secret}"} if secret else {}
        return self.client.request(method, PREFIX + path, json=body, headers=headers)

    def ok(self, method: str, path: str, secret: str | None, body: Any = None) -> Any:
        response = self.call(method, path, secret, body)
        assert 200 <= response.status_code < 300, (path, response.text)
        return response.json() if response.content else None


@pytest.fixture(scope="module")
def world() -> Iterator[tuple[World, dict[str, str], str]]:
    accounts = Accounts.create()
    with TestClient(create_app(include_legacy=False)) as client:
        w = World(client, accounts)
        owner = accounts.session()
        reviewer = accounts.session(reviewer=True)
        handle = "m" + uuid.uuid4().hex[:12]
        # Not discoverable: the profile and its follower-only post are private to others.
        w.ok("PUT", "/me/profile", owner, {"handle": handle, "display_name": "Matrix Owner"})  # fmt: skip
        venue = w.ok("POST", "/directory/venues", reviewer, {"name": f"Mx{uuid.uuid4().hex[:8]}", "country": "ES", **SOURCE})  # fmt: skip
        place = w.ok("POST", "/places", owner, {"name": SECRET, "country": "PT"})
        component = w.ok("POST", "/gear/components", owner, {"client_key": str(uuid.uuid4()), "kind": "reserve", "label": SECRET})["component"]  # fmt: skip
        entry = w.ok("POST", f"/gear/components/{component['id']}/service", owner, {"client_key": str(uuid.uuid4()), "kind": "repack", "done_on": "2026-10-01", "performed_by": SECRET})  # fmt: skip
        rig = w.ok("POST", "/gear/rigs", owner, {"client_key": str(uuid.uuid4()), "label": SECRET})  # fmt: skip
        jump = w.ok("POST", "/jumps", owner, {"client_key": str(uuid.uuid4()), "jumped_on": "2026-10-10", "jump_type": "belly", "venue_id": venue["id"], "notes": SECRET})["jump"]  # fmt: skip
        plan = w.ok("POST", "/plans", owner, {"title": SECRET, "starts_on": "2026-12-03", "ends_on": "2026-12-04", "venue_id": venue["id"]})  # fmt: skip
        post = w.ok("POST", f"/me/jumps/{jump['id']}/post", owner, {"jump_version": jump["version"], "audience": "followers", "caption": SECRET})  # fmt: skip
        ids = {
            "place_id": place["id"],
            "component_id": component["id"],
            "entry_id": _id(entry),
            "rig_id": _id(rig),
            "jump_id": jump["id"],
            "plan_id": plan["id"],
            "post_id": post["id"],
            "handle": handle,
            # Reviewer-tool ids: the role check comes before any lookup, so any id
            # shows that members and guests are refused.
            "venue_id": venue["id"],
            "opportunity_id": str(uuid.uuid7()),
            "provider_id": str(uuid.uuid7()),
            "submission_id": str(uuid.uuid7()),
            "report_id": str(uuid.uuid7()),
            # Versions for write bodies: the owner's current ones, so a refusal can
            # only come from ownership, never from a stale version.
            "v_component": str(_record(component)["version"]),
            "v_rig": str(_record(rig)["version"]),
            "v_jump": str(jump["version"]),
            "v_post": str(post["version"]),
        }
        yield w, ids, owner


def _record(created: dict[str, Any]) -> dict[str, Any]:
    """Created bodies wrap the record under one key or return it directly."""
    if "id" in created:
        return created
    (inner,) = (v for v in created.values() if isinstance(v, dict) and "id" in v)
    return dict(inner)


def _id(created: dict[str, Any]) -> str:
    return str(_record(created)["id"])


def _fake(ids: dict[str, str]) -> dict[str, str]:
    """The same parameters pointing at nothing that exists."""
    fake = {k: (v if k.startswith("v_") else str(uuid.uuid7())) for k, v in ids.items()}
    fake["handle"] = "zz" + uuid.uuid4().hex[:10]
    return fake


# A valid body for every parameterised write; reviewer tools get a plausible one
# (their role check answers first).
def _body(method: str, path: str, ids: dict[str, str]) -> dict[str, Any] | None:
    v = {k: int(val) for k, val in ids.items() if k.startswith("v_")}
    bodies: dict[tuple[str, str], dict[str, Any]] = {
        ("PATCH", "/gear/components/{component_id}"): {
            "label": "Changed",
            "version": v["v_component"],
        },  # fmt: skip
        ("POST", "/gear/components/{component_id}/archive"): {
            "archived": True,
            "version": v["v_component"],
        },  # fmt: skip
        ("POST", "/gear/components/{component_id}/rig"): {
            "rig_id": ids["rig_id"],
            "on": "2026-10-02",
            "version": v["v_component"],
        },  # fmt: skip
        ("POST", "/gear/components/{component_id}/service"): {
            "client_key": str(uuid.uuid4()),
            "kind": "repack",
            "done_on": "2026-10-02",
        },  # fmt: skip
        ("PATCH", "/gear/rigs/{rig_id}"): {"label": "Changed", "version": v["v_rig"]},
        ("PATCH", "/jumps/{jump_id}"): {"notes": "changed", "version": v["v_jump"]},
        ("POST", "/me/jumps/{jump_id}/post"): {
            "jump_version": v["v_jump"],
            "audience": "followers",
        },  # fmt: skip
        ("PUT", "/me/posts/{post_id}/audience"): {
            "audience": "public",
            "version": v["v_post"],
        },  # fmt: skip
        ("POST", "/people/{handle}/reports"): {"reason": "spam"},
        ("POST", "/posts/{post_id}/reports"): {"reason": "spam"},
        ("PATCH", "/places/{place_id}"): {"name": "Changed"},
        ("PATCH", "/plans/{plan_id}"): {"title": "Changed"},
        ("PUT", "/social/profiles/{handle}/moderation"): {
            "hidden": True,
            "publishing_restricted": True,
            "reason": "x",
        },  # fmt: skip
        ("POST", "/social/reports/{report_id}/decision"): {"decision": "no_action"},
    }
    if (method, path) in bodies:
        return bodies[(method, path)]
    if path.startswith("/directory/") and method != "GET":
        return {"status": "listed", "into": ids["venue_id"], "of": ids["venue_id"], "name": "x"}  # fmt: skip
    return None


def _routes() -> list[tuple[str, str, bool]]:
    """Every parameterised beta operation, from the app's own OpenAPI document."""
    paths = create_app(include_legacy=False).openapi()["paths"]
    found = []
    for full, operations in sorted(paths.items()):
        path = full.removeprefix(PREFIX)
        if "{" not in path or path in NOT_OWNER_SCOPED:
            continue
        for method, operation in sorted(operations.items()):
            found.append((method.upper(), path, "requestBody" in operation))
    assert len(found) > 30  # a collection failure must not pass silently
    return found


def _fill(path: str, ids: dict[str, str]) -> str:
    names = re.findall(r"{(\w+)}", path)
    missing = [n for n in names if n not in ids]
    assert not missing, f"map {missing} for {path} in the matrix fixture"
    return re.sub(r"{(\w+)}", lambda m: ids[m.group(1)], path)


@pytest.mark.parametrize(("method", "path", "has_body"), _routes())
def test_nobody_else_reaches_the_owners_records(
    world: tuple[World, dict[str, str], str], method: str, path: str, has_body: bool
) -> None:
    w, ids, _ = world
    fake = _fake(ids)
    body, fake_body = _body(method, path, ids), _body(method, path, fake)
    assert (body is not None) == has_body, f"map a valid body for {method} {path}"
    callers: dict[str, str | None] = {
        "other": w.accounts.session(),
        "anonymous": None,
    }
    tool = path.startswith(REVIEWER_TOOLS)
    if not tool:
        # The reviewer role grants nothing over private records.
        callers["reviewer"] = w.accounts.session(reviewer=True)
    for who, secret in callers.items():
        response = w.call(method, _fill(path, ids), secret, body)
        where = (who, method, path, response.status_code, response.text)
        assert SECRET not in response.text, where
        if tool:
            assert response.status_code == (401 if secret is None else 403), where
            continue
        allowed = (401, 404) if secret is None else (403, 404)
        assert response.status_code in allowed, where
        # The owner's real id answers exactly like an id that does not exist.
        absent = w.call(method, _fill(path, fake), secret, fake_body)
        assert (response.status_code, response.json()) == (
            absent.status_code,
            absent.json(),
        ), where


def test_dropzone_activity_shows_no_private_post(
    world: tuple[World, dict[str, str], str],
) -> None:
    """The one public route that lists posts at the owner's dropzone."""
    w, ids, _ = world
    readers = {
        "other": w.accounts.session(),
        "reviewer": w.accounts.session(reviewer=True),
        "anonymous": None,
    }
    for who, secret in readers.items():
        response = w.call("GET", f"/venues/{ids['venue_id']}/posts", secret)
        assert response.status_code == 200, who
        assert ids["post_id"] not in response.text, who
        assert SECRET not in response.text, who


def test_the_owners_records_are_unchanged(
    world: tuple[World, dict[str, str], str],
) -> None:
    w, ids, owner = world
    jump = w.ok("GET", f"/jumps/{ids['jump_id']}", owner)
    assert jump["jump"]["notes"] == SECRET
    assert w.ok("GET", f"/posts/{ids['post_id']}", owner)["caption"] == SECRET
    assert w.ok("GET", f"/gear/components/{ids['component_id']}", owner)
    assert any(p["id"] == ids["plan_id"] for p in w.ok("GET", "/plans", owner))
    assert any(p["id"] == ids["place_id"] for p in w.ok("GET", "/places", owner))
    # Nothing the other callers did created a follow, block or report.
    for relation in ("requests", "followers", "blocked"):
        assert w.ok("GET", f"/me/people/{relation}", owner) == [], relation
    reviewer = w.accounts.session(reviewer=True)
    reports = w.ok("GET", "/social/reports", reviewer)
    assert all(r["target"]["handle"] != ids["handle"] for r in reports)
    assert json.dumps(jump).count(SECRET) == 1
