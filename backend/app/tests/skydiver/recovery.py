"""#161 local recovery drill: seed, snapshot and check a database through the real app.

Run by `scripts/verify.sh recovery` against disposable databases only:

    python -m app.tests.skydiver.recovery seed MANIFEST    # populate via the API
    python -m app.tests.skydiver.recovery snapshot         # per-table count + digest
    python -m app.tests.skydiver.recovery check MANIFEST   # behaviour after restore

The database comes from the usual POSTGRES_* environment. Nothing here touches a
database it was not pointed at, and the manifest holds only disposable test data.
"""

import json
import sys
import uuid
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.db import engine
from app.main import create_app
from app.tests.skydiver.support import Accounts

PREFIX = "/api/skydiver/v1"
SOURCE = {"source_url": "https://example.org/dz", "checked_on": "2026-11-01"}


def _call(client: TestClient, method: str, path: str, secret: str | None, body: Any = None) -> Any:  # fmt: skip
    headers = {"authorization": f"Bearer {secret}"} if secret else {}
    response = client.request(method, PREFIX + path, json=body, headers=headers)
    return response


def _ok(client: TestClient, method: str, path: str, secret: str | None, body: Any = None) -> Any:  # fmt: skip
    response = _call(client, method, path, secret, body)
    assert 200 <= response.status_code < 300, (method, path, response.text)
    return response.json() if response.content else None


def seed(manifest: Path) -> None:
    """One of each kind of record, a follow, a post, a report, a revocation, a deletion."""
    accounts = Accounts.create()
    with TestClient(create_app(include_legacy=False)) as c:
        owner, follower, stranger = (accounts.session() for _ in range(3))
        reviewer = accounts.session(reviewer=True)
        revoked = accounts.session()
        handle, follower_handle = (f"r{uuid.uuid4().hex[:12]}" for _ in range(2))
        _ok(c, "PUT", "/me/profile", owner, {"handle": handle, "display_name": "Recovery Owner", "discoverable": True})  # fmt: skip
        _ok(c, "PUT", "/me/profile", follower, {"handle": follower_handle, "display_name": "Recovery Follower"})  # fmt: skip
        _ok(c, "PUT", f"/people/{handle}/follow", follower)
        _ok(c, "POST", f"/me/people/requests/{follower_handle}/approve", owner)
        venue = _ok(c, "POST", "/directory/venues", reviewer, {"name": f"Rc{uuid.uuid4().hex[:8]}", "country": "ES", **SOURCE})  # fmt: skip
        component = _ok(c, "POST", "/gear/components", owner, {"client_key": str(uuid.uuid4()), "kind": "reserve", "label": "Recovery reserve"})["component"]  # fmt: skip
        _ok(c, "POST", f"/gear/components/{component['id']}/service", owner, {"client_key": str(uuid.uuid4()), "kind": "repack", "done_on": "2026-10-01"})  # fmt: skip
        _ok(c, "POST", "/places", owner, {"name": "Recovery strip", "country": "PT"})
        kept = _ok(c, "POST", "/jumps", owner, {"client_key": str(uuid.uuid4()), "jumped_on": "2026-10-10", "jump_type": "belly", "venue_id": venue["id"], "notes": "kept note", "component_ids": [component["id"]]})["jump"]  # fmt: skip
        gone = _ok(c, "POST", "/jumps", owner, {"client_key": str(uuid.uuid4()), "jumped_on": "2026-10-11", "jump_type": "angle", "venue_id": venue["id"]})["jump"]  # fmt: skip
        _ok(c, "DELETE", f"/jumps/{gone['id']}?version={gone['version']}", owner)
        _ok(c, "PUT", "/history/baseline", owner, {"prior_jumps": 150, "before_on": "2026-01-01"})  # fmt: skip
        _ok(c, "POST", "/plans", owner, {"title": "Recovery trip", "starts_on": "2026-12-03", "ends_on": "2026-12-04", "venue_id": venue["id"]})  # fmt: skip
        post = _ok(c, "POST", f"/me/jumps/{kept['id']}/post", owner, {"jump_version": kept["version"], "audience": "followers", "shares": ["venue"], "caption": "Recovery caption"})  # fmt: skip
        _call(c, "POST", f"/people/{handle}/reports", follower, {"reason": "spam"})
        _ok(c, "DELETE", "/auth/session", revoked)
        assert _call(c, "GET", "/me/profile", revoked).status_code == 401
    manifest.write_text(
        json.dumps(
            {
                "owner": owner,
                "follower": follower,
                "stranger": stranger,
                "revoked": revoked,
                "handle": handle,
                "kept_jump": kept["id"],
                "deleted_jump": gone["id"],
                "post": post["id"],
                "venue": venue["id"],
            }
        )
    )


def snapshot() -> dict[str, list[Any]]:
    """Row count and an order-independent digest of every table's full content."""
    out: dict[str, list[Any]] = {}
    with engine.connect() as conn:
        tables = conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
                "ORDER BY table_name"
            )
        ).scalars()
        for table in list(tables):
            row = conn.execute(
                text(
                    f"SELECT count(*), md5(coalesce(string_agg(t::text, chr(10) "  # noqa: S608
                    f"ORDER BY t::text), '')) FROM \"{table}\" t"
                )
            ).one()
            out[table] = [row[0], row[1]]
    return out


def check(manifest: Path) -> None:
    """The restored database behaves like the original at backup time."""
    m = json.loads(manifest.read_text())
    with TestClient(create_app(include_legacy=False)) as c:
        own = _ok(c, "GET", f"/jumps/{m['kept_jump']}", m["owner"])
        assert own["jump"]["notes"] == "kept note"
        assert (
            _call(c, "GET", f"/jumps/{m['deleted_jump']}", m["owner"]).status_code
            == 404
        )
        assert _call(c, "GET", "/me/profile", m["revoked"]).status_code == 401
        history = _ok(c, "GET", "/history", m["owner"])
        assert history["baseline"]["prior_jumps"] == 150
        # Audience and follow state survive: the follower reads, a stranger does not.
        assert _ok(c, "GET", f"/posts/{m['post']}", m["follower"])["caption"] == "Recovery caption"  # fmt: skip
        assert _call(c, "GET", f"/posts/{m['post']}", m["stranger"]).status_code == 404
        assert _call(c, "GET", f"/posts/{m['post']}", None).status_code == 404
        venue = _ok(c, "GET", f"/venues/{m['venue']}/posts", m["follower"])
        assert [p["id"] for p in venue["items"]] == [m["post"]]
        # The restored database still accepts writes.
        _ok(c, "PATCH", f"/jumps/{m['kept_jump']}", m["owner"], {"notes": "after restore", "version": own["jump"]["version"]})  # fmt: skip


def main(argv: list[str]) -> None:
    command = argv[1]
    if command == "seed":
        seed(Path(argv[2]))
    elif command == "snapshot":
        json.dump(snapshot(), sys.stdout, indent=1, sort_keys=True)
        sys.stdout.write("\n")
    elif command == "check":
        check(Path(argv[2]))
    else:
        raise SystemExit(f"unknown command {command}")


if __name__ == "__main__":
    main(sys.argv)
