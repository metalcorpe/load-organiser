"""#160 cross-user boundary over every parameterised beta route of the real app.

One person (the owner) creates one of everything private. Every route that takes
an id or handle is then called with the owner's identifiers by another verified
user, by a reviewer and anonymously. None may succeed or echo private content,
and the owner's records must be unchanged afterwards. New routes are covered
automatically; a route this test cannot fill fails it until it is mapped.
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
    "/venues/{venue_id}/posts",  # public listing; readability tested in test_posts
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
        }
        yield w, ids, owner


def _id(created: dict[str, Any]) -> str:
    """Created bodies wrap the record under one key or return it directly."""
    if "id" in created:
        return str(created["id"])
    (inner,) = (v for v in created.values() if isinstance(v, dict) and "id" in v)
    return str(inner["id"])


def _routes() -> list[tuple[str, str]]:
    """Every parameterised beta operation, from the app's own OpenAPI document."""
    paths = create_app(include_legacy=False).openapi()["paths"]
    found = []
    for full, operations in sorted(paths.items()):
        path = full.removeprefix(PREFIX)
        if "{" not in path or path in NOT_OWNER_SCOPED:
            continue
        for method in sorted(operations):
            found.append((method.upper(), path))
    assert len(found) > 30  # a collection failure must not pass silently
    return found


def _fill(path: str, ids: dict[str, str]) -> str:
    names = re.findall(r"{(\w+)}", path)
    missing = [n for n in names if n not in ids]
    assert not missing, f"map {missing} for {path} in the matrix fixture"
    return re.sub(r"{(\w+)}", lambda m: ids[m.group(1)], path)


@pytest.mark.parametrize(("method", "path"), _routes())
def test_nobody_else_reaches_the_owners_records(
    world: tuple[World, dict[str, str], str], method: str, path: str
) -> None:
    w, ids, _ = world
    target = _fill(path, ids)
    body: dict[str, Any] | None = {} if method in ("POST", "PUT", "PATCH") else None
    other = w.accounts.session()
    reviewer = w.accounts.session(reviewer=True)
    callers: dict[str, str | None] = {"other": other, "anonymous": None}
    if not path.startswith(REVIEWER_TOOLS):
        # The reviewer role grants nothing over private records.
        callers["reviewer"] = reviewer
    for who, secret in callers.items():
        response = w.call(method, target, secret, body)
        assert not 200 <= response.status_code < 300, (
            who,
            method,
            target,
            response.text,
        )
        assert response.status_code in (401, 403, 404, 405, 409, 422), (
            who,
            response.status_code,
        )
        assert SECRET not in response.text, (who, method, target)


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
    assert json.dumps(jump).count(SECRET) == 1
