"""Logbook import from a spreadsheet over HTTP against the real PostgreSQL store."""

import json
import threading
import time
import uuid
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, date, datetime
from typing import Any

import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session, col, func, select

from app.core.db import engine
from app.skydiver.access.http import AccessDependencies
from app.skydiver.access.policy import Actor
from app.skydiver.directory.api import create_router as create_directory_router
from app.skydiver.directory.service import DirectoryService
from app.skydiver.directory.service import LimitReached as PlaceLimitReached
from app.skydiver.directory.store import sql_directory_store_factory
from app.skydiver.directory.tables import SkydiverProvisionalPlace
from app.skydiver.identity.policy import throttle_key
from app.skydiver.identity.tables import SkydiverThrottleEvent
from app.skydiver.imports.api import IMPORT_RULE, create_router
from app.skydiver.imports.policy import Options
from app.skydiver.imports.service import ImportService, LimitReached, PlaceName
from app.skydiver.imports.store import SqlImportStore, sql_import_store_factory
from app.skydiver.logbook.api import create_router as create_logbook_router
from app.skydiver.logbook.service import LimitReached as JumpLimitReached
from app.skydiver.logbook.service import LogbookService
from app.skydiver.logbook.store import sql_logbook_store_factory
from app.skydiver.logbook.tables import SkydiverJump, SkydiverJumpImport
from app.skydiver.opportunities.service import OpportunityService
from app.skydiver.opportunities.store import sql_listing_store_factory
from app.skydiver.records.api import PASSWORD_HEADER
from app.skydiver.records.api import create_router as create_records_router
from app.skydiver.records.service import RecordsService
from app.skydiver.records.store import sql_records_store_factory
from app.tests.skydiver.support import PASSWORD, Accounts

NOW = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)
SOURCE = {"source_url": "https://example.org/dz", "checked_on": "2026-11-01"}


class Api:
    def __init__(self, client: TestClient, accounts: Accounts, imports: ImportService) -> None:  # fmt: skip
        self.client = client
        self.accounts = accounts
        self.imports = imports
        self.reviewer = accounts.session(reviewer=True)

    def call(self, method: str, path: str, secret: str | None = None, body: Any = None) -> httpx2.Response:  # fmt: skip
        headers = {"authorization": f"Bearer {secret}"} if secret else {}
        return self.client.request(method, f"/api/skydiver/v1{path}", json=body, headers=headers)  # fmt: skip

    def ok(self, method: str, path: str, secret: str, body: Any = None, status: int = 200) -> Any:  # fmt: skip
        response = self.call(method, path, secret, body)
        assert response.status_code == status, response.text
        return response.json() if response.content else None

    def send(
        self, path: str, secret: str | None, raw: bytes, *,
        content_type: str = "text/csv", **params: str,
    ) -> httpx2.Response:  # fmt: skip
        headers = {"content-type": content_type}
        if secret:
            headers["authorization"] = f"Bearer {secret}"
        return self.client.post(
            f"/api/skydiver/v1{path}", content=raw, headers=headers, params=params
        )

    def check(self, secret: str, raw: bytes, **params: str) -> httpx2.Response:
        return self.send("/jumps/import/check", secret, raw, **params)

    def run(self, secret: str, raw: bytes, **params: str) -> httpx2.Response:
        return self.send("/jumps/import", secret, raw, **params)

    def venue(self, name: str, alias: str | None = None, country: str = "ES") -> str:
        body = {"name": name, "country": country, **SOURCE}
        venue = self.ok("POST", "/directory/venues", self.reviewer, body, 201)
        self.ok(
            "POST", f"/directory/venues/{venue['id']}/status", self.reviewer,
            {"status": "listed"},
        )  # fmt: skip
        if alias:
            self.ok(
                "POST", f"/directory/venues/{venue['id']}/aliases", self.reviewer,
                {"name": alias},
            )  # fmt: skip
        return str(venue["id"])

    def jumps(self, secret: str) -> list[dict[str, Any]]:
        page = self.ok("GET", "/jumps?limit=50", secret)
        return list(page["items"])


@pytest.fixture(scope="module")
def api() -> Iterator[Api]:
    accounts = Accounts.create()
    directory = DirectoryService(stores=sql_directory_store_factory(engine), clock=lambda: NOW)  # fmt: skip
    imports = ImportService(stores=sql_import_store_factory(engine), clock=lambda: NOW)
    logbook = LogbookService(stores=sql_logbook_store_factory(engine), clock=lambda: NOW, directory=directory)  # fmt: skip
    records = RecordsService(
        stores=sql_records_store_factory(engine), clock=lambda: NOW, directory=directory,
        opportunities=OpportunityService(stores=sql_listing_store_factory(engine), clock=lambda: NOW),
    )  # fmt: skip
    access = AccessDependencies(lambda: accounts.service)
    app = FastAPI()
    app.include_router(
        create_router(
            service=lambda: imports, identity=lambda: accounts.service, access=access
        )  # fmt: skip
    )
    app.include_router(create_logbook_router(service=lambda: logbook, access=access))
    app.include_router(create_directory_router(service=lambda: directory, access=access))  # fmt: skip
    app.include_router(
        create_records_router(
            service=lambda: records, identity=lambda: accounts.service, access=access,
            client_ip=lambda _: "203.0.113.9",
        )
    )  # fmt: skip
    with TestClient(app) as client:
        yield Api(client, accounts, imports)


def _csv(*rows: str, heading: str = "Date,Jump #,Dropzone,Type,Altitude,Freefall,Notes") -> bytes:  # fmt: skip
    return ("\n".join([heading, *rows]) + "\n").encode()


def _actor(api: Api, secret: str) -> Actor:
    viewer = api.accounts.service.current_viewer(secret=secret)
    return Actor(
        account_id=viewer.account_id, person_id=viewer.person_id,
        email_verified=True, roles=frozenset(),
    )  # fmt: skip


def _count(model: Any, actor: Actor) -> int:
    with Session(engine) as session:
        return int(
            session.execute(
                select(func.count())
                .select_from(model)
                .where(col(model.owner_person_id) == actor.person_id)
            ).scalar_one()
        )


def _bulk(count: int, first: int = 1, place: str = "Bulk field") -> bytes:
    return _csv(
        *(f"2020-01-01,{n},{place},belly,,," for n in range(first, first + count))
    )


def test_check_previews_every_rule_without_writing(api: Api) -> None:
    owner = api.accounts.session()
    actor = _actor(api, owner)
    tag = uuid.uuid4().hex[:8]
    venue = api.venue(f"Ix{tag} Skydive", alias=f"Ix{tag} DZ")
    place = api.ok("POST", "/places", owner, {"name": f"Farm {tag}", "country": "PT"}, 201)  # fmt: skip
    api.ok(
        "POST", "/jumps", owner,
        {"client_key": str(uuid.uuid4()), "jumped_on": "2024-01-01", "jump_type": "belly",
         "venue_id": venue, "jump_number": 50},
        201,
    )  # fmt: skip
    raw = _csv(
        f'12/03/2024,100,ix{tag} dz,FS,"13,500",60,first',  # alias, any case
        f"13/03/2024,101,FARM {tag},Head down,,,",  # own private place
        "14/03/2024,102,New strip,wingsuit,,,",  # a new private place
        "15/03/2024,103,new STRIP,,,,",  # the same new place
        "31/02/2024,104,New strip,,,,",  # not a date
        f"16/03/2024,50,Ix{tag} Skydive,,,,",  # number already in the logbook
        "17/03/2024,101,New strip,,,,",  # number repeated in the file
        "18/03/2024,105,,,,,",  # no place
        "01/12/2026,106,New strip,,,,",  # after today
    )
    before = _count(SkydiverJump, actor)
    preview = api.check(owner, raw, country="PT")
    assert preview.status_code == 200, preview.text
    assert preview.headers["cache-control"] == "no-store"
    p = preview.json()
    assert p["encoding"] == "utf-8"
    # Fields the file has no column for (e.g. aircraft) are null.
    assert {k: v for k, v in p["columns"].items() if v is not None} == {
        "date": 0, "number": 1, "place": 2, "type": 3, "altitude": 4, "freefall": 5,
        "notes": 6,
    }  # fmt: skip
    assert (p["rows_total"], p["rows_ok"], p["room"]) == (9, 4, 1999)
    assert p["new_places"] == ["New strip"]
    assert p["problems_total"] == 5
    assert [(x["row"], x["code"]) for x in p["problems"]] == [
        (5, "jump_date_invalid"),
        (6, "likely_duplicate"),
        (7, "repeated_in_file"),
        (8, "location_required"),
        (9, "jump_date_in_future"),
    ]
    sample = {s["row"]: s for s in p["sample"]}
    assert (
        sample[1]["place"] == f"Ix{tag} Skydive" and sample[1]["place_kind"] == "venue"
    )
    assert (sample[1]["exit_altitude"], sample[1]["altitude_unit"]) == (13500, "ft")
    assert sample[1]["jump_type"] == "belly"
    assert sample[2]["place_kind"] == "place" and sample[2]["place"] == place["name"]
    assert (
        sample[3]["place_kind"] == "new_place" and sample[3]["jump_type"] == "wingsuit"
    )
    assert p["already_imported_at"] is None
    assert _count(SkydiverJump, actor) == before
    assert _count(SkydiverJumpImport, actor) == 0


def test_import_writes_once_and_the_same_file_again_changes_nothing(api: Api) -> None:
    owner = api.accounts.session()
    actor = _actor(api, owner)
    tag = uuid.uuid4().hex[:8]
    venue = api.venue(f"Iy{tag} Skydive")
    raw = _csv(
        f"2024-03-12,1,Iy{tag} Skydive,freefly,4000,,From paper",
        "2024-03-13,2,Olive grove,,,,",
        "2024-03-14,,Olive grove,crw,,,",
    )
    checked = api.check(owner, raw, country="GR").json()
    done = api.run(owner, raw, country="GR", expected=checked["fingerprint"])
    assert done.status_code == 200, done.text
    result = done.json()
    assert result["outcome"] == "imported"
    assert result["item"]["counts"] == {"rows": 3, "jumps": 3, "new_places": 1, "skipped": 0}  # fmt: skip
    items = api.jumps(owner)
    assert len(items) == 3
    first = next(j for j in items if j["jump_number"] == 1)
    assert first["location"] == {
        "kind": "venue", "id": venue, "name": f"Iy{tag} Skydive", "country": "ES",
        "closed": False,
    }  # fmt: skip
    detail = api.ok("GET", f"/jumps/{first['id']}", owner)
    assert detail["jump"]["source"] == "imported"
    assert detail["jump"]["provenance"] == "self_reported"
    assert (detail["jump"]["exit_altitude"], detail["jump"]["altitude_unit"]) == (4000, "ft")  # fmt: skip
    assert detail["jump"]["altitude_datum"] == "unspecified"
    assert detail["jump"]["notes"] == "From paper"
    assert [(e["kind"], e["detail"]) for e in detail["events"]] == [
        ("created", {"source": "imported"})
    ]
    places = api.ok("GET", "/places", owner)
    assert [(p["name"], p["country"]) for p in places] == [("Olive grove", "GR")]

    # The same bytes and choices again: no writes, the original counts.
    again = api.run(owner, raw, country="GR")
    assert again.json() == {**result, "outcome": "already_imported"}
    assert _count(SkydiverJump, actor) == 3
    assert api.check(owner, raw, country="GR").json()["already_imported_at"] is not None
    # Other choices are another import, but every row is now a likely duplicate.
    other = api.run(owner, raw, country="PT")
    assert (other.status_code, other.json()["detail"]) == (422, "nothing_to_import")
    assert _count(SkydiverJump, actor) == 3
    listed = api.ok("GET", "/jumps/imports", owner)
    assert [i["id"] for i in listed] == [result["item"]["id"]]


def test_a_file_or_choice_other_than_the_checked_one_is_refused(api: Api) -> None:
    owner = api.accounts.session()
    raw = _csv("2024-03-12,1,Somewhere,,,,")
    checked = api.check(owner, raw, country="PT").json()["fingerprint"]
    for changed, params in (
        (raw + b"2024-03-13,2,Somewhere,,,,\n", {"country": "PT"}),
        (raw, {"country": "PT", "unit": "m"}),
        (raw, {"country": "PT", "col_notes": "none"}),
    ):
        response = api.run(owner, changed, expected=checked, **params)
        assert (response.status_code, response.json()["detail"]) == (409, "import_changed")  # fmt: skip
    assert api.jumps(owner) == []


def test_new_places_need_a_country(api: Api) -> None:
    owner = api.accounts.session()
    raw = _csv("2024-03-12,1,Hill A,,,,", "2024-03-13,2,Hill B,,,,", "2024-03-14,3,hill a,,,,")  # fmt: skip
    for call in (api.check, api.run):
        response = call(owner, raw)
        assert response.status_code == 422
        assert response.json() == {"detail": "country_required", "names": ["Hill A", "Hill B"]}  # fmt: skip
    bad = api.check(owner, raw, country="XX")
    assert (bad.status_code, bad.json()["detail"]) == (422, "country_invalid")
    assert api.jumps(owner) == []


def test_files_that_cannot_be_read_are_refused(api: Api) -> None:
    owner = api.accounts.session()
    cases = [
        (b"Date,Place\n2024-01-01,A\n", "application/json", 400, "file_unreadable"),
        (b"", "text/csv", 400, "header_required"),
        (b"Place,Type\nA,belly\n", "text/csv", 422, "date_column_required"),
        (b"Date,Place\n" + b"x" * (1024 * 1024), "text/csv", 413, "file_too_large"),
    ]
    for raw, kind, code, detail in cases:
        response = api.send("/jumps/import/check", owner, raw, content_type=kind)
        assert (response.status_code, response.json()["detail"]) == (code, detail)
    mapped = api.check(owner, b"Date,Place\n2024-01-01,A\n", col_place="7")
    assert (mapped.status_code, mapped.json()["detail"]) == (422, "mapping_invalid")


def test_the_jump_limit_refuses_the_whole_import_with_no_writes(api: Api) -> None:
    owner = api.accounts.session()
    actor = _actor(api, owner)
    assert api.run(owner, _bulk(1995), country="PT").json()["outcome"] == "imported"
    assert _count(SkydiverJump, actor) == 1995
    extra = _bulk(10, first=5000, place="Second field")
    preview = api.check(owner, extra, country="PT").json()
    assert (preview["rows_ok"], preview["room"]) == (10, 5)
    places, imports = _count(SkydiverProvisionalPlace, actor), _count(SkydiverJumpImport, actor)  # fmt: skip
    refused = api.run(owner, extra, country="PT")
    assert (refused.status_code, refused.json()["detail"]) == (
        409,
        "jump_limit_reached",
    )
    assert _count(SkydiverJump, actor) == 1995
    assert _count(SkydiverProvisionalPlace, actor) == places
    assert _count(SkydiverJumpImport, actor) == imports


def test_undo_removes_the_imports_jumps_and_unused_places_once(api: Api) -> None:
    owner = api.accounts.session()
    actor = _actor(api, owner)
    raw = _csv(
        "2024-03-12,1,Kept field,,,,",
        "2024-03-13,2,Kept field,,,,",
        "2024-03-14,3,Gone field,,,,",
    )
    item = api.run(owner, raw, country="PT").json()["item"]
    jumps = api.jumps(owner)
    edited = next(j for j in jumps if j["jump_number"] == 1)
    version = api.ok("GET", f"/jumps/{edited['id']}", owner)["jump"]["version"]
    api.ok("PATCH", f"/jumps/{edited['id']}", owner, {"notes": "edited", "version": version})  # fmt: skip
    kept = next(p for p in api.ok("GET", "/places", owner) if p["name"] == "Kept field")
    manual = api.ok(
        "POST", "/jumps", owner,
        {"client_key": str(uuid.uuid4()), "jumped_on": "2024-04-01", "jump_type": "belly",
         "place_id": kept["id"]},
        201,
    )["jump"]  # fmt: skip

    refused = api.call("POST", f"/jumps/imports/{item['id']}/undo", owner, {"confirm": False})  # fmt: skip
    assert (refused.status_code, refused.json()["detail"]) == (422, "confirm_required")
    undone = api.ok("POST", f"/jumps/imports/{item['id']}/undo", owner, {"confirm": True})  # fmt: skip
    assert undone["undone_at"] is not None
    assert undone["counts"]["removed_jumps"] == 3  # the edited one too
    assert undone["counts"]["removed_places"] == 1  # Kept field still has a jump
    assert [j["id"] for j in api.jumps(owner)] == [manual["id"]]
    assert [p["name"] for p in api.ok("GET", "/places", owner)] == ["Kept field"]

    twice = api.call("POST", f"/jumps/imports/{item['id']}/undo", owner, {"confirm": True})  # fmt: skip
    assert (twice.status_code, twice.json()["detail"]) == (409, "already_undone")
    assert api.ok("GET", "/jumps/imports", owner)[0]["undone_at"] is not None

    # An undone file may be imported again; it reuses the existing private place.
    again = api.run(owner, raw, country="PT").json()
    assert again["outcome"] == "imported"
    assert again["item"]["counts"]["new_places"] == 1  # Gone field, created anew
    assert _count(SkydiverJump, actor) == 4
    assert [i["id"] for i in api.ok("GET", "/jumps/imports", owner)] == [again["item"]["id"]]  # fmt: skip


def test_nobody_else_can_see_or_undo_an_import(api: Api) -> None:
    owner, other = api.accounts.session(), api.accounts.session()
    item = api.run(owner, _csv("2024-03-12,1,Private strip,,,,"), country="PT").json()["item"]  # fmt: skip
    assert api.ok("GET", "/jumps/imports", other) == []
    theirs = api.call("POST", f"/jumps/imports/{item['id']}/undo", other, {"confirm": True})  # fmt: skip
    missing = api.call("POST", f"/jumps/imports/{uuid.uuid7()}/undo", other, {"confirm": True})  # fmt: skip
    assert theirs.status_code == missing.status_code == 404
    assert theirs.json() == missing.json()
    for method, path in (("GET", "/jumps/imports"), ("POST", f"/jumps/imports/{item['id']}/undo")):  # fmt: skip
        assert api.call(method, path, None, {"confirm": True}).status_code == 401
    for path in ("/jumps/import/check", "/jumps/import"):
        assert api.send(path, None, _csv("2024-03-12,1,X,,,,")).status_code == 401
    assert len(api.jumps(owner)) == 1


def test_checking_needs_a_session_and_importing_a_confirmed_email(api: Api) -> None:
    unconfirmed = api.accounts.session(verified=False)
    raw = _csv("2024-03-12,1,Somewhere,,,,")
    assert api.check(unconfirmed, raw, country="PT").status_code == 200
    refused = api.run(unconfirmed, raw, country="PT")
    assert (refused.status_code, refused.json()["detail"]) == (403, "email_unverified")


def test_an_export_with_imported_jumps_restores_into_an_empty_account(api: Api) -> None:
    owner, target = api.accounts.session(), api.accounts.session()
    api.run(owner, _csv("2024-03-12,7,Export strip,angle,,,"), country="PT")
    exported = api.call("GET", "/records/export", owner)
    assert exported.status_code == 200, exported.text
    archive = json.loads(exported.content)
    assert [j["source"] for j in archive["records"]["jumps"]] == ["imported"]
    restored = api.client.post(
        "/api/skydiver/v1/records/restore", content=exported.content,
        headers={"authorization": f"Bearer {target}", "content-type": "application/json",
                 PASSWORD_HEADER: PASSWORD},
    )  # fmt: skip
    assert restored.status_code == 200, restored.text
    (jump,) = api.jumps(target)
    assert api.ok("GET", f"/jumps/{jump['id']}", target)["jump"]["source"] == "restored"


def _service(store_type: type[SqlImportStore]) -> ImportService:
    @contextmanager
    def stores() -> Iterator[SqlImportStore]:
        with Session(engine) as session:
            try:
                yield store_type(session)
            except BaseException:
                session.rollback()
                raise
            session.commit()

    return ImportService(stores=stores, clock=lambda: NOW)


def test_two_imports_at_once_never_pass_the_jump_limit_together(api: Api) -> None:
    """Both imports start counting at once; only one may pass the limit."""
    owner = api.accounts.session()
    actor = _actor(api, owner)
    api.run(owner, _bulk(1990), country="PT")
    files = [_bulk(8, first=3000, place="Race A"), _bulk(8, first=4000, place="Race B")]
    both_counted = threading.Barrier(2, timeout=10)
    lock = threading.Lock()
    waits = [0]

    class Simultaneous(SqlImportStore):
        def lock_owner(self, actor: Actor) -> None:
            with lock:
                first_two = waits[0] < 2
                waits[0] += 1
            if first_two:  # both imports reach the per-person gate together
                both_counted.wait()
            super().lock_owner(actor)

    service = _service(Simultaneous)

    def attempt(raw: bytes) -> str:
        try:
            options = Options(country="PT")
            return service.run(actor, raw, options, expected=None, before_write=lambda: None).outcome  # fmt: skip
        except LimitReached as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = sorted(pool.map(attempt, files))
    assert results == ["imported", "jump_limit_reached"]
    assert _count(SkydiverJump, actor) == 1998
    assert _count(SkydiverJumpImport, actor) == 2


def test_the_same_file_imported_twice_at_once_is_written_once(api: Api) -> None:
    owner = api.accounts.session()
    actor = _actor(api, owner)
    raw = _bulk(5, place="Twin field")
    both_counted = threading.Barrier(2, timeout=10)
    lock = threading.Lock()
    waits = [0]

    class Simultaneous(SqlImportStore):
        def lock_owner(self, actor: Actor) -> None:
            with lock:
                first_two = waits[0] < 2
                waits[0] += 1
            if first_two:  # both imports reach the per-person gate together
                both_counted.wait()
            super().lock_owner(actor)

    service = _service(Simultaneous)
    options = Options(country="PT")
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = sorted(
            pool.map(
                lambda _: (
                    service.run(
                        actor, raw, options, expected=None, before_write=lambda: None
                    ).outcome
                ),  # fmt: skip
                range(2),
            )
        )
    assert results == ["already_imported", "imported"]
    assert _count(SkydiverJump, actor) == 5
    assert _count(SkydiverProvisionalPlace, actor) == 1


def test_an_import_and_a_jump_logged_meanwhile_never_pass_the_jump_limit(
    api: Api,
) -> None:
    owner = api.accounts.session()
    actor = _actor(api, owner)
    api.run(owner, _bulk(1995), country="PT")
    place = uuid.UUID(api.ok("GET", "/places", owner)[0]["id"])
    counted = threading.Event()

    class Slow(SqlImportStore):
        def count_jumps(self, actor: Actor) -> int:
            count = super().count_jumps(actor)
            counted.set()
            time.sleep(0.5)  # a jump logged by hand starts while this import counts
            return count

    directory = DirectoryService(stores=sql_directory_store_factory(engine), clock=lambda: NOW)  # fmt: skip
    logbook = LogbookService(stores=sql_logbook_store_factory(engine), clock=lambda: NOW, directory=directory)  # fmt: skip
    fields = {"jumped_on": date(2024, 1, 1), "place_id": place, "jump_type": "belly"}

    def by_hand() -> str:
        assert counted.wait(10)
        try:
            logbook.create_jump(actor, uuid.uuid4(), fields, confirm_distinct=True)
        except JumpLimitReached as error:
            return error.code
        return "created"

    with ThreadPoolExecutor(max_workers=2) as pool:
        imported = pool.submit(
            lambda: _service(Slow).run(
                actor, _bulk(5, first=9000), Options(country="PT"),
                expected=None, before_write=lambda: None,
            ).outcome
        )  # fmt: skip
        manual = pool.submit(by_hand)
        assert (imported.result(), manual.result()) == (
            "imported",
            "jump_limit_reached",
        )
    assert _count(SkydiverJump, actor) == 2000


def test_an_import_and_a_place_added_meanwhile_never_pass_the_place_limit(
    api: Api,
) -> None:
    owner = api.accounts.session()
    actor = _actor(api, owner)
    many = _csv(*(f"2020-01-01,{n},Field {n},,,," for n in range(1, 200)))
    assert api.run(owner, many, country="PT").json()["item"]["counts"]["new_places"] == 199  # fmt: skip
    counted = threading.Event()

    class Slow(SqlImportStore):
        def count_places(self, actor: Actor) -> int:
            count = super().count_places(actor)
            counted.set()
            time.sleep(0.5)  # a place added by hand starts while this import counts
            return count

    directory = DirectoryService(stores=sql_directory_store_factory(engine), clock=lambda: NOW)  # fmt: skip

    def by_hand() -> str:
        assert counted.wait(10)
        try:
            directory.create_place(actor, name="Added by hand", country="PT")
        except PlaceLimitReached as error:
            return error.code
        return "created"

    with ThreadPoolExecutor(max_workers=2) as pool:
        imported = pool.submit(
            lambda: _service(Slow).run(
                actor, _csv("2020-02-02,500,Last field,,,,"), Options(country="PT"),
                expected=None, before_write=lambda: None,
            ).outcome
        )  # fmt: skip
        manual = pool.submit(by_hand)
        assert (imported.result(), manual.result()) == (
            "imported",
            "place_limit_reached",
        )
    assert _count(SkydiverProvisionalPlace, actor) == 200


def test_an_undo_and_an_import_reusing_its_place_do_not_collide(api: Api) -> None:
    """The undo waits for the import, so it keeps the place the new jump now uses."""
    owner = api.accounts.session()
    actor = _actor(api, owner)
    first = api.run(owner, _csv("2024-03-12,1,Shared field,,,,"), country="PT").json()
    read = threading.Event()

    class Slow(SqlImportStore):
        def own_places(self, actor: Actor) -> list[PlaceName]:
            places = super().own_places(actor)
            read.set()
            time.sleep(0.5)  # the undo starts while this import holds the place
            return places

    def undo() -> dict[str, int]:
        assert read.wait(10)
        return api.imports.undo(actor, uuid.UUID(first["item"]["id"])).counts

    with ThreadPoolExecutor(max_workers=2) as pool:
        imported = pool.submit(
            lambda: _service(Slow).run(
                actor, _csv("2024-03-13,2,Shared field,,,,"), Options(country="PT"),
                expected=None, before_write=lambda: None,
            ).outcome
        )  # fmt: skip
        undone = pool.submit(undo)
        assert imported.result() == "imported"
        counts = undone.result()
    assert (counts["removed_jumps"], counts["removed_places"]) == (1, 0)
    assert [j["jump_number"] for j in api.jumps(owner)] == [2]
    assert [p["name"] for p in api.ok("GET", "/places", owner)] == ["Shared field"]


def test_only_completed_imports_use_the_daily_quota(api: Api) -> None:
    owner = api.accounts.session()
    for _ in range(11):  # refused: new places but no country
        refused = api.run(owner, _csv("2024-03-12,1,Nowhere,,,,"))
        assert refused.json()["detail"] == "country_required"
    for n in range(1, 11):
        done = api.run(owner, _csv(f"2024-03-12,{n},Quota field,,,,"), country="PT")
        assert done.json()["outcome"] == "imported", done.text
    over = api.run(owner, _csv("2024-03-12,11,Quota field,,,,"), country="PT")
    assert (over.status_code, over.json()["detail"]) == (429, "too_many_attempts")
    assert int(over.headers["retry-after"]) > 0
    assert len(api.ok("GET", "/jumps?limit=50", owner)["items"]) == 10


def _quota_hits(api: Api, secret: str) -> int:
    account = str(api.accounts.service.current_viewer(secret=secret).account_id)
    with Session(engine) as session:
        return int(
            session.execute(
                select(func.count())
                .select_from(SkydiverThrottleEvent)
                .where(col(SkydiverThrottleEvent.bucket) == IMPORT_RULE.bucket)
                .where(
                    col(SkydiverThrottleEvent.key_hash)
                    == throttle_key(IMPORT_RULE.bucket, account)
                )
            ).scalar_one()
        )


def test_a_refused_or_repeated_import_gives_its_quota_slot_back(api: Api) -> None:
    owner = api.accounts.session()
    raw = _csv("2024-03-12,1,Refund field,,,,")
    assert api.run(owner, raw, country="PT").json()["outcome"] == "imported"
    assert _quota_hits(api, owner) == 1
    refused = api.run(owner, _csv("2024-03-12,2,Unknown field,,,,"))
    assert refused.json()["detail"] == "country_required"
    duplicate = api.run(owner, raw, country="GR")  # every row already in the logbook
    assert duplicate.json()["detail"] == "nothing_to_import"
    assert api.run(owner, raw, country="PT").json()["outcome"] == "already_imported"
    assert _quota_hits(api, owner) == 1


def test_imports_at_once_at_the_daily_limit_take_one_slot_each(api: Api) -> None:
    owner = api.accounts.session()
    for n in range(1, 10):
        done = api.run(owner, _csv(f"2024-03-12,{n},Race quota,,,,"), country="PT")
        assert done.json()["outcome"] == "imported", done.text
    assert _quota_hits(api, owner) == 9
    files = [_csv(f"2024-04-01,{n},Race quota,,,,") for n in (100, 200, 300)]
    start = threading.Barrier(3, timeout=10)

    def send(raw: bytes) -> int:
        start.wait()
        return api.run(owner, raw, country="PT").status_code

    with ThreadPoolExecutor(max_workers=3) as pool:
        codes = sorted(pool.map(send, files))
    assert codes == [200, 429, 429]
    assert _quota_hits(api, owner) == 10
    assert len(api.ok("GET", "/jumps?limit=50", owner)["items"]) == 10


def test_import_requests_are_throttled_before_the_file_is_read(api: Api) -> None:
    owner = api.accounts.session()
    for _ in range(30):
        assert api.run(owner, b"\x00not a spreadsheet").status_code == 400
    valid = api.run(owner, _csv("2024-03-12,1,Late field,,,,"), country="PT")
    assert (valid.status_code, valid.json()["detail"]) == (429, "too_many_attempts")
    assert api.jumps(owner) == []


def test_an_aircraft_column_is_imported_as_written(api: Api) -> None:
    owner = api.accounts.session()
    raw = _csv(
        "2024-03-12,Olive grove,Cessna 208 SX-ABC",
        "2024-03-13,Olive grove,",
        f"2024-03-14,Olive grove,{'x' * 61}",
        heading="Date,Place,Αεροσκάφος",
    )
    checked = api.check(owner, raw, country="GR").json()
    assert checked["columns"]["aircraft"] == 2
    assert [s["aircraft"] for s in checked["sample"]] == ["Cessna 208 SX-ABC", None]
    assert checked["problems"] == [{"row": 3, "code": "aircraft_too_long"}]
    assert api.run(owner, raw, country="GR").status_code == 200
    by_day = {j["jumped_on"]: j["aircraft"] for j in api.jumps(owner)}
    assert by_day == {"2024-03-12": "Cessna 208 SX-ABC", "2024-03-13": None}
    # "none" leaves a detected aircraft column out.
    other = api.accounts.session()
    unread = api.check(other, raw, country="GR", col_aircraft="none").json()
    assert unread["columns"]["aircraft"] is None
    assert unread["problems"] == []
