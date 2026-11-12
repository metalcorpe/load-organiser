"""#161 local recovery drill: seed, snapshot and check a database through the real app.

Run by `scripts/verify.sh recovery` against disposable databases only:

    python -m app.tests.skydiver.recovery seed MANIFEST    # populate via the API
    python -m app.tests.skydiver.recovery snapshot [SKIP...]  # per-table count + digest
    python -m app.tests.skydiver.recovery check MANIFEST   # behaviour after restore
    python -m app.tests.skydiver.recovery erase MANIFEST   # deletions after the backup
    python -m app.tests.skydiver.recovery replayed MANIFEST  # restore + ledger replay

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

from app.core.config import settings
from app.core.db import engine
from app.main import create_app
from app.tests.skydiver.support import PASSWORD, Accounts

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
    settings.SKYDIVER_PUBLISHING_OPEN = True  # this drill process only; it seeds a post
    accounts = Accounts.create()
    with TestClient(create_app(include_legacy=False)) as c:
        owner, follower, stranger = (accounts.session() for _ in range(3))
        reviewer = accounts.session(reviewer=True)
        revoked = accounts.session()
        leaver = accounts.session()
        handle, follower_handle, stranger_handle = (f"r{uuid.uuid4().hex[:12]}" for _ in range(3))  # fmt: skip
        _ok(c, "PUT", "/me/profile", owner, {"handle": handle, "display_name": "Recovery Owner", "discoverable": True})  # fmt: skip
        _ok(c, "PUT", "/me/profile", follower, {"handle": follower_handle, "display_name": "Recovery Follower"})  # fmt: skip
        _ok(c, "PUT", "/me/profile", stranger, {"handle": stranger_handle, "display_name": "Recovery Stranger", "discoverable": True})  # fmt: skip
        _ok(c, "PUT", f"/people/{handle}/follow", follower)
        _ok(c, "POST", f"/me/people/requests/{follower_handle}/approve", owner)
        venue = _ok(c, "POST", "/directory/venues", reviewer, {"name": f"Rc{uuid.uuid4().hex[:8]}", "country": "ES", **SOURCE})  # fmt: skip
        component = _ok(c, "POST", "/gear/components", owner, {"client_key": str(uuid.uuid4()), "kind": "reserve", "label": "Recovery reserve"})["component"]  # fmt: skip
        _ok(c, "POST", f"/gear/components/{component['id']}/service", owner, {"client_key": str(uuid.uuid4()), "kind": "repack", "done_on": "2026-10-01"})  # fmt: skip
        place = _ok(c, "POST", "/places", owner, {"name": "Recovery strip", "country": "PT"})  # fmt: skip
        kept = _ok(c, "POST", "/jumps", owner, {"client_key": str(uuid.uuid4()), "jumped_on": "2026-10-10", "jump_type": "belly", "venue_id": venue["id"], "notes": "kept note", "component_ids": [component["id"]]})["jump"]  # fmt: skip
        gone = _ok(c, "POST", "/jumps", owner, {"client_key": str(uuid.uuid4()), "jumped_on": "2026-10-11", "jump_type": "angle", "venue_id": venue["id"]})["jump"]  # fmt: skip
        _ok(c, "DELETE", f"/jumps/{gone['id']}?version={gone['version']}", owner)
        # Removed and set again before the backup: a replay must not remove it again.
        first = _ok(c, "PUT", "/history/baseline", owner, {"prior_jumps": 150, "before_on": "2026-01-01"})  # fmt: skip
        _ok(c, "DELETE", f"/history/baseline?version={first['baseline']['version']}", owner)  # fmt: skip
        _ok(c, "PUT", "/history/baseline", owner, {"prior_jumps": 150, "before_on": "2026-01-01"})  # fmt: skip
        _ok(c, "PUT", "/me/licence", owner, {"licence": "b"})
        later = _ok(c, "POST", "/jumps", owner, {"client_key": str(uuid.uuid4()), "jumped_on": "2026-10-13", "jump_type": "belly", "venue_id": venue["id"]})["jump"]  # fmt: skip
        plan = _ok(c, "POST", "/plans", owner, {"title": "Recovery trip", "starts_on": "2026-12-03", "ends_on": "2026-12-04", "venue_id": venue["id"]})  # fmt: skip
        post = _ok(c, "POST", f"/me/jumps/{kept['id']}/post", owner, {"jump_version": kept["version"], "audience": "followers", "shares": ["venue"], "caption": "Recovery caption"})  # fmt: skip
        _ok(c, "POST", f"/people/{handle}/reports", follower, {"reason": "spam"})
        _ok(c, "POST", "/jumps", leaver, {"client_key": str(uuid.uuid4()), "jumped_on": "2026-10-12", "jump_type": "belly", "venue_id": venue["id"], "notes": "leaver note"})  # fmt: skip
        _ok(c, "DELETE", "/auth/session", revoked)
        # Before the backup: a new password (kept by a replay) and a hidden profile.
        _ok(c, "POST", "/auth/password", follower, {"current_password": PASSWORD, "new_password": SEED_PASSWORD})  # fmt: skip
        _ok(c, "PUT", f"/social/profiles/{stranger_handle}/moderation", reviewer, {"hidden": True, "publishing_restricted": False, "reason": "Drill."})  # fmt: skip
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
                "follower_handle": follower_handle,
                "reviewer": reviewer,
                "later_jump": later["id"],
                "follower_account": _account(accounts, follower),
                "stranger_handle": stranger_handle,
                "component": component["id"],
                "place": place["id"],
                "plan": plan["id"],
                "leaver": leaver,
                "owner_account": _account(accounts, owner),
                "owner_person": _ok(c, "GET", "/auth/session", owner)["person_id"],
                "stranger_person": _ok(c, "GET", "/auth/session", stranger)[
                    "person_id"
                ],  # fmt: skip
                "leaver_account": _account(accounts, leaver),
                "leaver_person": _ok(c, "GET", "/auth/session", leaver)["person_id"],
            }
        )
    )


def _account(accounts: Accounts, secret: str) -> str:
    return str(accounts.service.current_viewer(secret=secret).account_id)


def snapshot() -> dict[str, list[Any]]:
    """Row count and an order-independent digest of every table's full content.

    The drill seeds no submissions. If it ever seeds one from the leaver, replaying
    the deletion stamps `skydiver_submission.author_removed_at` with the replay time,
    so the restored row legitimately differs from the source: skip that column.
    """
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


# Tables the seed must populate; an empty one means the drill compared nothing.
SEEDED = (
    "skydiver_jump",
    "skydiver_jump_post",
    "skydiver_follow",
    "skydiver_session",
    "skydiver_social_report",
    "skydiver_component",
    "skydiver_jump_baseline",
    "skydiver_jumper_licence",
)


def seeded(snapshot_file: Path) -> None:
    counts = {t: v[0] for t, v in json.loads(snapshot_file.read_text()).items()}
    empty = [t for t in SEEDED if counts.get(t, 0) == 0]
    assert not empty, f"seeded tables are empty: {empty}"


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
        assert history["currency"]["licence"] == "b"
        # Audience and follow state survive: the follower reads, a stranger does not.
        assert _ok(c, "GET", f"/posts/{m['post']}", m["follower"])["caption"] == "Recovery caption"  # fmt: skip
        assert _call(c, "GET", f"/posts/{m['post']}", m["stranger"]).status_code == 404
        assert _call(c, "GET", f"/posts/{m['post']}", None).status_code == 404
        venue = _ok(c, "GET", f"/venues/{m['venue']}/posts", m["follower"])
        assert [p["id"] for p in venue["items"]] == [m["post"]]
        # The restored database still accepts writes.
        _ok(c, "PATCH", f"/jumps/{m['kept_jump']}", m["owner"], {"notes": "after restore", "version": own["jump"]["version"]})  # fmt: skip


NEW_PASSWORD = "after the backup 2026"
SEED_PASSWORD = "before the backup 2026"


def erase(manifest: Path) -> None:
    """After the backup: deletions and revocations the ledger must carry over."""
    m = json.loads(manifest.read_text())
    with TestClient(create_app(include_legacy=False)) as c:
        owner = m["owner"]
        _ok(c, "DELETE", f"/me/posts/{m['post']}", owner)
        _ok(c, "DELETE", f"/me/people/followers/{m['follower_handle']}", owner)
        reviewer = m["reviewer"]
        _ok(c, "PUT", f"/social/profiles/{m['stranger_handle']}/moderation", reviewer, {"hidden": False, "publishing_restricted": False, "reason": "Drill."})  # fmt: skip
        _ok(c, "PUT", f"/social/profiles/{m['follower_handle']}/moderation", reviewer, {"hidden": True, "publishing_restricted": True, "reason": "Drill."})  # fmt: skip
        _ok(c, "PUT", f"/people/{m['stranger_handle']}/block", owner)
        later = _ok(c, "GET", f"/jumps/{m['later_jump']}", owner)["jump"]
        _ok(c, "DELETE", f"/jumps/{m['later_jump']}?version={later['version']}", owner)
        # The component stops being used, then goes; the restored copy still links it.
        jump = _ok(c, "GET", f"/jumps/{m['kept_jump']}", owner)["jump"]
        _ok(c, "PATCH", f"/jumps/{m['kept_jump']}", owner, {"component_ids": [], "version": jump["version"]})  # fmt: skip
        component = _ok(c, "GET", f"/gear/components/{m['component']}", owner)["component"]  # fmt: skip
        _ok(c, "DELETE", f"/gear/components/{m['component']}?version={component['version']}", owner)  # fmt: skip
        _ok(c, "DELETE", f"/places/{m['place']}", owner)
        _ok(c, "DELETE", f"/plans/{m['plan']}", owner)
        _ok(c, "PUT", "/me/licence", owner, {"licence": "none"})  # deletes its row
        profile = _ok(c, "GET", "/me/profile", owner)
        _ok(c, "PUT", "/me/profile", owner, {"handle": profile["handle"], "display_name": profile["display_name"], "discoverable": False, "version": profile["version"]})  # fmt: skip
        _ok(c, "POST", "/auth/password", owner, {"current_password": PASSWORD, "new_password": NEW_PASSWORD})  # fmt: skip
        _ok(c, "POST", "/auth/account/deletion", m["leaver"], {"password": PASSWORD})


def _scalar(sql: str, **params: Any) -> Any:
    with engine.connect() as conn:
        return conn.execute(text(sql), params).scalar_one()


def replayed(manifest: Path) -> None:
    """The restored database after the ledger replay: nothing erased came back."""
    m = json.loads(manifest.read_text())
    with TestClient(create_app(include_legacy=False)) as c:
        # Every session issued before the restore is refused.
        for who in ("owner", "follower", "stranger"):
            assert _call(c, "GET", "/auth/session", m[who]).status_code == 401, who
        assert _scalar("SELECT count(*) FROM skydiver_session WHERE revoked_at IS NULL") == 0  # fmt: skip
        assert _scalar("SELECT count(*) FROM skydiver_account_token") == 0
        # The password replaced after the backup no longer works; the newer one is
        # unknown to the restored copy, so the owner resets it.
        email = _scalar('SELECT email FROM "user" WHERE id = :id', id=m["owner_account"])  # fmt: skip
        for password in (PASSWORD, NEW_PASSWORD):
            login = c.post(PREFIX + "/auth/sessions", json={"email": email, "password": password})  # fmt: skip
            assert login.status_code in (401, 422), (password, login.text)
        # The account deleted after the backup is gone with everything it owned.
        assert _scalar('SELECT count(*) FROM "user" WHERE id = :id', id=m["leaver_account"]) == 0  # fmt: skip
        assert _scalar("SELECT count(*) FROM skydiver_jump WHERE owner_person_id = :p", p=m["leaver_person"]) == 0  # fmt: skip
        # Unpublished, removed and deleted records stay gone; the block holds.
        assert _call(c, "GET", f"/posts/{m['post']}", None).status_code == 404
        assert _scalar("SELECT count(*) FROM skydiver_jump_post WHERE id = :id", id=m["post"]) == 0  # fmt: skip
        assert _scalar("SELECT count(*) FROM skydiver_follow WHERE followee_person_id = :p", p=m["owner_person"]) == 0  # fmt: skip
        assert _scalar("SELECT count(*) FROM skydiver_block WHERE blocker_person_id = :a AND blocked_person_id = :b", a=m["owner_person"], b=m["stranger_person"]) == 1  # fmt: skip
        for table, key in (("skydiver_component", "component"), ("skydiver_provisional_place", "place"), ("skydiver_visit_plan", "plan")):  # fmt: skip
            assert (
                _scalar(f"SELECT count(*) FROM {table} WHERE id = :id", id=m[key]) == 0
            ), table  # noqa: S608
        # The licence (set before the backup) was cleared after it: it stays cleared.
        assert _scalar("SELECT count(*) FROM skydiver_jumper_licence WHERE owner_person_id = :p", p=m["owner_person"]) == 0  # fmt: skip
        assert _scalar("SELECT discoverable FROM skydiver_profile WHERE person_id = :p", p=m["owner_person"]) is False  # fmt: skip
        # Moderation after the backup, both ways: set and cleared.
        assert _scalar("SELECT hidden_at IS NULL FROM skydiver_profile WHERE person_id = :p", p=m["stranger_person"]) is True  # fmt: skip
        hidden, restricted = (_scalar(f"SELECT {c} IS NOT NULL FROM skydiver_profile p JOIN skydiver_person s ON s.id = p.person_id WHERE s.account_id = :a", a=m["follower_account"]) for c in ("hidden_at", "publishing_restricted_at"))  # fmt: skip  # noqa: S608
        assert hidden is True and restricted is True
        assert _scalar("SELECT count(*) FROM skydiver_jump WHERE id = :id", id=m["later_jump"]) == 0  # fmt: skip
        # Changes from before the backup are not replayed again: the baseline set
        # again after its removal stays, and the password changed then still works.
        assert _scalar("SELECT prior_jumps FROM skydiver_jump_baseline WHERE owner_person_id = :p", p=m["owner_person"]) == 150  # fmt: skip
        follower_email = _scalar('SELECT email FROM "user" WHERE id = :id', id=m["follower_account"])  # fmt: skip
        signed_in = c.post(PREFIX + "/auth/sessions", json={"email": follower_email, "password": SEED_PASSWORD})  # fmt: skip
        assert signed_in.status_code in (200, 201), signed_in.text
        # Signed out again, so that the drill's own session is not left live.
        _ok(c, "DELETE", "/auth/session", signed_in.json()["session_secret"])
        # What was not erased is still there: the kept jump, without the component.
        assert _scalar("SELECT notes FROM skydiver_jump WHERE id = :id", id=m["kept_jump"]) == "after restore"  # fmt: skip
        assert _scalar("SELECT count(*) FROM skydiver_jump_component WHERE jump_id = :id", id=m["kept_jump"]) == 0  # fmt: skip


def main(argv: list[str]) -> None:
    command = argv[1]
    if command == "seed":
        seed(Path(argv[2]))
    elif command == "snapshot":
        tables = {t: v for t, v in snapshot().items() if t not in argv[2:]}
        json.dump(tables, sys.stdout, indent=1, sort_keys=True)
        sys.stdout.write("\n")
    elif command == "seeded":
        seeded(Path(argv[2]))
    elif command == "check":
        check(Path(argv[2]))
    elif command == "erase":
        erase(Path(argv[2]))
    elif command == "replayed":
        replayed(Path(argv[2]))
    else:
        raise SystemExit(f"unknown command {command}")


if __name__ == "__main__":
    main(sys.argv)
