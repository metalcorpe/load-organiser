"""Load the candidate listings as local development data (#162).

    python -m app.skydiver.devdata load PATH --reviewer EMAIL

Owner decision 2026-11-09: the researched candidate records are for local testing
only and are never loaded into production. This refuses to run unless
ENVIRONMENT=local. Records go through the same services and publication rules as
`/review`, acting as EMAIL, an account with the reviewer role. A record the rules
refuse stays unpublished and is reported: a listing without dates waits in
the review queue.

Running it again adds only records not loaded before: each record's source note
carries `dev-data:<key>`.
"""

import argparse
import json
import re
import sys
import unicodedata
import uuid
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, func, select, text
from sqlmodel import Session, col

from app.models import User
from app.skydiver.access.policy import Actor, Role, actor_roles
from app.skydiver.directory.policy import SOURCE_NOTE_MAX, DirectoryRuleError
from app.skydiver.directory.service import DirectoryService, VenueInput
from app.skydiver.identity.tables import SkydiverPerson, SkydiverRoleGrant
from app.skydiver.opportunities.policy import Audience, Discipline, OpportunityStatus
from app.skydiver.opportunities.service import OpportunityService

MARK = "dev-data:"
DRAFTED_ON = date(2026, 11, 9)
OPPORTUNITY_FIELDS = (
    "location_note",
    "starts_on",
    "ends_on",
    "time_zone",
    "disciplines",
    "audience",
    "languages",
    "summary",
    "prerequisites",
    "price_amount",
    "price_currency",
    "price_basis",
    "price_note",
    "registration_url",
    "source_url",
)


class DevDataError(RuntimeError):
    pass


def _slug(value: str) -> str:
    plain = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")[:60]


def _note(key: str, extra: str | None = None) -> str:
    note = f"{MARK}{key} Unreviewed candidate, local development only."
    return f"{note} {extra}"[:SOURCE_NOTE_MAX] if extra else note


def reviewer_actor(engine: Engine, email: str) -> Actor:
    with Session(engine) as session:
        user = session.execute(
            select(User).where(func.lower(col(User.email)) == email.strip().lower())
        ).scalar_one_or_none()
        if user is None:
            raise DevDataError(f"no account for {email}")
        person = session.execute(
            select(SkydiverPerson).where(col(SkydiverPerson.account_id) == user.id)
        ).scalar_one()
        roles = frozenset(
            session.execute(
                select(col(SkydiverRoleGrant.role)).where(
                    col(SkydiverRoleGrant.account_id) == user.id
                )
            ).scalars()
        )
    actor = Actor(
        account_id=user.id,
        person_id=person.id,
        email_verified=True,
        roles=actor_roles(roles),
    )
    if not actor.has(Role.REVIEWER):
        raise DevDataError(f"{email} has no reviewer role (scripts/dev.sh grant)")
    return actor


def _loaded(engine: Engine, table: str) -> dict[str, uuid.UUID]:
    """Records loaded before, by key."""
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                f"SELECT id, source_note FROM {table} "  # noqa: S608 - fixed table names
                "WHERE source_note LIKE :mark"
            ),
            {"mark": f"{MARK}%"},
        ).all()
    return {str(note).split()[0].removeprefix(MARK): row_id for row_id, note in rows}


def load(
    engine: Engine,
    path: Path,
    actor: Actor,
    directory: DirectoryService,
    opportunities: OpportunityService,
) -> dict[str, Any]:
    data = json.loads(path.read_text())
    report: dict[str, Any] = {
        "added": {},
        "skipped": 0,
        "tags_dropped": 0,
        "drafts": [],
    }
    added = report["added"]

    venues = _loaded(engine, "skydiver_venue")
    for v in data["venues"]:
        if v["key"] in venues:
            report["skipped"] += 1
            continue
        venue = directory.create_venue(
            actor,
            VenueInput(
                name=v["name"],
                country=v["country"],
                locality=v.get("locality"),
                latitude=v.get("latitude"),
                longitude=v.get("longitude"),
                source_url=v["source_url"],
                source_note=_note(v["key"]),
                checked_on=DRAFTED_ON,
            ),
        )
        venues[v["key"]] = venue.id
        added["venues"] = added.get("venues", 0) + 1

    providers = _loaded(engine, "skydiver_provider")
    for p in data["providers"]:
        if p["key"] in providers:
            report["skipped"] += 1
            continue
        fields = {
            "name": p["name"],
            "kind": p["kind"],
            "country": p.get("country"),
            "website_url": p.get("website_url"),
            "source_url": p.get("source_url"),
            "source_note": _note(p["key"], p.get("note")),
            "checked_on": DRAFTED_ON,
        }
        provider = opportunities.create_provider(actor, fields, publish=True)
        providers[p["key"]] = provider.id
        added["providers"] = added.get("providers", 0) + 1

    listings = _loaded(engine, "skydiver_opportunity")
    for o in data["opportunities"]:
        key = f"{o['provider']}-{_slug(o['title'])}-{o.get('starts_on') or 'ongoing'}"
        if key in listings:
            report["skipped"] += 1
            continue
        fields = {name: o.get(name) for name in OPPORTUNITY_FIELDS}
        fields.update(
            title=o["title"],
            category=o["category"],
            country=o["country"],
            provider_id=providers[o["provider"]],
            venue_id=venues.get(o["venue"]) if o.get("venue") else None,
            source_note=_note(key),
            checked_on=DRAFTED_ON,
        )
        # Training methods (AFF, static line, tandem...) are not disciplines.
        for name, known in (("disciplines", Discipline), ("audience", Audience)):
            values = fields[name] or []
            kept = [v for v in values if v in set(known)]
            report["tags_dropped"] += len(values) - len(kept)
            fields[name] = kept
        # The API layer parses these before the service sees them; do the same.
        for name in ("starts_on", "ends_on"):
            if fields[name]:
                fields[name] = date.fromisoformat(fields[name])
        if fields["price_amount"] is not None:
            fields["price_amount"] = Decimal(str(fields["price_amount"]))
        try:
            row = opportunities.create_opportunity(actor, fields)
        except DirectoryRuleError as error:
            report["drafts"].append({"key": key, "reason": f"not created: {error}"})
            continue
        listings[key] = row.id
        added["opportunities"] = added.get("opportunities", 0) + 1
        try:
            for status in (OpportunityStatus.REVIEW, OpportunityStatus.PUBLISHED):
                opportunities.set_opportunity_status(actor, row.id, status)
            added["published"] = added.get("published", 0) + 1
        except DirectoryRuleError as error:
            report["drafts"].append({"key": key, "reason": str(error)})
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Load local development listings.")
    parser.add_argument("command", choices=["load"])
    parser.add_argument("path", type=Path)
    parser.add_argument(
        "--reviewer", required=True, help="account with the reviewer role"
    )
    args = parser.parse_args(argv)

    from app.core.config import settings  # settings are read only when run

    if settings.ENVIRONMENT != "local":
        print("dev data loads only with ENVIRONMENT=local", file=sys.stderr)
        return 2
    from app.core.db import engine
    from app.main import directory_service, opportunity_service

    try:
        actor = reviewer_actor(engine, args.reviewer)
    except DevDataError as error:
        print(error, file=sys.stderr)
        return 1
    report = load(engine, args.path, actor, directory_service, opportunity_service)
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
