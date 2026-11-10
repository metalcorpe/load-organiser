"""Local development listings loader (#162)."""

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text

from app.core.config import settings
from app.core.db import engine
from app.skydiver import devdata
from app.skydiver.directory.policy import SOURCE_NOTE_MAX
from app.skydiver.directory.service import DirectoryService
from app.skydiver.directory.store import sql_directory_store_factory
from app.skydiver.opportunities.service import OpportunityService
from app.skydiver.opportunities.store import sql_listing_store_factory
from app.tests.skydiver.support import Accounts

REPO = Path(__file__).resolve().parents[4]


def _email(accounts: Accounts, secret: str) -> str:
    account = accounts.service.current_viewer(secret=secret).account_id
    with engine.connect() as conn:
        return str(conn.execute(text('SELECT email FROM "user" WHERE id = :id'), {"id": account}).scalar_one())  # fmt: skip


def _fixture(tag: str) -> dict[str, Any]:
    return {
        "venues": [
            {
                "key": f"t-{tag}-dz",
                "name": f"Dev DZ {tag}",
                "country": "ES",
                "locality": "Somewhere",
                "latitude": None,
                "longitude": None,
                "source_url": "https://example.org/dz",
            }
        ],  # fmt: skip
        "providers": [
            {
                "key": f"t-{tag}-org",
                "name": f"Dev Org {tag}",
                "kind": "organization",
                "country": "ES",
                "website_url": "https://example.org/",
                "source_url": "https://example.org/about",
                "note": "Owner says: one organizer.",
            }
        ],  # fmt: skip
        "opportunities": [
            {
                "title": f"Dated boogie {tag}",
                "category": "boogie",
                "provider": f"t-{tag}-org",
                "venue": f"t-{tag}-dz",
                "country": "ES",
                "starts_on": "2027-03-25",
                "ends_on": "2027-03-29",
                "time_zone": "Europe/Madrid",
                "disciplines": ["belly"],
                "audience": [],
                "languages": [],
                "summary": "A test boogie.",
                "price_amount": "80",
                "price_currency": "EUR",
                "price_basis": "per_person",
                "registration_url": "https://example.org/register",
                "source_url": "https://example.org/boogie",
            },  # fmt: skip
            {
                "title": f"Ongoing AFF {tag}",
                "category": "course",
                "provider": f"t-{tag}-org",
                "venue": f"t-{tag}-dz",
                "country": "ES",
                "starts_on": None,
                "ends_on": None,
                "time_zone": None,
                "disciplines": ["aff", "freefly"],
                "audience": [],
                "languages": [],
                "registration_url": "https://example.org/contact",
                "source_url": "https://example.org/aff",
            },  # fmt: skip
        ],
    }


def test_loads_through_the_rules_once_and_leaves_undated_listings_in_review(tmp_path: Path) -> None:  # fmt: skip
    accounts = Accounts.create()
    actor = devdata.reviewer_actor(engine, _email(accounts, accounts.session(reviewer=True)))  # fmt: skip
    clock = lambda: datetime.now(UTC)  # noqa: E731
    directory = DirectoryService(stores=sql_directory_store_factory(engine), clock=clock)  # fmt: skip
    listings = OpportunityService(stores=sql_listing_store_factory(engine), clock=clock)  # fmt: skip
    tag = uuid.uuid4().hex[:8]
    path = tmp_path / "dev.json"
    path.write_text(json.dumps(_fixture(tag)))

    first = devdata.load(engine, path, actor, directory, listings)
    assert first["added"] == {"venues": 1, "providers": 1, "opportunities": 2, "published": 1}  # fmt: skip
    assert [d["key"] for d in first["drafts"]] == [
        f"t-{tag}-org-ongoing-aff-{tag}-ongoing"
    ]
    assert first["tags_dropped"] == 1  # "aff" is a training method, not a discipline
    with engine.connect() as conn:
        rows: dict[str, str] = dict(conn.execute(text("SELECT title, status FROM skydiver_opportunity WHERE title LIKE :t"), {"t": f"%{tag}"}).all())  # fmt: skip
    assert rows == {f"Dated boogie {tag}": "published", f"Ongoing AFF {tag}": "review"}

    again = devdata.load(engine, path, actor, directory, listings)
    assert again["added"] == {}
    assert again["skipped"] == 4


def test_needs_a_reviewer() -> None:
    accounts = Accounts.create()
    with pytest.raises(devdata.DevDataError):
        devdata.reviewer_actor(engine, _email(accounts, accounts.session()))


def test_refuses_outside_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    assert devdata.main(["load", "x.json", "--reviewer", "a@example.com"]) == 2


def test_the_dev_listings_file_matches_what_the_loader_reads() -> None:
    data = json.loads((REPO / "docs/product/inventory/dev-listings.json").read_text())
    providers = {p["key"] for p in data["providers"]}
    venues = {v["key"] for v in data["venues"]}
    assert all(v["source_url"] for v in data["venues"])
    for o in data["opportunities"]:
        assert o["provider"] in providers, o["title"]
        assert o["venue"] is None or o["venue"] in venues, o["title"]
        assert o["category"] in ("event", "boogie", "camp", "course"), o["title"]
    # Notes go through the source-note length rule (a 286-character note once broke seeding).
    for p in data["providers"]:
        note = devdata._note(p["key"], p.get("note"))
        assert len(note) <= SOURCE_NOTE_MAX and note.endswith(p.get("note") or "."), p["key"]  # fmt: skip
    assert len(devdata._note("k" * 60, "x" * 500)) == SOURCE_NOTE_MAX
