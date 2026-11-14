"""Load the candidate listings as local development data (#162).

    python -m app.skydiver.devdata load PATH --reviewer EMAIL [--dropzones DIR]
    python -m app.skydiver.devdata dropzones DIR --reviewer EMAIL [--publish STATUSES]

`dropzones` is the one exception to the rule below (owner request 2026-11-14): the
researched dropzone inventory into the hosted database, run only by the owner
through `scripts/staging.sh load-dropzones`. New dropzones are drafts until the
owner names the research statuses to publish; see `load_dropzones`.

Owner decision 2026-11-09: the researched candidate records are for local testing
only and are never loaded into production. `load` refuses to run unless
ENVIRONMENT=local and SKYDIVER_DEV_DATA=1 are both set explicitly (scripts/dev.sh
seed sets them) and the database is on this machine. Records go through the same services and publication rules as
`/review`, acting as EMAIL, an account with the reviewer role. A record the rules
refuse stays unpublished and is reported: a listing without dates waits in
the review queue.

Running it again adds only records not loaded before: each record's source note
carries `dev-data:<key>`.

The researched dropzone inventory (`dropzones/<CC>.json` next to PATH, or DIR; files
starting with `_` are notes and are skipped) loads as venues with coordinates and
aliases. A dropzone already present is not added again: by key, by its name matching
a stored venue name or alias, by a stored venue in the same country within
`NEAR_KM`, by place name (see `same_place`), or by an alias no other record of the
country carries. An existing venue without coordinates gets the researched ones.
Aliases several records share never match: they are often operator brands of
several airfields. Each venue is created as a
draft and made public (listed, or closed for researched `closed` dropzones) in one
step at the end; `uncertain` ones stay drafts, as on staging: an unconfirmed lead is
not shown as a dropzone. The research status is in the source note. Invalid records
are refused and reported; the rest still load.
"""

import argparse
import json
import math
import os
import re
import sys
import unicodedata
import uuid
from collections import Counter
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, func, select, text
from sqlmodel import Session, col

from app.models import User
from app.skydiver.access.policy import Actor, Role, actor_roles
from app.skydiver.directory.policy import (
    DETAIL_MAX,
    OPERATOR_NAME_MAX,
    OPERATORS_MAX,
    SOURCE_NOTE_MAX,
    DirectoryRuleError,
    VenueStatus,
    clean_text,
    search_key,
    web_url,
)
from app.skydiver.directory.service import (
    MAX_MERGE_HOPS,
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


# The source note shows on the public dropzone page, so a hosted record says what it is
# in words and carries its inventory key at the end (how a later run finds it).
HOSTED_REF = re.compile(r"Inventory ref ([a-z0-9-]+)\.$")


def _hosted_note(key: str, status: str) -> str:
    return f"Research status: {status}. Inventory ref {key}."


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
    """Records loaded before, by key: local (`dev-data:`) or hosted (`Inventory ref`)."""
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                f"SELECT id, source_note FROM {table} "  # noqa: S608 - fixed table names
                "WHERE source_note LIKE :mark OR source_note LIKE :ref"
            ),
            {"mark": f"{MARK}%", "ref": "%Inventory ref %"},
        ).all()
    loaded: dict[str, uuid.UUID] = {}
    for row_id, note in rows:
        hosted = HOSTED_REF.search(str(note))
        if hosted:
            loaded[hosted.group(1)] = row_id
        elif str(note).startswith(MARK):
            loaded[str(note).split()[0].removeprefix(MARK)] = row_id
    return loaded


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


# Two dropzones closer than this are one place: the inventory's own rule.
NEAR_KM = 1.5
# Names alone never match two places further apart than this.
NAME_KM = 10.0
# Words that say what a place is, not which one. Direction words stay: "West" and
# "Ost" are two airfields of one town.
GENERIC_WORDS = frozenset(
    """
    aerodrome aerodromo aerodrom aerodromas aerodromul aerodroom aeroport aeroporto
    aeroportul aeropuerto airport airfield airstrip vliegveld flugplatz flughafen
    landeplatz sonderlandeplatz verkehrslandeplatz lotnisko letiste letisko repuloter
    flygplats flyplass lufthavn lentokentta lentopaikka aviosuperficie havaalani
    aeroclub aeroklub civil municipal military base aviation international regional
    field strip landing area site zone drop dropzone dz skydive skydiving parachute
    parachuting parachutisme paracaidismo paracadutismo fallschirm fallschirmsport
    fallskjerm fallskarm laskuvarjo centre center centro club klub school ecole escuela
    de la le les du des el los las da do dos das di del della dei the of and und am an
    der im bei sur en van het op
    """.split()
)


def place_words(name: str) -> frozenset[str]:
    """The words of a name that say which place it is."""
    return frozenset(
        w for w in search_key(name).split() if len(w) > 1 and w not in GENERIC_WORDS
    )


def _km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 6371.0 * 2 * math.asin(math.sqrt(h))


@dataclass(frozen=True)
class StoredVenue:
    id: uuid.UUID
    words: frozenset[str]
    point: tuple[float, float] | None


def same_place(
    words: frozenset[str],
    point: tuple[float, float] | None,
    candidates: Iterable[StoredVenue],
) -> tuple[uuid.UUID, str] | None:
    """The venue (of one country) a dropzone already is, and how that was decided.

    Within `NEAR_KM` it is the same place whatever the names. Otherwise the place
    words of one name must all be in the other ("Aeródromo de Lillo" and "Skydive
    Madrid (Aeródromo de Lillo)"), unless both have coordinates more than `NAME_KM`
    apart.
    """
    named: uuid.UUID | None = None
    for venue in candidates:
        if point is not None and venue.point is not None:
            distance = _km(point, venue.point)
            if distance <= NEAR_KM:
                return venue.id, "distance"
            if distance > NAME_KM:
                continue
        if named is None:
            small, large = sorted((words, venue.words), key=len)
            if small and small <= large:
                named = venue.id
    return (named, "name") if named is not None else None


def _by_own_alias(
    aliases: Sequence[str],
    country: str,
    point: tuple[float, float] | None,
    names: Mapping[tuple[str, str], uuid.UUID],
    carried: Mapping[tuple[str, str], int],
    stored: Mapping[str, Sequence[StoredVenue]],
) -> tuple[uuid.UUID, str] | None:
    """A stored venue named by an alias only this record carries ("iJump Gran Canaria",
    the operator's office, for the airfield it flies from), unless far apart."""
    points = {v.id: v.point for v in stored.get(country, ())}
    for alias in aliases:
        key = (country, search_key(alias))
        venue_id = names.get(key)
        if venue_id is None or carried[key] != 1:
            continue
        there = points.get(venue_id)
        if point is not None and there is not None and _km(point, there) > NAME_KM:
            continue
        return venue_id, "alias"
    return None


def _stored_venues(engine: Engine) -> dict[str, list[StoredVenue]]:
    """Unmerged venues by country, as stored before this run."""
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT id, country, name, latitude, longitude FROM skydiver_venue "
                "WHERE status <> 'merged'"
            )
        ).all()
    stored: dict[str, list[StoredVenue]] = {}
    for venue_id, country, name, lat, lon in rows:
        point = (float(lat), float(lon)) if lat is not None else None
        stored.setdefault(country, []).append(
            StoredVenue(venue_id, place_words(name), point)
        )
    return stored


def _point(dropzone: Mapping[str, Any]) -> tuple[float, float] | None:
    lat, lon = dropzone.get("latitude"), dropzone.get("longitude")
    return (float(lat), float(lon)) if lat is not None and lon is not None else None


def _venue_status(engine: Engine, venue_id: uuid.UUID) -> str:
    with engine.connect() as conn:
        return str(
            conn.execute(
                text("SELECT status FROM skydiver_venue WHERE id = :id"),
                {"id": venue_id},
            ).scalar_one()
        )


def _surviving(engine: Engine, venue_id: uuid.UUID) -> uuid.UUID | None:
    """The venue `venue_id` resolves to through merges (itself if not merged)."""
    with engine.connect() as conn:
        for _ in range(MAX_MERGE_HOPS):
            row = conn.execute(
                text(
                    "SELECT status, merged_into_id FROM skydiver_venue WHERE id = :id"
                ),
                {"id": venue_id},
            ).one_or_none()
            if row is None:
                return None
            if row.status != "merged":
                return venue_id
            venue_id = row.merged_into_id
    return None


DROPZONE_STATUSES = frozenset({"active", "seasonal", "uncertain", "closed"})
# The local load shows what the research confirmed; `uncertain` leads stay drafts.
LOCAL_PUBLISH = DROPZONE_STATUSES - {"uncertain"}
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


def _details(dropzone: Mapping[str, Any]) -> dict[str, Any]:
    """Operators, season and aircraft as the record states them, cleaned so a quirk
    (an over-long name, a broken link) drops that detail instead of the record."""
    operators: list[dict[str, str | None]] = []
    for op in dropzone.get("operators") or []:
        if not isinstance(op, dict) or len(operators) == OPERATORS_MAX:
            continue
        try:
            name = clean_text(
                str(op.get("name") or ""), field="operator", maximum=OPERATOR_NAME_MAX
            )
        except DirectoryRuleError:
            continue
        if any(search_key(o["name"] or "") == search_key(name) for o in operators):
            continue
        url = None
        for candidate in (op.get("website"), op.get("facebook")):
            try:
                url = web_url(str(candidate), code="url") if candidate else None
            except DirectoryRuleError:
                url = None
            if url:
                break
        operators.append({"name": name, "url": url})

    def text(key: str) -> str | None:
        value = " ".join(str(dropzone.get(key) or "").split())
        return (
            value[: DETAIL_MAX - 1] + "…" if len(value) > DETAIL_MAX else value or None
        )

    return {
        "operators": operators,
        "season": text("season"),
        "aircraft": text("aircraft"),
    }


def _fill_details(
    directory: DirectoryService,
    actor: Actor,
    venue_id: uuid.UUID,
    dropzone: Mapping[str, Any],
) -> bool:
    """Give a venue the researched details if it has none of them (compare-and-swap)."""
    details = _details(dropzone)
    if not any(details.values()):
        return False
    try:
        venue, _ = directory.reviewer_venue(actor, venue_id)
        if venue.operators or venue.season or venue.aircraft:
            return False
        directory.update_venue(
            actor, venue_id, VenueChanges(details), expected_version=venue.version
        )
    except EditConflict, DirectoryRuleError:
        return False  # changed meanwhile, merged, or refused: left as it is
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
    engine: Engine,
    folder: Path,
    actor: Actor,
    directory: DirectoryService,
    publish: Collection[str] | None = None,
) -> dict[str, Any]:
    """Every country file; a bad file or record is refused, never the whole load.

    A record is a duplicate by its own name matching a stored name or alias, by
    `same_place` against the venues stored before this run and those this run adds,
    or by one of its aliases matching a stored name or alias when no other record of
    that country carries the alias. Shared aliases (often operator brands of several
    airfields) never identify a dropzone.

    `publish` None is the local development load: every status but `uncertain` is
    made public (`LOCAL_PUBLISH`), with or without coordinates. Given (the hosted
    load), only records whose research status is in it and that have coordinates are
    made public. Only records made public fill in a stored venue's missing
    coordinates or details (operators, season, aircraft: `_fill_details`, also for
    venues an earlier run loaded before the details existed); every other new record
    stays a draft that a later run with its status publishes. An empty set changes
    nothing public.
    """
    report: dict[str, Any] = {
        "files": 0,
        "added": 0,
        "closed": 0,
        "skipped": 0,
        "resumed": 0,
        "drafted": 0,
        "duplicates": [],
        "located": 0,
        "detailed": 0,
        "aliases_dropped": 0,
        "refused": [],
    }

    def publishes(dz: Mapping[str, Any]) -> bool:
        if publish is None:
            return dz["status"] in LOCAL_PUBLISH
        return dz["status"] in publish and _point(dz) is not None

    loaded = _loaded(engine, "skydiver_venue")
    names = _venue_names(engine)
    stored = _stored_venues(engine)
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
        carried = Counter(
            (dz["country"].upper(), search_key(alias))
            for dz in records
            if _record_problem(dz) is None
            for alias in {a for a in dz.get("aliases") or [] if a.strip()}
        )
        for dz in records:
            problem = _record_problem(dz)
            if problem:
                key = dz.get("key") if isinstance(dz, dict) else None
                report["refused"].append({"key": key, "reason": problem})
                continue
            key = dz["key"]
            status = dz["status"]
            aliases = [a for a in dz.get("aliases") or [] if a.strip()]
            resumed = key in loaded
            if resumed:
                if _venue_status(engine, loaded[key]) != "draft":
                    report["skipped"] += 1
                    # Loaded before the details existed: add them where it may publish,
                    # to the surviving venue when this one was merged into another.
                    target = _surviving(engine, loaded[key]) if publishes(dz) else None
                    if target is not None:
                        report["detailed"] += _fill_details(
                            directory, actor, target, dz
                        )
                    continue
                venue_id = loaded[key]  # a draft an earlier run left, or kept
                report["detailed"] += _fill_details(directory, actor, venue_id, dz)
            else:
                country = dz["country"].upper()
                words, point = place_words(dz["name"]), _point(dz)
                exact = names.get((country, search_key(dz["name"])))
                match = (
                    (exact, "name")
                    if exact is not None
                    else same_place(words, point, stored.get(country, ()))
                )
                if match is None:
                    match = _by_own_alias(
                        aliases, country, point, names, carried, stored
                    )
                if match is not None:
                    report["duplicates"].append(
                        {"key": key, "matched": str(match[0]), "by": match[1]}
                    )
                    if publishes(dz):
                        report["located"] += _locate(directory, actor, match[0], dz)
                        report["detailed"] += _fill_details(
                            directory, actor, match[0], dz
                        )
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
                            source_note=(
                                _note(key, f"Research status: {status}.")
                                if publish is None
                                else _hosted_note(key, status)
                            ),
                            checked_on=checked,
                            listed=False,
                            **_details(dz),
                        ),
                    )
                except (DirectoryRuleError, ValueError) as error:
                    report["refused"].append({"key": key, "reason": str(error)})
                    continue
                venue_id = venue.id
                loaded[key] = venue_id
                names[(country, search_key(venue.name))] = venue_id
                stored.setdefault(country, []).append(
                    StoredVenue(venue_id, words, point)
                )
            if not publishes(dz):
                report["drafted"] += 1
                continue
            report["resumed"] += resumed
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


def hosted_refusal(environ: Mapping[str, str]) -> str | None:
    """Why the hosted dropzone load must not run here, or None.

    Only `scripts/staging.sh load-dropzones` runs it: ENVIRONMENT=staging and the
    operator's DATABASE_URL, both set explicitly in a cleared environment.
    """
    if environ.get("ENVIRONMENT") != "staging" or not environ.get("DATABASE_URL"):
        return (
            "the hosted dropzone load runs only from scripts/staging.sh load-dropzones"
        )
    return None


def _statuses(value: str | None) -> frozenset[str]:
    chosen = frozenset(s.strip() for s in (value or "").split(",") if s.strip())
    unknown = chosen - DROPZONE_STATUSES
    if unknown:
        raise argparse.ArgumentTypeError(
            f"unknown status {', '.join(sorted(unknown))}; "
            f"choose from {', '.join(sorted(DROPZONE_STATUSES))}"
        )
    return chosen


def load_hosted(folder: Path, reviewer: str, publish: frozenset[str]) -> int:
    """The researched dropzones into the hosted database (owner request 2026-11-14).

    Drafts only unless `publish` names research statuses; see `load_dropzones`.
    """
    from datetime import UTC, datetime

    from app.core.db import engine
    from app.skydiver.directory.store import sql_directory_store_factory

    directory = DirectoryService(
        stores=sql_directory_store_factory(engine), clock=lambda: datetime.now(UTC)
    )
    try:
        actor = reviewer_actor(engine, reviewer)
    except DevDataError as error:
        print(error, file=sys.stderr)
        return 1
    report = load_dropzones(engine, folder, actor, directory, publish=publish)
    print(json.dumps(report, indent=1))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Load local development listings, or the researched dropzones "
        "into the hosted database."
    )
    parser.add_argument("command", choices=["load", "dropzones"])
    parser.add_argument(
        "path",
        type=Path,
        help="load: the listings file; dropzones: the dropzone inventory folder",
    )
    parser.add_argument(
        "--reviewer", required=True, help="account with the reviewer role"
    )
    parser.add_argument(
        "--dropzones",
        type=Path,
        default=None,
        help="load: dropzone inventory folder (default: dropzones/ next to PATH)",
    )
    parser.add_argument(
        "--publish",
        type=_statuses,
        default=frozenset(),
        help="dropzones: research statuses to make public, comma-separated "
        "(default: none; new dropzones stay drafts)",
    )
    args = parser.parse_args(argv)

    if args.command == "dropzones":
        refusal = hosted_refusal(os.environ)
        if refusal:
            print(refusal, file=sys.stderr)
            return 2
        if not args.path.is_dir():
            print(f"{args.path} is not a directory", file=sys.stderr)
            return 2
        return load_hosted(args.path, args.reviewer, args.publish)

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
