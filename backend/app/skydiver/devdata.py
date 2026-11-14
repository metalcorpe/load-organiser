"""Load the candidate listings as local development data (#162).

    python -m app.skydiver.devdata load PATH --reviewer EMAIL [--dropzones DIR]

Owner decision 2026-11-09: the researched candidate records are for local testing
only and are never loaded into production. This refuses to run unless
ENVIRONMENT=local and SKYDIVER_DEV_DATA=1 are both set explicitly (scripts/dev.sh
seed sets them) and the database is on this machine. Records go through the same services and publication rules as
`/review`, acting as EMAIL, an account with the reviewer role. A record the rules
refuse stays unpublished and is reported: a listing without dates waits in
the review queue.

Running it again adds only records not loaded before: each record's source note
carries `dev-data:<key>`.

The researched dropzone inventory (`dropzones/<CC>.json` next to PATH, or DIR; files
starting with `_` are notes and are skipped) loads as venues with coordinates and
aliases. A dropzone already present, by key, or by its name matching a stored venue
name or alias in the same country, is not added again; an existing venue without
coordinates gets the researched ones. Its own aliases never match: they are often
operator brands shared by several airfields. Each venue is created as a draft and
made public (listed, or closed for researched `closed` dropzones) in one step at
the end; `uncertain` ones stay listed, with the research status in the source note.
Invalid records are refused and reported; the rest still load.
"""

import argparse
import json
import os
import re
import sys
import unicodedata
import uuid
from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, func, select, text
from sqlmodel import Session, col

from app.models import User
from app.skydiver.access.policy import Actor, Role, actor_roles
from app.skydiver.directory.policy import (
    SOURCE_NOTE_MAX,
    DirectoryRuleError,
    VenueStatus,
    search_key,
)
from app.skydiver.directory.service import (
    DirectoryService,
    EditConflict,
    VenueChanges,
    VenueInput,
)
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


def dropzone_files(folder: Path) -> list[Path]:
    """Country files of the dropzone inventory; `_`-prefixed files are research notes."""
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.glob("*.json") if not p.name.startswith("_"))


def _venue_names(engine: Engine) -> dict[tuple[str, str], uuid.UUID]:
    """Unmerged venues by (country, name or alias search key), as stored before this run."""
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT country, name_key, id FROM skydiver_venue "
                "WHERE status <> 'merged' "
                "UNION ALL "
                "SELECT v.country, a.alias_key, v.id FROM skydiver_venue_alias a "
                "JOIN skydiver_venue v ON v.id = a.venue_id WHERE v.status <> 'merged'"
            )
        ).all()
    return {(country, key): venue_id for country, key, venue_id in rows}


def _venue_status(engine: Engine, venue_id: uuid.UUID) -> str:
    with engine.connect() as conn:
        return str(
            conn.execute(
                text("SELECT status FROM skydiver_venue WHERE id = :id"),
                {"id": venue_id},
            ).scalar_one()
        )


DROPZONE_STATUSES = frozenset({"active", "seasonal", "uncertain", "closed"})
DROPZONE_KEY = re.compile(r"^[a-z0-9-]+$")


def _is_coordinate(value: Any) -> bool:
    return value is None or (
        isinstance(value, int | float) and not isinstance(value, bool)
    )


def _record_problem(dz: Any) -> str | None:
    """Why a research record cannot load, checked before anything is written."""
    if not isinstance(dz, dict):
        return "record_invalid"
    if not isinstance(dz.get("key"), str) or not DROPZONE_KEY.match(dz["key"]):
        return "key_invalid"
    if not isinstance(dz.get("name"), str) or not isinstance(dz.get("country"), str):
        return "name_or_country_invalid"
    if dz.get("status") not in DROPZONE_STATUSES:
        return "status_invalid"
    if not (_is_coordinate(dz.get("latitude")) and _is_coordinate(dz.get("longitude"))):
        return "coordinates_invalid"
    aliases = dz.get("aliases") or []
    if not isinstance(aliases, list) or not all(isinstance(a, str) for a in aliases):
        return "aliases_invalid"
    return None


def _source(dropzone: dict[str, Any], researched_on: str | None) -> tuple[str, date]:
    """The first web source, and the day it was checked (or the file's research day)."""
    for source in dropzone.get("sources") or []:
        url = str(source.get("url") or "")
        if url.startswith(("https://", "http://")):
            day = source.get("checked_on") or researched_on
            return url, date.fromisoformat(str(day))
    raise DirectoryRuleError("source_required")


def _locate(
    directory: DirectoryService,
    actor: Actor,
    venue_id: uuid.UUID,
    dropzone: dict[str, Any],
) -> bool:
    """Give an existing venue the researched coordinates if it has none (compare-and-swap)."""
    if dropzone.get("latitude") is None or dropzone.get("longitude") is None:
        return False
    venue, _ = directory.reviewer_venue(actor, venue_id)
    if venue.latitude is not None:
        return False
    try:
        directory.update_venue(
            actor,
            venue_id,
            VenueChanges(
                {"latitude": dropzone["latitude"], "longitude": dropzone["longitude"]}
            ),
            expected_version=venue.version,
        )
    except EditConflict, DirectoryRuleError:
        return False  # changed meanwhile, or the coordinates are refused: left as it is
    return True


def _publish(
    directory: DirectoryService,
    actor: Actor,
    venue_id: uuid.UUID,
    aliases: list[str],
    status: str,
) -> int:
    """Aliases, then the public status in one step; returns the aliases dropped.

    The venue is created as a draft, so it is not public until this succeeds. A
    failure leaves the draft, and the next run finishes it (aliases are idempotent).
    """
    dropped = 0
    venue, _ = directory.reviewer_venue(actor, venue_id)
    for alias in aliases:
        try:
            venue = directory.add_alias(
                actor, venue_id, alias, expected_version=venue.version
            )
        except DirectoryRuleError:
            dropped += 1
    target = VenueStatus.CLOSED if status == "closed" else VenueStatus.LISTED
    directory.set_status(actor, venue_id, target, expected_version=venue.version)
    return dropped


def load_dropzones(
    engine: Engine, folder: Path, actor: Actor, directory: DirectoryService
) -> dict[str, Any]:
    """Every country file; a bad file or record is refused, never the whole load.

    A record is a duplicate only by its own name, matched against the names and
    aliases stored before this run and the names of venues this run adds. Aliases
    added here (often operator brands shared by several airfields) never identify
    a dropzone.
    """
    report: dict[str, Any] = {
        "files": 0,
        "added": 0,
        "closed": 0,
        "skipped": 0,
        "resumed": 0,
        "duplicates": [],
        "located": 0,
        "aliases_dropped": 0,
        "refused": [],
    }
    loaded = _loaded(engine, "skydiver_venue")
    names = _venue_names(engine)
    for file in dropzone_files(folder):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            records = data["dropzones"]
            if not isinstance(records, list):
                raise TypeError("dropzones is not a list")
        except (ValueError, KeyError, TypeError) as error:
            report["refused"].append({"file": file.name, "reason": str(error)[:200]})
            continue
        report["files"] += 1
        for dz in records:
            problem = _record_problem(dz)
            if problem:
                key = dz.get("key") if isinstance(dz, dict) else None
                report["refused"].append({"key": key, "reason": problem})
                continue
            key = dz["key"]
            status = dz["status"]
            aliases = [a for a in dz.get("aliases") or [] if a.strip()]
            if key in loaded:
                if _venue_status(engine, loaded[key]) != "draft":
                    report["skipped"] += 1
                    continue
                venue_id = loaded[key]  # a draft an earlier run left unfinished
                report["resumed"] += 1
            else:
                country = dz["country"].upper()
                match = names.get((country, search_key(dz["name"])))
                if match is not None:
                    report["duplicates"].append({"key": key, "matched": str(match)})
                    report["located"] += _locate(directory, actor, match, dz)
                    continue
                try:
                    url, checked = _source(dz, data.get("researched_on"))
                    venue = directory.create_venue(
                        actor,
                        VenueInput(
                            name=dz["name"],
                            country=country,
                            locality=dz.get("locality"),
                            latitude=dz.get("latitude"),
                            longitude=dz.get("longitude"),
                            source_url=url,
                            source_note=_note(key, f"Research status: {status}."),
                            checked_on=checked,
                            listed=False,
                        ),
                    )
                except (DirectoryRuleError, ValueError) as error:
                    report["refused"].append({"key": key, "reason": str(error)})
                    continue
                venue_id = venue.id
                loaded[key] = venue_id
                names[(country, search_key(venue.name))] = venue_id
            try:
                report["aliases_dropped"] += _publish(
                    directory, actor, venue_id, aliases, status
                )
            except (DirectoryRuleError, EditConflict) as error:
                reason = getattr(error, "code", None) or str(error)
                report["refused"].append(
                    {"key": key, "reason": f"left as draft: {reason}"}
                )
                continue
            report["added"] += 1
            report["closed"] += status == "closed"
    return report


def load(
    engine: Engine,
    path: Path,
    actor: Actor,
    directory: DirectoryService,
    opportunities: OpportunityService,
    dropzones: Path | None = None,
) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
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

    # After the listings' venues, so a dropzone they already name is not added twice.
    report["dropzones"] = load_dropzones(
        engine, dropzones or path.parent / "dropzones", actor, directory
    )

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


LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def dev_data_refusal(
    environ: Mapping[str, str], environment: str, postgres_server: str
) -> str | None:
    """Why loading must not run here, or None. Every condition is an explicit opt-in.

    Settings default ENVIRONMENT to "local", so the setting alone could fail open:
    the variable itself must say local, `SKYDIVER_DEV_DATA=1` must be set (only
    `scripts/dev.sh seed` sets it) and the database must be on this machine.
    """
    if environ.get("SKYDIVER_DEV_DATA") != "1":
        return "dev data loads only with SKYDIVER_DEV_DATA=1 (scripts/dev.sh seed)"
    if environ.get("ENVIRONMENT") != "local" or environment != "local":
        return "dev data loads only with ENVIRONMENT=local set explicitly"
    if postgres_server not in LOOPBACK_HOSTS:
        return "dev data loads only into a database on this machine"
    return None


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Load local development listings.")
    parser.add_argument("command", choices=["load"])
    parser.add_argument("path", type=Path)
    parser.add_argument(
        "--reviewer", required=True, help="account with the reviewer role"
    )
    parser.add_argument(
        "--dropzones",
        type=Path,
        default=None,
        help="dropzone inventory folder (default: dropzones/ next to PATH)",
    )
    args = parser.parse_args(argv)

    from app.core.config import settings  # settings are read only when run

    refusal = dev_data_refusal(
        os.environ, settings.ENVIRONMENT, settings.POSTGRES_SERVER
    )
    if refusal:
        print(refusal, file=sys.stderr)
        return 2
    if args.dropzones is not None and not args.dropzones.is_dir():
        print(f"--dropzones {args.dropzones} is not a directory", file=sys.stderr)
        return 2
    from app.core.db import engine
    from app.main import directory_service, opportunity_service

    try:
        actor = reviewer_actor(engine, args.reviewer)
    except DevDataError as error:
        print(error, file=sys.stderr)
        return 1
    report = load(
        engine,
        args.path,
        actor,
        directory_service,
        opportunity_service,
        dropzones=args.dropzones,
    )
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
