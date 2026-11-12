"""Private personal jump logbook (#153).

Owner-only. A jump needs a date, a location (a listed venue or the owner's own
private place) and a type; everything else is optional and never invented.
Creates are idempotent by a client key whose receipt outlives the jump, so a
replay after deletion reports it was deleted instead of recreating it. Edits and
deletes compare-and-swap the jump version. Equipment links point only at the
owner's own components; unknown gear is simply no link, never the current rig.
"""

import hashlib
import json
import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import StrEnum
from typing import Any, Protocol

from app.skydiver.access.policy import Actor
from app.skydiver.directory.policy import DirectoryRuleError as RuleError
from app.skydiver.directory.service import (
    DirectoryService,
    EditConflict,
    Venue,
    decode_cursor,
    encode_cursor,
)
from app.skydiver.logbook import policy
from app.skydiver.logbook.policy import AltitudeDatum, AltitudeUnit, JumpType

DEFAULT_PAGE = 20
MAX_PAGE = 50


class NotFound(Exception):
    """Absent and foreign records alike."""


class LimitReached(Exception):
    code = "jump_limit_reached"


class KeyReused(Exception):
    code = "client_key_reused"


class JumpDeleted(Exception):
    """A replayed create whose jump was saved and later deleted by its owner."""

    code = "jump_deleted"


class LikelyDuplicate(Exception):
    code = "likely_duplicate"

    def __init__(self, duplicate_of: uuid.UUID) -> None:
        super().__init__(self.code)
        self.duplicate_of = duplicate_of


@dataclass(frozen=True)
class Jump:
    id: uuid.UUID
    jumped_on: date
    venue_id: uuid.UUID | None
    place_id: uuid.UUID | None
    jump_type: JumpType
    jump_number: int | None
    exit_time: time | None
    time_zone: str | None
    exit_altitude: int | None
    deployment_altitude: int | None
    altitude_unit: AltitudeUnit | None
    altitude_datum: AltitudeDatum
    freefall_seconds: int | None
    other_gear: str | None
    notes: str | None
    links: tuple[str, ...]
    component_ids: tuple[uuid.UUID, ...]
    source: str
    version: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class Receipt:
    fingerprint: str
    jump_id: uuid.UUID | None


@dataclass(frozen=True)
class ComponentRef:
    id: uuid.UUID
    kind: str
    label: str
    archived: bool


@dataclass(frozen=True)
class PlaceRef:
    id: uuid.UUID
    name: str
    country: str


@dataclass(frozen=True)
class Location:
    kind: str  # "venue" | "place"
    id: uuid.UUID
    name: str | None  # None: a venue no longer listed
    country: str | None
    closed: bool = False


@dataclass(frozen=True)
class JumpView:
    jump: Jump
    location: Location
    components: list[ComponentRef]


@dataclass(frozen=True)
class JumpEvent:
    kind: str
    detail: dict[str, Any]
    created_at: datetime


@dataclass(frozen=True)
class JumpDetail:
    view: JumpView
    events: list[JumpEvent]
    same_number: list[uuid.UUID]


@dataclass(frozen=True)
class JumpFilter:
    """The owner's own search over their logbook; every field narrows the set."""

    text: str | None = None
    jump_type: JumpType | None = None
    venue_id: uuid.UUID | None = None
    place_id: uuid.UUID | None = None
    from_date: date | None = None
    to_date: date | None = None
    number_from: int | None = None
    number_to: int | None = None


@dataclass(frozen=True)
class Criteria:
    """A JumpFilter resolved for the store: venues are expanded through merges."""

    text: str | None = None
    text_venue_ids: frozenset[uuid.UUID] = frozenset()
    jump_type: str | None = None
    venue_ids: frozenset[uuid.UUID] | None = None
    place_id: uuid.UUID | None = None
    from_date: date | None = None
    to_date: date | None = None
    number_from: int | None = None
    number_to: int | None = None


@dataclass(frozen=True)
class Totals:
    jumps: int
    freefall_seconds: int | None  # sum over the jumps that recorded it
    freefall_recorded: int
    first_on: date | None
    last_on: date | None


@dataclass(frozen=True)
class JumpPage:
    items: list[JumpView]
    next_cursor: str | None
    recorded_total: int
    matched: Totals


@dataclass(frozen=True)
class NumberedRef:
    id: uuid.UUID
    jumped_on: date
    number: int


class LogbookStore(Protocol):
    def lock_owner(self, actor: Actor) -> None:
        """Serialise this person's jump-limit checks (manual creates and imports)."""
        ...

    def count_jumps(self, actor: Actor) -> int: ...
    def receipt(self, actor: Actor, client_key: uuid.UUID) -> Receipt | None: ...
    def get_jump(self, actor: Actor, jump_id: uuid.UUID) -> Jump | None: ...
    def page(
        self,
        actor: Actor,
        after: tuple[date, uuid.UUID] | None,
        limit: int,
        where: Criteria = Criteria(),
    ) -> list[Jump]:
        """Newest activity date first, then newest entry."""
        ...

    def totals(self, actor: Actor, where: Criteria) -> Totals: ...
    def venue_ids(self, actor: Actor) -> list[uuid.UUID]:
        """The distinct venues of the owner's jumps, as stored (before merges)."""

    def numbered(self, actor: Actor) -> list[NumberedRef]:
        """The owner's numbered jumps by number, then date and id (bounded by the limit)."""
        ...

    def find_same(self, actor: Actor, values: dict[str, Any]) -> uuid.UUID | None:
        """An existing jump with the same number, or the same core facts."""
        ...

    def same_number(
        self, actor: Actor, number: int, exclude: uuid.UUID
    ) -> list[uuid.UUID]: ...
    def insert_jump(
        self,
        actor: Actor,
        client_key: uuid.UUID,
        fingerprint: str,
        values: dict[str, Any],
        component_ids: list[uuid.UUID],
        now: datetime,
    ) -> uuid.UUID | None:
        """Jump and receipt together; None if a concurrent same-key create won."""
        ...

    def update_jump(
        self,
        actor: Actor,
        jump_id: uuid.UUID,
        values: dict[str, Any],
        component_ids: list[uuid.UUID] | None,
        now: datetime,
        *,
        expected_version: int,
    ) -> None:
        """Compare-and-swap; raises EditConflict if the version moved."""
        ...

    def delete_jump(
        self, actor: Actor, jump_id: uuid.UUID, *, expected_version: int
    ) -> None: ...
    def components(
        self, actor: Actor, component_ids: list[uuid.UUID]
    ) -> list[ComponentRef]:
        """The owner's own components among these IDs; others are omitted."""
        ...

    def places(self, actor: Actor, place_ids: list[uuid.UUID]) -> list[PlaceRef]: ...
    def record(
        self,
        actor: Actor,
        jump_id: uuid.UUID,
        kind: str,
        detail: dict[str, Any],
        now: datetime,
    ) -> None: ...
    def events(self, actor: Actor, jump_id: uuid.UUID) -> list[JumpEvent]: ...
    def withdraw_post(
        self, actor: Actor, jump_id: uuid.UUID, changed: set[str]
    ) -> bool:
        """Delete the jump's published summary if `changed` touches a shared value."""
        ...


StoreFactory = Callable[[], AbstractContextManager[LogbookStore]]
Clock = Callable[[], datetime]

# Corrections to these keep the earlier value in the owner's history; notes, links
# and other-gear text record only that they changed.
_FACTS = (
    "jumped_on",
    "venue_id",
    "place_id",
    "jump_type",
    "jump_number",
    "exit_time",
    "time_zone",
    "exit_altitude",
    "deployment_altitude",
    "altitude_unit",
    "altitude_datum",
    "freefall_seconds",
)
_PRIVATE_TEXT = ("other_gear", "notes", "links")


def fingerprint(values: dict[str, Any]) -> str:
    canonical = json.dumps(
        {k: _plain(v) for k, v in sorted(values.items())}, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _plain(value: Any) -> Any:
    if value is None or isinstance(value, bool | int | str):
        return value
    if isinstance(value, list | tuple):
        return [_plain(v) for v in value]
    return str(value)


class LogbookService:
    def __init__(
        self, *, stores: StoreFactory, clock: Clock, directory: DirectoryService
    ) -> None:
        self._stores = stores
        self._clock = clock
        self._directory = directory

    def _latest_local_date(self) -> date:
        # The latest calendar date anywhere (UTC+14): "today" for every jumper.
        return (self._clock() + timedelta(hours=14)).date()

    # -- reads ------------------------------------------------------------------------

    def list_jumps(
        self,
        actor: Actor,
        *,
        cursor: str | None = None,
        limit: int | None = None,
        search: JumpFilter | None = None,
    ) -> JumpPage:
        """One page of the owner's jumps, optionally filtered.

        The cursor is the last (date, id) seen; filters only add conditions to the
        same order, so a page stays stable while the filters stay the same.
        """
        size = min(max(limit or DEFAULT_PAGE, 1), MAX_PAGE)
        after = _after(cursor) if cursor else None
        _check_filter(search or JumpFilter())
        with self._stores() as store:
            where = self._criteria(store, actor, search or JumpFilter())
            rows = store.page(actor, after, size + 1, where)
            total = store.count_jumps(actor)
            matched = store.totals(actor, where)
            views = self._views(store, actor, rows[:size])
        next_cursor = None
        if len(rows) > size:
            last = rows[size - 1]
            next_cursor = encode_cursor(last.jumped_on.isoformat(), last.id)
        return JumpPage(views, next_cursor, total, matched)

    def _criteria(
        self, store: LogbookStore, actor: Actor, search: JumpFilter
    ) -> Criteria:
        text = search.text.strip() if search.text else None
        venue_ids: frozenset[uuid.UUID] | None = None
        text_venue_ids: frozenset[uuid.UUID] = frozenset()
        if search.venue_id is not None or text:
            # Bounded by the owner's distinct venues; merged venues count under
            # the venue they resolve to, as on the history page.
            stored = store.venue_ids(actor)
            resolved = self._directory.public_venues(stored) if stored else {}
            if search.venue_id is not None:
                target = resolved.get(search.venue_id)
                wanted = target.id if target else search.venue_id
                venue_ids = frozenset(
                    {search.venue_id}
                    | {v for v, venue in resolved.items() if venue.id == wanted}
                )
            if text:
                needle = text.casefold()
                text_venue_ids = frozenset(
                    v
                    for v, venue in resolved.items()
                    if needle in venue.name.casefold()
                    or any(needle in a.name.casefold() for a in venue.aliases)
                )
        return Criteria(
            text=text or None,
            text_venue_ids=text_venue_ids,
            jump_type=search.jump_type.value if search.jump_type else None,
            venue_ids=venue_ids,
            place_id=search.place_id,
            from_date=search.from_date,
            to_date=search.to_date,
            number_from=search.number_from,
            number_to=search.number_to,
        )

    def numbering(self, actor: Actor) -> policy.Numbering[NumberedRef]:
        """Highest jump number, gaps and repeats in the owner's own numbering."""
        with self._stores() as store:
            rows = store.numbered(actor)
        return policy.numbering([policy.Numbered(r.number, r) for r in rows])

    def jump(self, actor: Actor, jump_id: uuid.UUID) -> JumpDetail:
        with self._stores() as store:
            row = store.get_jump(actor, jump_id)
            if row is None:
                raise NotFound()
            return JumpDetail(
                view=self._views(store, actor, [row])[0],
                events=store.events(actor, jump_id),
                same_number=store.same_number(actor, row.jump_number, row.id)
                if row.jump_number
                else [],
            )

    # -- writes -----------------------------------------------------------------------

    def create_jump(
        self,
        actor: Actor,
        client_key: uuid.UUID,
        fields: dict[str, Any],
        *,
        confirm_distinct: bool = False,
    ) -> tuple[JumpDetail, bool]:
        values, given_ids = self._values(fields, partial=False)
        component_ids = given_ids or []
        values = self._located(actor, values)
        digest = fingerprint(
            values | {"component_ids": sorted(map(str, component_ids))}
        )
        now = self._clock()
        jump_id: uuid.UUID | None = None
        created = False
        with self._stores() as store:
            receipt = store.receipt(actor, client_key)
            if receipt is None:
                store.lock_owner(actor)
                self._check_components(store, actor, component_ids)
                self._check_place(store, actor, values.get("place_id"))
                refusal: Exception | None = None
                if store.count_jumps(actor) >= policy.MAX_JUMPS:
                    refusal = LimitReached()
                elif not confirm_distinct:
                    same = store.find_same(actor, values)
                    if same is not None:
                        refusal = LikelyDuplicate(same)
                if refusal is not None:
                    # A same-key create may have committed since the first read:
                    # then this is its retry, not a duplicate or an over-limit.
                    receipt = store.receipt(actor, client_key)
                    if receipt is None:
                        raise refusal
                else:
                    jump_id = store.insert_jump(
                        actor, client_key, digest, values, component_ids, now
                    )
                    if jump_id is not None:
                        store.record(
                            actor, jump_id, "created", {"source": "manual"}, now
                        )
                        created = True
                    else:  # a concurrent retry with the same key won
                        receipt = store.receipt(actor, client_key)
            if receipt is not None:
                if receipt.fingerprint != digest:
                    raise KeyReused()
                if receipt.jump_id is None:
                    raise JumpDeleted()
                jump_id, created = receipt.jump_id, False
        assert jump_id is not None
        return self.jump(actor, jump_id), created

    def update_jump(
        self,
        actor: Actor,
        jump_id: uuid.UUID,
        fields: dict[str, Any],
        *,
        expected_version: int | None,
    ) -> JumpDetail:
        values, component_ids = self._values(fields, partial=True)
        values = self._located(actor, values)
        now = self._clock()
        with self._stores() as store:
            current = store.get_jump(actor, jump_id)
            if current is None:
                raise NotFound()
            if expected_version is not None and expected_version != current.version:
                raise EditConflict()
            before = _values_of(current)
            merged = {**before, **values}
            policy.altitudes(
                merged["exit_altitude"],
                merged["deployment_altitude"],
                AltitudeUnit(merged["altitude_unit"])
                if merged["altitude_unit"]
                else None,
                AltitudeDatum(merged["altitude_datum"]),
            )
            if (merged["exit_time"] is None) != (merged["time_zone"] is None):
                raise RuleError("time_zone_required")
            changed = {k: v for k, v in values.items() if before.get(k) != v}
            if "place_id" in changed:
                self._check_place(store, actor, changed["place_id"])
            links_changed = component_ids is not None and set(component_ids) != set(
                current.component_ids
            )
            if links_changed:
                assert component_ids is not None
                added = [c for c in component_ids if c not in current.component_ids]
                self._check_components(store, actor, added)
            if changed or links_changed:
                store.update_jump(
                    actor,
                    jump_id,
                    changed,
                    component_ids if links_changed else None,
                    now,
                    expected_version=current.version,
                )
                detail: dict[str, Any] = {
                    k: {"from": _plain(before[k]), "to": _plain(changed[k])}
                    if k in _FACTS
                    else "changed"
                    for k in sorted(changed)
                }
                if links_changed:
                    detail["equipment"] = "changed"
                store.record(actor, jump_id, "corrected", detail, now)
                # Same transaction: a shared value never changes under a live post.
                if store.withdraw_post(actor, jump_id, set(changed)):
                    store.record(
                        actor,
                        jump_id,
                        "post_withdrawn",
                        {"reason": "shared_field_changed"},
                        now,
                    )
        return self.jump(actor, jump_id)

    def delete_jump(
        self, actor: Actor, jump_id: uuid.UUID, *, expected_version: int | None
    ) -> None:
        with self._stores() as store:
            current = store.get_jump(actor, jump_id)
            if current is None:
                raise NotFound()
            if expected_version is not None and expected_version != current.version:
                raise EditConflict()
            store.delete_jump(actor, jump_id, expected_version=current.version)

    # -- helpers ----------------------------------------------------------------------

    def _values(
        self, raw: dict[str, Any], *, partial: bool
    ) -> tuple[dict[str, Any], list[uuid.UUID] | None]:
        values: dict[str, Any] = {}

        def given(name: str) -> bool:
            return name in raw or not partial

        if given("jumped_on"):
            if raw.get("jumped_on") is None:
                raise RuleError("jump_date_required")
            values["jumped_on"] = policy.jump_date(
                raw["jumped_on"], self._latest_local_date()
            )
        if given("venue_id") or given("place_id"):
            venue_id, place_id = raw.get("venue_id"), raw.get("place_id")
            if (venue_id is None) == (place_id is None):
                raise RuleError("location_required")
            values["venue_id"], values["place_id"] = venue_id, place_id
        if given("jump_type"):
            kind = _enum(JumpType, raw.get("jump_type"), "jump_type")
            values["jump_type"] = (kind or JumpType.UNSPECIFIED).value
        if given("jump_number"):
            values["jump_number"] = policy.jump_number(raw.get("jump_number"))
        if given("exit_time") or given("time_zone"):
            if partial and not ("exit_time" in raw and "time_zone" in raw):
                raise RuleError("exit_time_incomplete")
            at, zone = policy.exit_time(raw.get("exit_time"), raw.get("time_zone"))
            values["exit_time"], values["time_zone"] = at, zone
        names = ("exit_altitude", "deployment_altitude", "altitude_unit")
        if any(given(n) for n in (*names, "altitude_datum")):
            if partial and not all(n in raw for n in names):
                raise RuleError("altitudes_incomplete")
            heights = policy.altitudes(
                raw.get("exit_altitude"),
                raw.get("deployment_altitude"),
                _enum(AltitudeUnit, raw.get("altitude_unit"), "altitude_unit"),
                _enum(AltitudeDatum, raw.get("altitude_datum"), "altitude_datum"),
            )
            values["exit_altitude"] = heights.exit
            values["deployment_altitude"] = heights.deployment
            values["altitude_unit"] = heights.unit.value if heights.unit else None
            values["altitude_datum"] = heights.datum.value
        if given("freefall_seconds"):
            values["freefall_seconds"] = policy.freefall_seconds(
                raw.get("freefall_seconds")
            )
        if given("other_gear"):
            values["other_gear"] = policy.other_gear(raw.get("other_gear"))
        if given("notes"):
            values["notes"] = policy.notes(raw.get("notes"))
        if given("links"):
            values["links"] = policy.links(raw.get("links"))
        component_ids = (
            policy.component_ids(raw.get("component_ids"))
            if given("component_ids")
            else None
        )
        return values, component_ids

    def _located(self, actor: Actor, values: dict[str, Any]) -> dict[str, Any]:
        """A chosen venue must be listed now; it is stored merge-resolved."""
        venue_id = values.get("venue_id")
        if venue_id is None:
            return values
        found = self._directory.public_venues([venue_id]).get(venue_id)
        if found is None:
            raise RuleError("venue_not_listed")
        return values | {"venue_id": found.id}

    @staticmethod
    def _check_place(
        store: LogbookStore, actor: Actor, place_id: uuid.UUID | None
    ) -> None:
        if place_id is not None and not store.places(actor, [place_id]):
            raise RuleError("place_unknown")  # foreign and absent alike

    @staticmethod
    def _check_components(
        store: LogbookStore, actor: Actor, component_ids: list[uuid.UUID] | None
    ) -> None:
        if not component_ids:
            return
        found = {c.id for c in store.components(actor, component_ids)}
        if found != set(component_ids):
            raise RuleError("component_unknown")  # foreign and absent alike

    def _views(
        self, store: LogbookStore, actor: Actor, rows: list[Jump]
    ) -> list[JumpView]:
        venue_ids = list({r.venue_id for r in rows if r.venue_id})
        place_ids = list({r.place_id for r in rows if r.place_id})
        component_ids = list({c for r in rows for c in r.component_ids})
        venues: dict[uuid.UUID, Venue] = (
            self._directory.public_venues(venue_ids) if venue_ids else {}
        )
        places = {p.id: p for p in store.places(actor, place_ids)} if place_ids else {}
        components = (
            {c.id: c for c in store.components(actor, component_ids)}
            if component_ids
            else {}
        )
        views: list[JumpView] = []
        for row in rows:
            if row.venue_id is not None:
                venue = venues.get(row.venue_id)
                location = Location(
                    "venue",
                    venue.id if venue else row.venue_id,
                    venue.name if venue else None,
                    venue.country if venue else None,
                    closed=bool(venue and venue.status.value == "closed"),
                )
            else:
                assert row.place_id is not None
                place = places.get(row.place_id)
                location = Location(
                    "place",
                    row.place_id,
                    place.name if place else None,
                    place.country if place else None,
                )
            views.append(
                JumpView(
                    row,
                    location,
                    [components[c] for c in row.component_ids if c in components],
                )
            )
        return views


def _values_of(jump: Jump) -> dict[str, Any]:
    return {
        "jumped_on": jump.jumped_on,
        "venue_id": jump.venue_id,
        "place_id": jump.place_id,
        "jump_type": jump.jump_type.value,
        "jump_number": jump.jump_number,
        "exit_time": jump.exit_time,
        "time_zone": jump.time_zone,
        "exit_altitude": jump.exit_altitude,
        "deployment_altitude": jump.deployment_altitude,
        "altitude_unit": jump.altitude_unit.value if jump.altitude_unit else None,
        "altitude_datum": jump.altitude_datum.value,
        "freefall_seconds": jump.freefall_seconds,
        "other_gear": jump.other_gear,
        "notes": jump.notes,
        "links": list(jump.links),
    }


def _check_filter(search: JumpFilter) -> None:
    if search.venue_id is not None and search.place_id is not None:
        raise RuleError("location_filter_invalid")
    if search.from_date and search.to_date and search.from_date > search.to_date:
        raise RuleError("date_range_invalid")
    low, high = search.number_from, search.number_to
    if low is not None and high is not None and low > high:
        raise RuleError("number_range_invalid")


def _after(cursor: str) -> tuple[date, uuid.UUID]:
    key, jump_id = decode_cursor(cursor)
    try:
        return date.fromisoformat(key), jump_id
    except ValueError:
        raise RuleError("cursor_invalid") from None


def _enum[E: StrEnum](kind: type[E], value: Any, field: str) -> E | None:
    if value is None or value == "":
        return None
    try:
        return kind(value)
    except ValueError:
        raise RuleError(f"{field}_invalid") from None
