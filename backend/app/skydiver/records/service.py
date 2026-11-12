"""Personal export and empty-record restore (#155).

Export: the owner's records in format v1 from one consistent snapshot.

Restore, in order:
1. Bound and parse the raw bytes (v1 schema), then validate everything without a
   write. The SHA-256 of the exact raw bytes identifies the file.
2. A completed restore of the same file by the same owner answers "already
   restored" with no writes, even after later edits or deletions.
3. Otherwise the records must be empty (places, gear, jumps, baseline, saved
   listings and plans); a non-empty target is refused before any write.
4. Everything is inserted under new IDs in one transaction with the receipt. The
   managed collections are counted again before commit, so a write that landed
   concurrently makes the whole restore roll back (compare-and-swap style, no
   lock). Public references resolve to their current public record; a venue no
   longer public becomes a private place from the archive's snapshot, a plan's
   listing link that is no longer public is dropped, and a saved listing that is
   no longer public is reported and not restored.

Nothing in an archive grants a role, a follow, a publication or verification:
the schema cannot carry them, and restored records are marked `restored`.
"""

import hashlib
import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Protocol

from pydantic import ValidationError

from app.skydiver.access.policy import Actor
from app.skydiver.directory.policy import DirectoryRuleError
from app.skydiver.directory.service import DirectoryService
from app.skydiver.gear import policy as gear_policy
from app.skydiver.gear.service import fingerprint as gear_fingerprint
from app.skydiver.opportunities.service import OpportunityService
from app.skydiver.records import format as v1
from app.skydiver.records import policy, spreadsheet
from app.skydiver.records.policy import ArchiveInvalid, Counts


class ArchiveMalformed(Exception):
    """Not a JSON object, or not this format."""

    code = "archive_malformed"


class ArchiveUnsupported(Exception):
    code = "archive_version_unsupported"


class ArchiveTooLarge(Exception):
    code = "archive_too_large"


class RecordsNotEmpty(Exception):
    code = "records_not_empty"


@dataclass(frozen=True)
class Receipt:
    fingerprint: str
    counts: dict[str, Any]
    restored_at: datetime


@dataclass(frozen=True)
class Summary:
    counts: dict[str, int]
    empty: bool
    last_restore: Receipt | None


@dataclass(frozen=True)
class Detached:
    venues_to_private_places: int = 0
    plan_links_dropped: int = 0
    saved_not_restorable: list[str] = field(default_factory=list)  # public titles


@dataclass(frozen=True)
class Check:
    fingerprint: str
    exported_at: datetime
    counts: Counts
    detached: Detached
    eligible: bool
    reason: str | None  # records_not_empty | already_restored
    already_restored_at: datetime | None


@dataclass(frozen=True)
class Outcome:
    outcome: str  # restored | already_restored
    fingerprint: str
    counts: dict[str, Any]
    restored_at: datetime


@dataclass(frozen=True)
class SheetJump:
    """One jump as the spreadsheet needs it."""

    jumped_on: date
    venue_id: uuid.UUID | None
    place_id: uuid.UUID | None
    jump_type: str
    jump_number: int | None
    aircraft: str | None
    exit_altitude: int | None
    deployment_altitude: int | None
    altitude_unit: str | None
    freefall_seconds: int | None
    notes: str | None
    other_gear: str | None
    gear: list[str]  # labels of the components used


class RecordsStore(Protocol):
    def snapshot(self) -> None: ...
    def export_records(self, actor: Actor) -> v1.RecordsV1: ...
    def sheet_jumps(
        self, actor: Actor, from_on: date | None, until_on: date | None
    ) -> list[SheetJump]:
        """Oldest first; dates inclusive. Bounded by the jump limit."""
        ...

    def place_names(self, actor: Actor) -> dict[uuid.UUID, tuple[str, str]]:
        """The owner's private places: name and country."""
        ...

    def venue_refs(self, venue_ids: list[uuid.UUID]) -> list[v1.VenueRefV1]: ...
    def listing_refs(self, listing_ids: list[uuid.UUID]) -> list[v1.ListingRefV1]: ...
    def managed_counts(self, actor: Actor) -> dict[str, int]: ...
    def receipt(self, actor: Actor, fingerprint: str) -> Receipt | None: ...
    def latest_receipt(self, actor: Actor) -> Receipt | None: ...
    def insert_rows(self, table: str, rows: list[dict[str, Any]]) -> None:
        """Bulk insert; raises ArchiveInvalid when a database rule refuses a row."""
        ...

    def next_receipt_sequence(self, actor: Actor) -> int: ...
    def insert_receipt(
        self, actor: Actor, receipt: Receipt, version: int, sequence: int
    ) -> bool:
        """False when a concurrent restore already took this file or this sequence."""
        ...


StoreFactory = Callable[[], AbstractContextManager[RecordsStore]]
Clock = Callable[[], datetime]


class _LostRace(Exception):
    """Another restore committed first: the same file, or a different one."""


def parse(raw: bytes) -> tuple[v1.ArchiveV1, str]:
    """The validated archive and the SHA-256 of the exact raw bytes."""
    if len(raw) > policy.RAW_MAX_BYTES:
        raise ArchiveTooLarge()
    digest = hashlib.sha256(raw).hexdigest()
    try:
        archive = v1.ArchiveV1.model_validate_json(raw, strict=True)
    except ValidationError as error:
        first = error.errors(include_url=False, include_input=False)[0]
        loc = first["loc"]
        if first["type"] in ("json_invalid", "model_type") and len(loc) <= 1:
            raise ArchiveMalformed() from None
        if loc and loc[0] in ("format", "version"):
            raise ArchiveUnsupported() from None
        raise ArchiveInvalid(_where(loc, first["type"])) from None
    if len(archive.model_dump_json()) > policy.NORMALIZED_MAX_BYTES:
        raise ArchiveTooLarge()
    return archive, digest


def _where(loc: tuple[Any, ...], kind: str) -> str:
    """`records.jumps[3].notes.string_too_long`: positions and rule only, no content."""
    parts: list[str] = []
    for item in loc:
        if isinstance(item, int) and parts:
            parts[-1] += f"[{item}]"
        else:
            parts.append(str(item))
    return ".".join([*parts, kind])[:200]


class RecordsService:
    def __init__(
        self,
        *,
        stores: StoreFactory,
        clock: Clock,
        directory: DirectoryService,
        opportunities: OpportunityService,
    ) -> None:
        self._stores = stores
        self._clock = clock
        self._directory = directory
        self._opportunities = opportunities

    def _latest_local_date(self) -> date:
        return (self._clock() + timedelta(hours=14)).date()

    # -- reads ------------------------------------------------------------------------

    def summary(self, actor: Actor) -> Summary:
        with self._stores() as store:
            counts = store.managed_counts(actor)
            last = store.latest_receipt(actor)
        return Summary(counts, not any(counts.values()), last)

    def export(self, actor: Actor) -> bytes:
        """Compact UTF-8 JSON, format v1, from one database snapshot."""
        now = self._clock()
        with self._stores() as store:
            store.snapshot()
            records = store.export_records(actor)
            venue_ids = {p.venue_id for p in records.places if p.venue_id}
            venue_ids |= {j.venue_id for j in records.jumps if j.venue_id}
            venue_ids |= {p.venue_id for p in records.plans if p.venue_id}
            listing_ids = {s.opportunity_id for s in records.saved_listings}
            listing_ids |= {p.opportunity_id for p in records.plans if p.opportunity_id}
            references = v1.ReferencesV1(
                venues=store.venue_refs(sorted(venue_ids)),
                listings=store.listing_refs(sorted(listing_ids)),
            )
        archive = v1.ArchiveV1(
            format="load-organiser.personal-records",
            version=1,
            exported_at=now,
            records=records,
            references=references,
        )
        return archive.model_dump_json().encode()

    def spreadsheet(
        self, actor: Actor, *, from_on: date | None = None, until_on: date | None = None
    ) -> bytes:
        """The owner's jumps as CSV (see records/spreadsheet.py), oldest first, from
        one snapshot. Dates are inclusive; both are optional."""
        if from_on is not None and until_on is not None and from_on > until_on:
            raise DirectoryRuleError("date_range_invalid")
        with self._stores() as store:
            store.snapshot()
            jumps = store.sheet_jumps(actor, from_on, until_on)
            places = store.place_names(actor)
            venue_ids = sorted({j.venue_id for j in jumps if j.venue_id})
            stored = {v.id: v for v in store.venue_refs(venue_ids)}
        # The dropzone's current name (merges followed), else its name as stored.
        current = self._directory.public_venues(venue_ids) if venue_ids else {}
        rows = []
        for j in jumps:
            name, country = "", None
            if j.venue_id is not None:
                venue = current.get(j.venue_id)
                ref = stored.get(j.venue_id)
                if venue is not None:
                    name, country = venue.name, venue.country
                elif ref is not None:
                    name, country = ref.name, ref.country
            elif j.place_id is not None and j.place_id in places:
                name, country = places[j.place_id]
            rows.append(
                spreadsheet.Row(
                    jumped_on=j.jumped_on,
                    jump_number=j.jump_number,
                    place=name,
                    country=country,
                    jump_type=j.jump_type,
                    aircraft=j.aircraft,
                    exit_altitude=j.exit_altitude,
                    altitude_unit=j.altitude_unit,
                    deployment_altitude=j.deployment_altitude,
                    freefall_seconds=j.freefall_seconds,
                    notes=j.notes,
                    gear=[*j.gear, *([j.other_gear] if j.other_gear else [])],
                )
            )
        return spreadsheet.render(rows)

    def check(self, actor: Actor, raw: bytes) -> Check:
        """Validate and preview without writing. Advisory: restore rechecks all."""
        archive, digest = parse(raw)
        policy.check(archive, self._latest_local_date())
        plan = self._plan(archive)
        with self._stores() as store:
            done = store.receipt(actor, digest)
            counts = store.managed_counts(actor)
        reason = (
            "already_restored"
            if done
            else ("records_not_empty" if any(counts.values()) else None)
        )
        return Check(
            fingerprint=digest,
            exported_at=archive.exported_at,
            counts=policy.counts(archive),
            detached=plan.detached,
            eligible=reason is None,
            reason=reason,
            already_restored_at=done.restored_at if done else None,
        )

    # -- restore ----------------------------------------------------------------------

    def restore(
        self, actor: Actor, raw: bytes, *, before_write: Callable[[], None]
    ) -> Outcome:
        """`before_write` runs once, only when a write will be attempted (throttle)."""
        archive, digest = parse(raw)
        policy.check(archive, self._latest_local_date())
        with self._stores() as store:
            done = store.receipt(actor, digest)
        if done:
            return Outcome("already_restored", digest, done.counts, done.restored_at)
        before_write()
        plan = self._plan(archive)
        now = self._clock()
        try:
            with self._stores() as store:
                if (done := store.receipt(actor, digest)) is not None:
                    return Outcome(
                        "already_restored", digest, done.counts, done.restored_at
                    )
                # Read before the emptiness check: a restore committing after this
                # read either shows up in that check or holds the same sequence.
                sequence = store.next_receipt_sequence(actor)
                if any(store.managed_counts(actor).values()):
                    raise RecordsNotEmpty()
                rows = _rows(actor, archive, plan, now)
                for table, items in rows.items():
                    store.insert_rows(table, items)
                # Compare-and-swap on emptiness: anything else that landed meanwhile
                # makes the counts differ, and the whole restore rolls back.
                after = store.managed_counts(actor)
                expected = {name: len(rows.get(name, [])) for name in after}
                if after != expected:
                    raise RecordsNotEmpty()
                counts: dict[str, Any] = {
                    **expected,
                    "service_entries": len(rows.get("service_entries", [])),
                    "venues_to_private_places": plan.detached.venues_to_private_places,
                    "plan_links_dropped": plan.detached.plan_links_dropped,
                    "saved_not_restorable": len(plan.detached.saved_not_restorable),
                }
                receipt = Receipt(digest, counts, now)
                if not store.insert_receipt(actor, receipt, archive.version, sequence):
                    raise _LostRace()
        except _LostRace:
            with self._stores() as store:
                done = store.receipt(actor, digest)
            if done is None:  # a different file won: these records are no longer empty
                raise RecordsNotEmpty() from None
            return Outcome("already_restored", digest, done.counts, done.restored_at)
        return Outcome("restored", digest, counts, now)

    def _plan(self, archive: v1.ArchiveV1) -> _Plan:
        """Current public state of every referenced venue and listing."""
        r = archive.records
        venue_ids = sorted(
            {p.venue_id for p in r.places if p.venue_id}
            | {j.venue_id for j in r.jumps if j.venue_id}
            | {p.venue_id for p in r.plans if p.venue_id}
        )
        venues = {k: v.id for k, v in self._directory.public_venues(venue_ids).items()}
        listing_ids = sorted(
            {s.opportunity_id for s in r.saved_listings}
            | {p.opportunity_id for p in r.plans if p.opportunity_id}
        )
        found = (
            self._opportunities.public_opportunities(listing_ids) if listing_ids else {}
        )
        listings = {k: v.value.row.id for k, v in found.items() if v is not None}
        # Venues a jump or plan still needs as a location become private places.
        located = {j.venue_id for j in r.jumps if j.venue_id} | {
            p.venue_id for p in r.plans if p.venue_id
        }
        missing = sorted(v for v in located if v not in venues)
        if len(r.places) + len(missing) > policy.MAX_PLACES:
            raise ArchiveInvalid("places.too_many")
        titles = {ref.id: ref.title for ref in archive.references.listings}
        detached = Detached(
            venues_to_private_places=len(missing),
            plan_links_dropped=sum(
                1
                for p in r.plans
                if p.opportunity_id and p.opportunity_id not in listings
            ),
            saved_not_restorable=[
                titles.get(s.opportunity_id, s.title)
                for s in r.saved_listings
                if s.opportunity_id not in listings
            ],
        )
        return _Plan(venues, listings, missing, detached)


@dataclass(frozen=True)
class _Plan:
    venues: dict[uuid.UUID, uuid.UUID]  # archive venue -> current public venue
    listings: dict[uuid.UUID, uuid.UUID]  # archive listing -> current public listing
    missing_venues: list[uuid.UUID]  # needed as locations, no longer public
    detached: Detached


def _rows(
    actor: Actor, archive: v1.ArchiveV1, plan: _Plan, now: datetime
) -> dict[str, list[dict[str, Any]]]:
    """Every row to insert, under new IDs owned by `actor`."""
    r = archive.records
    owner = actor.person_id
    ids: dict[uuid.UUID, uuid.UUID] = {}

    def new(old: uuid.UUID) -> uuid.UUID:
        ids[old] = uuid.uuid7()
        return ids[old]

    marker = {"exported_at": archive.exported_at.isoformat()}
    refs = {v.id: v for v in archive.references.venues}
    out: dict[str, list[dict[str, Any]]] = {}

    places = [
        {
            "id": new(p.id),
            "owner_person_id": owner,
            "name": p.name,
            "country": p.country,
            "venue_id": plan.venues.get(p.venue_id) if p.venue_id else None,
            "created_at": p.created_at,
            "updated_at": p.updated_at,
        }  # fmt: skip
        for p in r.places
    ]
    venue_place: dict[uuid.UUID, uuid.UUID] = {}
    for venue_id in plan.missing_venues:
        ref = refs[venue_id]
        venue_place[venue_id] = uuid.uuid7()
        places.append(
            {
                "id": venue_place[venue_id],
                "owner_person_id": owner,
                "name": ref.name,
                "country": ref.country,
                "venue_id": None,
                "created_at": now,
                "updated_at": now,
            }  # fmt: skip
        )
    out["places"] = places

    components = []
    for c in r.components:
        values = c.model_dump(exclude={"id", "archived_at", "created_at", "updated_at"})
        components.append(
            {
                **values,
                "id": new(c.id),
                "owner_person_id": owner,
                "client_key": uuid.uuid4(),
                "fingerprint": gear_fingerprint(values),
                "serial_key": gear_policy.serial_key(c.serial),
                "archived_at": c.archived_at,
                "version": 1,
                "created_at": c.created_at,
                "updated_at": c.updated_at,
            }  # fmt: skip
        )
    out["components"] = components
    out["rigs"] = [
        {
            "id": new(g.id),
            "owner_person_id": owner,
            "client_key": uuid.uuid4(),
            "label": g.label,
            "archived_at": g.archived_at,
            "version": 1,
            "created_at": g.created_at,
            "updated_at": g.updated_at,
        }  # fmt: skip
        for g in r.rigs
    ]
    out["rig_stints"] = [
        {
            "id": uuid.uuid7(),
            "owner_person_id": owner,
            "rig_id": ids[m.rig_id],
            "component_id": ids[m.component_id],
            "from_on": m.from_on,
            "until_on": m.until_on,
        }  # fmt: skip
        for m in r.rig_stints
    ]
    services = []
    for s in r.service_entries:
        values = s.model_dump(exclude={"id", "component_id", "created_at"})
        services.append(
            {
                **values,
                "id": new(s.id),
                "owner_person_id": owner,
                "client_key": uuid.uuid4(),
                "fingerprint": gear_fingerprint(values),
                "component_id": ids[s.component_id],
                "created_at": s.created_at,
            }  # fmt: skip
        )
    out["service_entries"] = services

    jumps, links = [], []
    for j in r.jumps:
        venue = plan.venues.get(j.venue_id) if j.venue_id else None
        place = (
            ids[j.place_id]
            if j.place_id
            else (venue_place[j.venue_id] if j.venue_id and venue is None else None)
        )
        jump_id = new(j.id)
        values = j.model_dump(
            exclude={
                "id",
                "venue_id",
                "place_id",
                "component_ids",
                "source",
                "created_at",
                "updated_at",
            }  # fmt: skip
        )
        jumps.append(
            {
                **values,
                "id": jump_id,
                "owner_person_id": owner,
                "venue_id": venue,
                "place_id": place,
                "source": "restored",
                "version": 1,
                "created_at": j.created_at,
                "updated_at": j.updated_at,
            }  # fmt: skip
        )
        links += [
            {"jump_id": jump_id, "component_id": ids[c], "owner_person_id": owner}
            for c in j.component_ids
        ]
    out["jumps"], out["jump_components"] = jumps, links

    # History keeps its dates; archive IDs inside details point at the new records.
    text_ids = {str(k): str(v) for k, v in ids.items()}
    out["gear_events"] = [
        {
            "id": uuid.uuid7(),
            "owner_person_id": owner,
            "component_id": ids[e.component_id],
            "kind": e.kind,
            "detail": policy.remap(e.detail, text_ids),
            "created_at": e.created_at,
        }  # fmt: skip
        for e in r.gear_events
    ] + [
        {
            "id": uuid.uuid7(),
            "owner_person_id": owner,
            "component_id": ids[c.id],
            "kind": "from_export",
            "detail": marker,
            "created_at": now,
        }  # fmt: skip
        for c in r.components
    ]
    out["jump_events"] = [
        {
            "id": uuid.uuid7(),
            "owner_person_id": owner,
            "jump_id": ids[e.jump_id],
            "kind": e.kind,
            "detail": policy.jump_history(e.detail, text_ids),
            "created_at": e.created_at,
        }  # fmt: skip
        for e in r.jump_events
    ] + [
        {
            "id": uuid.uuid7(),
            "owner_person_id": owner,
            "jump_id": ids[j.id],
            "kind": "from_export",
            "detail": marker,
            "created_at": now,
        }  # fmt: skip
        for j in r.jumps
    ]

    if r.baseline is not None:
        b = r.baseline
        out["baseline"] = [
            {
                "owner_person_id": owner,
                "prior_jumps": b.prior_jumps,
                "before_on": b.before_on,
                "source": "restored",
                "version": 1,
                "created_at": b.created_at,
                "updated_at": b.updated_at,
            }  # fmt: skip
        ]
    events = [
        {
            "id": uuid.uuid7(),
            "owner_person_id": owner,
            "kind": e.kind,
            "detail": e.detail,
            "created_at": e.created_at,
        }  # fmt: skip
        for e in r.baseline_events
    ]
    if r.baseline is not None:
        events.append(
            {
                "id": uuid.uuid7(),
                "owner_person_id": owner,
                "kind": "from_export",
                "detail": marker
                | {
                    "prior_jumps": r.baseline.prior_jumps,
                    "before_on": r.baseline.before_on.isoformat(),
                },
                "created_at": now,
            }  # fmt: skip
        )
    out["baseline_events"] = events

    saved: dict[uuid.UUID, dict[str, Any]] = {}
    for item in r.saved_listings:
        current = plan.listings.get(item.opportunity_id)
        if current is not None and current not in saved:
            saved[current] = {
                "id": uuid.uuid7(), "owner_person_id": owner,
                "opportunity_id": current, "title": item.title,
                "created_at": item.created_at,
            }  # fmt: skip
    out["saved_listings"] = list(saved.values())

    plans = []
    for p in r.plans:
        venue = plan.venues.get(p.venue_id) if p.venue_id else None
        plans.append(
            {
                "id": uuid.uuid7(),
                "owner_person_id": owner,
                "title": p.title,
                "starts_on": p.starts_on,
                "ends_on": p.ends_on,
                "note": p.note,
                "opportunity_id": plan.listings.get(p.opportunity_id)
                if p.opportunity_id
                else None,
                "venue_id": venue,
                "place_id": ids[p.place_id]
                if p.place_id
                else (
                    venue_place[p.venue_id] if p.venue_id and venue is None else None
                ),
                "created_at": p.created_at,
                "updated_at": p.updated_at,
            }  # fmt: skip
        )
    out["plans"] = plans
    if r.licence is not None:
        out["licence"] = [
            {"owner_person_id": owner, "licence": r.licence, "updated_at": now}
        ]
    if r.exit_weight is not None:
        out["exit_weight"] = [
            {
                "owner_person_id": owner,
                "grams": r.exit_weight.grams,
                "unit": r.exit_weight.unit,
            }
        ]
    return out
