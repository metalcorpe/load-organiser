"""Private saved opportunities and visit plans (#150).

Owner-only records. A save is a bookmark, not registration or attendance; a plan is
the person's own dated intention and is never shared, published or turned into a
jump. Public listing and venue state is read through their own services, so a
withdrawn listing shows as unavailable rather than leaking its non-public state.
"""

import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Protocol

from app.skydiver.access.policy import Actor
from app.skydiver.directory import policy as directory_policy
from app.skydiver.directory.policy import DirectoryRuleError as RuleError
from app.skydiver.directory.service import DirectoryService, Place, Venue
from app.skydiver.directory.service import NotFound as VenueNotFound
from app.skydiver.opportunities.service import (
    Opportunity,
    OpportunityService,
    Resolved,
)

# Working caps per person (design defaults, not measured capacity).
MAX_SAVED = 200
MAX_PLANS = 100
TITLE_MAX = 120
NOTE_MAX = 500
PLAN_SPAN_MAX_DAYS = 366


class NotFound(Exception):
    """Absent and foreign records alike."""


class LimitReached(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class SavedRow:
    opportunity_id: uuid.UUID
    title: str
    saved_at: datetime


@dataclass(frozen=True)
class Saved:
    opportunity_id: uuid.UUID
    title: str
    saved_at: datetime
    # The listing's current public state, or None once it is no longer public.
    current: Resolved[Opportunity] | None


@dataclass(frozen=True)
class PlanRow:
    id: uuid.UUID
    title: str
    starts_on: date
    ends_on: date
    note: str | None
    opportunity_id: uuid.UUID | None
    venue_id: uuid.UUID | None
    place_id: uuid.UUID | None
    updated_at: datetime


@dataclass(frozen=True)
class Plan:
    row: PlanRow
    opportunity: Resolved[Opportunity] | None
    venue: Venue | None
    place: Place | None


class SavesStore(Protocol):
    def lock_owner(self, actor: Actor) -> None: ...
    def list_saved(self, actor: Actor) -> list[SavedRow]: ...
    def get_saved(self, actor: Actor, opportunity_id: uuid.UUID) -> SavedRow | None: ...
    def count_saved(self, actor: Actor) -> int: ...
    def insert_saved(
        self, actor: Actor, opportunity_id: uuid.UUID, title: str, now: datetime
    ) -> None: ...
    def delete_saved(self, actor: Actor, opportunity_id: uuid.UUID) -> None: ...
    def owns_place(self, actor: Actor, place_id: uuid.UUID) -> bool: ...
    def list_plans(self, actor: Actor) -> list[PlanRow]: ...
    def get_plan(
        self, actor: Actor, plan_id: uuid.UUID, *, lock: bool = False
    ) -> PlanRow | None: ...
    def count_plans(self, actor: Actor) -> int: ...
    def insert_plan(
        self, actor: Actor, values: dict[str, Any], now: datetime
    ) -> uuid.UUID: ...
    def update_plan(
        self, actor: Actor, plan_id: uuid.UUID, values: dict[str, Any], now: datetime
    ) -> None: ...
    def delete_plan(self, actor: Actor, plan_id: uuid.UUID) -> None: ...


StoreFactory = Callable[[], AbstractContextManager[SavesStore]]
Clock = Callable[[], datetime]
_LINKS = ("opportunity_id", "venue_id", "place_id")


class SavesService:
    def __init__(
        self,
        *,
        stores: StoreFactory,
        clock: Clock,
        opportunities: OpportunityService,
        directory: DirectoryService,
    ) -> None:
        self._stores = stores
        self._clock = clock
        self._opportunities = opportunities
        self._directory = directory

    # -- saved opportunities --------------------------------------------------------

    def list_saved(self, actor: Actor) -> list[Saved]:
        with self._stores() as store:
            rows = store.list_saved(actor)
        current = self._opportunities.public_opportunities(
            [r.opportunity_id for r in rows]
        )
        return [
            Saved(r.opportunity_id, r.title, r.saved_at, current[r.opportunity_id])
            for r in rows
        ]

    def saved(self, actor: Actor, opportunity_id: uuid.UUID) -> SavedRow:
        with self._stores() as store:
            row = store.get_saved(actor, opportunity_id)
        if row is None:
            raise NotFound()
        return row

    def save(self, actor: Actor, opportunity_id: uuid.UUID) -> tuple[SavedRow, bool]:
        """Idempotent: saving again returns the existing bookmark (created=False)."""
        found = self._opportunities.public_opportunities([opportunity_id])[
            opportunity_id
        ]
        if found is None:
            raise NotFound()  # drafts and withdrawn listings are not disclosed
        listing = found.value.row
        now = self._clock()
        with self._stores() as store:
            store.lock_owner(actor)
            existing = store.get_saved(actor, listing.id)
            if existing is not None:
                return existing, False
            if store.count_saved(actor) >= MAX_SAVED:
                raise LimitReached("saved_limit_reached")
            store.insert_saved(actor, listing.id, listing.title, now)
            row = store.get_saved(actor, listing.id)
        assert row is not None
        return row, True

    def unsave(self, actor: Actor, opportunity_id: uuid.UUID) -> None:
        """Idempotent: removing a bookmark that is not there is not an error."""
        with self._stores() as store:
            store.delete_saved(actor, opportunity_id)

    # -- visit plans --------------------------------------------------------------

    def list_plans(self, actor: Actor) -> list[Plan]:
        with self._stores() as store:
            rows = store.list_plans(actor)
        return self._plans(actor, rows)

    def create_plan(self, actor: Actor, fields: dict[str, Any]) -> Plan:
        values = _plan_values(fields)
        for required in ("title", "starts_on", "ends_on"):
            if values.get(required) is None:
                raise RuleError(f"{required}_required")
        full = {"note": None, **dict.fromkeys(_LINKS), **values}
        _check_plan(full)
        full |= self._resolve_links(full, only=set(values) & set(_LINKS))
        now = self._clock()
        with self._stores() as store:
            store.lock_owner(actor)
            if store.count_plans(actor) >= MAX_PLANS:
                raise LimitReached("plan_limit_reached")
            self._check_place(store, actor, full["place_id"])
            plan_id = store.insert_plan(actor, full, now)
            row = store.get_plan(actor, plan_id)
        assert row is not None
        return self._plans(actor, [row])[0]

    def update_plan(
        self, actor: Actor, plan_id: uuid.UUID, fields: dict[str, Any]
    ) -> Plan:
        values = _plan_values(fields)
        changed_links = set(values) & set(_LINKS)
        values |= self._resolve_links(values, only=changed_links)
        now = self._clock()
        with self._stores() as store:
            current = store.get_plan(actor, plan_id, lock=True)
            if current is None:
                raise NotFound()
            before = {
                "title": current.title,
                "starts_on": current.starts_on,
                "ends_on": current.ends_on,
                "note": current.note,
                "opportunity_id": current.opportunity_id,
                "venue_id": current.venue_id,
                "place_id": current.place_id,
            }
            full = {**before, **values}
            _check_plan(full)
            if "place_id" in changed_links:
                self._check_place(store, actor, full["place_id"])
            changed = {k: v for k, v in values.items() if before[k] != v}
            if changed:
                store.update_plan(actor, plan_id, changed, now)
            row = store.get_plan(actor, plan_id)
        assert row is not None
        return self._plans(actor, [row])[0]

    def delete_plan(self, actor: Actor, plan_id: uuid.UUID) -> None:
        with self._stores() as store:
            if store.get_plan(actor, plan_id, lock=True) is None:
                raise NotFound()
            store.delete_plan(actor, plan_id)

    # -- helpers ------------------------------------------------------------------

    def _resolve_links(
        self, values: dict[str, Any], *, only: set[str]
    ) -> dict[str, Any]:
        """Links to public records are stored as their current surviving IDs."""
        resolved: dict[str, Any] = {}
        if (
            opportunity_id := values.get("opportunity_id")
        ) and "opportunity_id" in only:
            found = self._opportunities.public_opportunities([opportunity_id])[
                opportunity_id
            ]
            if found is None:
                raise RuleError("opportunity_unavailable")
            resolved["opportunity_id"] = found.value.row.id
        if (venue_id := values.get("venue_id")) and "venue_id" in only:
            try:
                resolved["venue_id"] = self._directory.public_venue(venue_id).venue.id
            except VenueNotFound:
                raise RuleError("venue_not_listed") from None
        return resolved

    @staticmethod
    def _check_place(
        store: SavesStore, actor: Actor, place_id: uuid.UUID | None
    ) -> None:
        if place_id is not None and not store.owns_place(actor, place_id):
            raise RuleError("place_unknown")  # foreign and absent alike

    def _plans(self, actor: Actor, rows: list[PlanRow]) -> list[Plan]:
        opportunity_ids = [r.opportunity_id for r in rows if r.opportunity_id]
        venue_ids = [r.venue_id for r in rows if r.venue_id]
        opportunities = (
            self._opportunities.public_opportunities(opportunity_ids)
            if opportunity_ids
            else {}
        )
        venues = self._directory.public_venues(venue_ids) if venue_ids else {}
        places = (
            {p.id: p for p in self._directory.list_places(actor)}
            if any(r.place_id for r in rows)
            else {}
        )
        return [
            Plan(
                row=r,
                opportunity=opportunities.get(r.opportunity_id)
                if r.opportunity_id
                else None,
                venue=venues.get(r.venue_id) if r.venue_id else None,
                place=places.get(r.place_id) if r.place_id else None,
            )
            for r in rows
        ]


def _plan_values(raw: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    if "title" in raw:
        values["title"] = directory_policy.clean_text(
            raw["title"] or "", field="title", maximum=TITLE_MAX
        )
    for name in ("starts_on", "ends_on"):
        if name in raw:
            if raw[name] is None:
                raise RuleError("dates_required")
            values[name] = raw[name]
    if "note" in raw:
        values["note"] = directory_policy.optional_text(
            raw["note"], field="note", maximum=NOTE_MAX
        )
    for name in _LINKS:
        if name in raw:
            values[name] = raw[name]
    return values


def _check_plan(full: dict[str, Any]) -> None:
    if full["ends_on"] < full["starts_on"]:
        raise RuleError("dates_out_of_order")
    if (full["ends_on"] - full["starts_on"]).days >= PLAN_SPAN_MAX_DAYS:
        raise RuleError("dates_span_too_long")
    if sum(full[name] is not None for name in _LINKS) > 1:
        raise RuleError("plan_link_conflict")
