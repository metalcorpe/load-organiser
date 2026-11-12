"""Erasure ledger recording and validation (architecture A9).

Replay against a restored backup is exercised by the recovery drill
(`scripts/verify.sh recovery`), which needs its own databases: `apply` revokes
every session, so it never runs against the shared test database here.
"""

import json
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx2
import pytest
from fastapi.testclient import TestClient
from pwdlib.hashers.bcrypt import BcryptHasher
from sqlalchemy import text

from app.core.db import engine
from app.main import create_app
from app.skydiver.recovery import ledger
from app.tests.skydiver.support import PASSWORD, Accounts, random_ip

PREFIX = "/api/skydiver/v1"


class Api:
    def __init__(self, client: TestClient, accounts: Accounts) -> None:
        self.client, self.accounts = client, accounts

    def call(self, method: str, path: str, secret: str | None, body: Any = None) -> httpx2.Response:  # fmt: skip
        headers = {"authorization": f"Bearer {secret}"} if secret else {}
        return self.client.request(method, PREFIX + path, json=body, headers=headers)

    def ok(self, method: str, path: str, secret: str | None, body: Any = None) -> Any:
        response = self.call(method, path, secret, body)
        assert 200 <= response.status_code < 300, (method, path, response.text)
        return response.json() if response.content else None


@pytest.fixture(scope="module")
def api() -> Iterator[Api]:
    with TestClient(create_app(include_legacy=False)) as client:
        yield Api(client, Accounts.create())


def _since(start: datetime) -> list[dict[str, Any]]:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT action, table_name, row_key, row_values FROM skydiver_erasure_ledger "
                "WHERE recorded_at >= :start ORDER BY recorded_at, id"
            ),
            {"start": start},
        ).all()
    return [{"action": r[0], "table": r[1], "key": r[2], "values": r[3]} for r in rows]


def _now() -> datetime:
    with engine.connect() as conn:
        return conn.execute(text("SELECT clock_timestamp()")).scalar_one()  # type: ignore[no-any-return]


def _mine(entries: list[dict[str, Any]], *ids: str) -> list[dict[str, Any]]:
    """Entries naming one of these ids (other tests may write concurrently)."""
    return [e for e in entries if set(map(str, e["key"].values())) & set(ids)]


def test_triggers_match_the_replay_map() -> None:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT c.relname, t.tgtype, encode(t.tgargs, 'escape') "
                "FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid "
                "JOIN pg_proc p ON p.oid = t.tgfoid "
                "WHERE p.proname = 'skydiver_erasure_record' AND NOT t.tgisinternal"
            )
        ).all()
    found: dict[str, dict[str, Any]] = {}
    for table, kind, raw in rows:
        args = raw.split("\\000")[:-1]
        spec = found.setdefault(table, {"keys": None, "watched": (), "inserts": False})
        spec["keys"] = tuple(args[0].split(","))
        if kind & 4:  # INSERT
            spec["inserts"] = True
        if kind & 16:  # UPDATE
            spec["watched"] = tuple(args[1].split(","))
    expected = {
        t: {"keys": r.keys, "watched": r.watched, "inserts": bool(r.inserts)}
        for t, r in ledger.REPLAY.items()
    }
    assert found == expected


def test_clearing_a_licence_records_its_owner_key_only(api: Api) -> None:
    owner = api.accounts.session()
    person = api.ok("GET", "/auth/session", owner)["person_id"]
    start = _now()
    api.ok("PUT", "/me/licence", owner, {"licence": "b"})
    api.ok("PUT", "/me/licence", owner, {"licence": "c"})
    assert _mine(_since(start), person) == []  # setting or changing records nothing
    api.ok("PUT", "/me/licence", owner, {"licence": "none"})
    assert _mine(_since(start), person) == [
        {
            "action": "delete",
            "table": "skydiver_jumper_licence",
            "key": {"owner_person_id": person},
            "values": None,
        }
    ]


def test_clearing_an_exit_weight_records_its_owner_key_only(api: Api) -> None:
    owner = api.accounts.session()
    person = api.ok("GET", "/auth/session", owner)["person_id"]
    start = _now()
    api.ok("PUT", "/me/exit-weight", owner, {"value": 81.6, "unit": "kg"})
    api.ok("PUT", "/me/exit-weight", owner, {"value": 180, "unit": "lb"})
    assert _mine(_since(start), person) == []  # setting or changing records nothing
    api.ok("PUT", "/me/exit-weight", owner, {"value": None, "unit": "lb"})
    entries = _mine(_since(start), person)
    assert entries == [
        {
            "action": "delete",
            "table": "skydiver_exit_weight",
            "key": {"owner_person_id": person},
            "values": None,
        }
    ]
    # Ids and times only: the weight itself is never in the ledger.
    assert "81647" not in json.dumps(entries) and "81600" not in json.dumps(entries)
    # The chosen unit is a preference and stays.
    assert api.ok("GET", "/me/exit-weight", owner) == {
        "exit_weight": None,
        "unit": "lb",
    }


def test_deletions_record_keys_without_content(api: Api) -> None:
    owner = api.accounts.session()
    start = _now()
    place = api.ok("POST", "/places", owner, {"name": "Secret field", "country": "PT"})
    jump = api.ok("POST", "/jumps", owner, {"client_key": str(uuid.uuid4()), "jumped_on": "2026-10-01", "jump_type": "belly", "place_id": place["id"], "notes": "private ledger note"})["jump"]  # fmt: skip
    assert (
        _mine(_since(start), jump["id"], place["id"]) == []
    )  # creating records nothing

    api.ok("DELETE", f"/jumps/{jump['id']}?version={jump['version']}", owner)
    api.ok("DELETE", f"/places/{place['id']}", owner)

    entries = _mine(_since(start), jump["id"], place["id"])
    assert entries == [
        {
            "action": "delete",
            "table": "skydiver_jump",
            "key": {"id": jump["id"]},
            "values": None,
        },  # fmt: skip
        {
            "action": "delete",
            "table": "skydiver_provisional_place",
            "key": {"id": place["id"]},
            "values": None,
        },  # fmt: skip
    ]
    assert "private ledger note" not in json.dumps(_since(start))
    assert "Secret field" not in json.dumps(_since(start))


def test_visibility_changes_record_only_the_changed_watched_values(api: Api) -> None:
    owner, other = api.accounts.session(), api.accounts.session()
    person = api.ok("GET", "/auth/session", owner)["person_id"]
    other_person = api.ok("GET", "/auth/session", other)["person_id"]
    handle, other_handle = (f"l{uuid.uuid4().hex[:12]}" for _ in range(2))
    profile = api.ok("PUT", "/me/profile", owner, {"handle": handle, "display_name": "Ledger", "discoverable": True})  # fmt: skip
    api.ok("PUT", "/me/profile", other, {"handle": other_handle, "display_name": "Other", "discoverable": True})  # fmt: skip
    start = _now()

    # A display-name edit is not a revocation: nothing recorded.
    profile = api.ok("PUT", "/me/profile", owner, {"handle": handle, "display_name": "Renamed", "discoverable": True, "version": profile["version"]})  # fmt: skip
    assert _mine(_since(start), person) == []

    api.ok("PUT", "/me/profile", owner, {"handle": handle, "display_name": "Renamed", "discoverable": False, "version": profile["version"]})  # fmt: skip
    api.ok("PUT", f"/people/{other_handle}/block", owner)
    entries = _mine(_since(start), person)
    assert entries[0] == {"action": "update", "table": "skydiver_profile", "key": {"person_id": person}, "values": {"discoverable": False}}  # fmt: skip
    block = entries[1]
    assert (block["action"], block["table"]) == ("insert", "skydiver_block")
    assert block["key"] == {"blocker_person_id": person, "blocked_person_id": other_person}  # fmt: skip
    assert len(entries) == 2


def test_a_new_password_is_recorded_but_a_rehash_is_not(api: Api) -> None:
    email = f"ledger-{uuid.uuid4().hex[:10]}@example.com"
    service = api.accounts.service
    service.register(email=email, password=PASSWORD, display_name=None, client_ip=random_ip())  # fmt: skip
    service.confirm_email(token=api.accounts.outbox.token_for(email))
    secret = str(service.login(email=email, password=PASSWORD, client_ip=random_ip()).secret)  # fmt: skip
    account = str(service.current_viewer(secret=secret).account_id)

    # An outdated encoding of the same password is replaced at sign-in.
    bcrypt = BcryptHasher().hash(PASSWORD)
    with engine.begin() as conn:
        conn.execute(text('UPDATE "user" SET hashed_password = :h WHERE id = :id'), {"h": bcrypt, "id": account})  # fmt: skip
    start = _now()
    secret = str(service.login(email=email, password=PASSWORD, client_ip=random_ip()).secret)  # fmt: skip
    with engine.connect() as conn:
        rehashed = conn.execute(text('SELECT hashed_password FROM "user" WHERE id = :id'), {"id": account}).scalar_one()  # fmt: skip
    assert rehashed != bcrypt
    assert _mine(_since(start), account) == []

    api.ok("POST", "/auth/password", secret, {"current_password": PASSWORD, "new_password": "a different one 2026"})  # fmt: skip
    assert _mine(_since(start), account) == [
        {"action": "password", "table": "user", "key": {"id": account}, "values": None}
    ]


def test_export_writes_entries_that_read_back(tmp_path: Path, api: Api) -> None:
    owner = api.accounts.session()
    plan = api.ok("POST", "/plans", owner, {"title": "Export", "starts_on": "2026-12-03", "ends_on": "2026-12-04"})  # fmt: skip
    api.ok("DELETE", f"/plans/{plan['id']}", owner)
    out = tmp_path / "ledger.jsonl"
    count = ledger.export(engine, out)
    entries = ledger.read(out)
    assert count == len(entries) > 0
    assert any(e.key == {"id": plan["id"]} for e in entries)
    assert not (tmp_path / "ledger.jsonl.partial").exists()


def test_prune_keeps_recent_entries() -> None:
    old, recent = uuid.uuid4(), uuid.uuid4()
    with engine.begin() as conn:
        for entry, age in ((old, 40), (recent, 1)):
            conn.execute(
                text(
                    "INSERT INTO skydiver_erasure_ledger (id, recorded_at, action, table_name, row_key) "  # fmt: skip
                    "VALUES (:id, :at, 'delete', 'skydiver_visit_plan', jsonb_build_object('id', gen_random_uuid()))"  # fmt: skip
                ),
                {"id": entry, "at": datetime.now(UTC) - timedelta(days=age)},
            )
    assert ledger.prune(engine, 30) >= 1
    with engine.connect() as conn:
        left = set(conn.execute(text("SELECT id FROM skydiver_erasure_ledger WHERE id IN (:a, :b)"), {"a": old, "b": recent}).scalars())  # fmt: skip
    assert left == {recent}
    with pytest.raises(ledger.LedgerError):
        ledger.prune(engine, 0)


def test_prune_records_its_cutoff_and_never_moves_it_back() -> None:
    def cutoff() -> datetime:
        with engine.connect() as conn:
            return conn.execute(text("SELECT pruned_before FROM skydiver_erasure_ledger_pruned WHERE id = 1")).scalar_one()  # type: ignore[no-any-return]  # fmt: skip

    now = datetime.now(UTC)
    ledger.prune(engine, 30, now=now)
    assert cutoff() >= now - timedelta(days=30)
    recorded = cutoff()
    ledger.prune(engine, 60, now=now)  # a longer retention does not lower it
    assert cutoff() == recorded


GOOD = {
    "id": str(uuid.uuid4()),
    "recorded_at": "2026-11-07T10:00:00+00:00",
    "action": "delete",
    "table": "skydiver_jump",
    "key": {"id": str(uuid.uuid4())},
    "values": None,
}


@pytest.mark.parametrize(
    "change",
    [
        {"table": "skydiver_venue"},  # not a replayed table
        {"table": "user; DROP TABLE x"},
        {"action": "truncate"},
        {"key": {"owner_person_id": str(uuid.uuid4())}},  # wrong key
        {"action": "update", "values": {"notes": "x"}},  # not a watched column
        {
            "action": "update",
            "table": "skydiver_profile",
            "key": {"person_id": "p"},
            "values": {"bio": "x"},
        },  # fmt: skip
        {"action": "insert", "values": {"id": "x"}},  # inserts only for blocks
        {
            "action": "insert",
            "table": "skydiver_block",
            "key": {"blocker_person_id": "a", "blocked_person_id": "b"},
            "values": {
                "blocker_person_id": "a",
                "blocked_person_id": "b",
                "created_at": "2026-11-07T10:00:00+00:00",
                "extra": 1,
            },
        },  # fmt: skip
        {"action": "password"},  # passwords only for accounts
        {"recorded_at": "2026-11-07T10:00:00"},  # no time zone
        {"id": "not a uuid"},
    ],
)
def test_entries_outside_the_replay_map_are_refused(change: dict[str, Any]) -> None:
    ledger.Entry.parse(GOOD)
    with pytest.raises(ledger.LedgerError):
        ledger.Entry.parse({**GOOD, **change})


def test_copies_that_disagree_are_refused(tmp_path: Path) -> None:
    first, second = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    first.write_text(json.dumps(GOOD) + "\n")
    second.write_text(json.dumps({**GOOD, "key": {"id": str(uuid.uuid4())}}) + "\n")
    entries = [*ledger.read(first), *ledger.read(second)]
    with pytest.raises(ledger.LedgerError):
        ledger._merge(entries)
    assert len(ledger._merge([*ledger.read(first), *ledger.read(first)])) == 1
