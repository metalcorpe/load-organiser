"""Personal history summaries and the prior-history baseline (#154).

Owner-only. Every count derives from distinct detailed jump entries; posts, plans,
receipts and jump numbers never count. Equipment use comes only from components the
jumper explicitly recorded on a jump, on either side of the baseline date. The
baseline is a private self-report: it adds no dated activity, gear use, currency or
eligibility, and it is changed only by its owner (compare-and-swap on `version`),
with each declaration, correction and removal kept as private provenance.
"""

import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any, Literal, Protocol

from app.skydiver.access.policy import Actor
from app.skydiver.directory.service import DirectoryService, EditConflict, Venue
from app.skydiver.history import currency, licences, milestones, policy
from app.skydiver.history.currency import Currency, Licence
from app.skydiver.history.licences import Progress
from app.skydiver.history.milestones import Milestone
from app.skydiver.history.policy import Baseline, Totals
from app.skydiver.logbook.service import ComponentRef, Location, PlaceRef

EVENTS_SHOWN = 50


@dataclass(frozen=True)
class BaselineState:
    prior_jumps: int
    before_on: date
    source: str
    version: int
    updated_at: datetime


@dataclass(frozen=True)
class BaselineEvent:
    kind: str  # declared | corrected | removed
    detail: dict[str, Any]
    created_at: datetime


@dataclass(frozen=True)
class ComponentUse:
    component: ComponentRef
    jumps: int
    last_on: date


@dataclass(frozen=True)
class Summary:
    totals: Totals
    baseline: BaselineState | None
    first_jump_on: date | None
    last_jump_on: date | None
    months: list[tuple[str, int]]
    by_type: list[tuple[str, int]]
    by_location: list[tuple[Location, int]]
    by_component: list[ComponentUse]
    baseline_events: list[BaselineEvent]
    currency: Currency
    progress: Progress | None = None  # None without a licence


@dataclass(frozen=True)
class EntryRow:
    """What milestones need of one detailed entry."""

    id: uuid.UUID
    jumped_on: date
    jump_number: int | None
    exit_time: time | None
    jump_type: str
    freefall_seconds: int | None
    venue_id: uuid.UUID | None
    place_id: uuid.UUID | None


@dataclass(frozen=True)
class MilestoneView:
    milestone: Milestone
    location: Location | None  # for a first jump at a place


@dataclass(frozen=True)
class MilestoneList:
    items: list[MilestoneView]
    # How jump counts are numbered: entries only, after the declared prior jumps,
    # or not at all while the prior count disagrees with the entries.
    counted: Literal["entries", "with_prior", "unchecked"]


@dataclass(frozen=True)
class Preview:
    current: Totals
    proposed: Totals


class HistoryStore(Protocol):
    def snapshot(self) -> None:
        """Read everything after this from one consistent database snapshot."""
        ...

    def baseline(self, actor: Actor) -> BaselineState | None: ...
    def insert_baseline(self, actor: Actor, base: Baseline, now: datetime) -> bool:
        """False if one already exists (a concurrent declaration won)."""
        ...

    def update_baseline(
        self, actor: Actor, base: Baseline, now: datetime, *, expected_version: int
    ) -> None:
        """Compare-and-swap; raises EditConflict if the version moved."""
        ...

    def delete_baseline(self, actor: Actor, *, expected_version: int) -> None: ...
    def record(
        self, actor: Actor, kind: str, detail: dict[str, Any], now: datetime
    ) -> None: ...
    def events(self, actor: Actor, limit: int) -> list[BaselineEvent]:
        """Newest last."""
        ...

    def licence(self, actor: Actor) -> Licence:
        """The owner's stated licence; NONE when never set."""
        ...

    def set_licence(self, actor: Actor, licence: Licence, now: datetime) -> None:
        """Last write wins; NONE removes the setting."""
        ...

    def count_jumps(self, actor: Actor) -> int: ...
    def entries(self, actor: Actor) -> list[EntryRow]:
        """Every detailed entry of the owner (at most MAX_JUMPS), in no order."""
        ...

    def freefall(self, actor: Actor) -> tuple[int, int, int]:
        """(seconds, entries with a freefall time, entries without one)."""
        ...

    def count_before(self, actor: Actor, on: date) -> int: ...
    def date_range(self, actor: Actor) -> tuple[date | None, date | None]: ...
    def per_day_since(self, actor: Actor, start: date) -> dict[date, int]: ...
    def by_type(self, actor: Actor) -> list[tuple[str, int]]: ...
    def by_location(
        self, actor: Actor
    ) -> list[tuple[uuid.UUID | None, uuid.UUID | None, int]]:
        """(venue_id, place_id, jumps) as stored."""
        ...

    def by_component(self, actor: Actor) -> list[tuple[ComponentRef, int, date]]: ...
    def places(self, actor: Actor, place_ids: list[uuid.UUID]) -> list[PlaceRef]: ...


StoreFactory = Callable[[], AbstractContextManager[HistoryStore]]
Clock = Callable[[], datetime]


def _plain(base: Baseline | BaselineState) -> dict[str, Any]:
    return {"prior_jumps": base.prior_jumps, "before_on": base.before_on.isoformat()}


class HistoryService:
    def __init__(
        self, *, stores: StoreFactory, clock: Clock, directory: DirectoryService
    ) -> None:
        self._stores = stores
        self._clock = clock
        self._directory = directory

    def _latest_local_date(self) -> date:
        # The latest calendar date anywhere (UTC+14), as for jump dates.
        return (self._clock() + timedelta(hours=14)).date()

    # -- reads ------------------------------------------------------------------------

    def summary(self, actor: Actor) -> Summary:
        months = policy.recent_months(self._latest_local_date())
        start = date.fromisoformat(f"{months[0]}-01")
        with self._stores() as store:
            store.snapshot()
            state = store.baseline(actor)
            totals = self._totals(store, actor, state)
            first, last = store.date_range(actor)
            per_day = store.per_day_since(actor, start)
            by_type = store.by_type(actor)
            located = store.by_location(actor)
            uses = store.by_component(actor)
            place_ids = [p for _, p, _ in located if p is not None]
            places = {p.id: p for p in store.places(actor, place_ids)}
            events = store.events(actor, EVENTS_SHOWN)
            licence = store.licence(actor)
            seconds, with_time, without_time = store.freefall(actor)
        per_month = dict.fromkeys(months, 0)
        for day, jumps in per_day.items():
            key = f"{day.year:04d}-{day.month:02d}"
            if key in per_month:
                per_month[key] += jumps
        return Summary(
            totals=totals,
            baseline=state,
            first_jump_on=first,
            last_jump_on=last,
            months=list(per_month.items()),
            by_type=sorted(by_type, key=lambda t: (-t[1], t[0])),
            by_location=self._locations(located, places),
            by_component=sorted(
                (ComponentUse(c, n, on) for c, n, on in uses),
                key=lambda u: (-u.jumps, u.component.label.casefold()),
            ),
            baseline_events=events,
            # Only dated entries: a prior jump count adds no currency.
            currency=currency.currency(licence, last),
            # The reported total when it holds (prior jumps included), else the
            # entries; freefall time from entries only.
            progress=licences.progress(
                licence,
                jumps=totals.recorded if totals.lifetime is None else totals.lifetime,
                jumps_include_prior=totals.lifetime is not None,
                freefall_seconds=seconds,
                entries_with_freefall=with_time,
                entries_without_freefall=without_time,
            ),
        )

    def preview(self, actor: Actor, prior_jumps: int, before_on: date) -> Preview:
        """Totals now and with this declaration, without saving anything."""
        proposed = policy.baseline(prior_jumps, before_on, self._latest_local_date())
        with self._stores() as store:
            store.snapshot()
            state = store.baseline(actor)
            current = self._totals(store, actor, state)
            recorded = store.count_jumps(actor)
            before = store.count_before(actor, proposed.before_on)
        return Preview(current, policy.totals(recorded, before, proposed))

    def licence(self, actor: Actor) -> Licence:
        with self._stores() as store:
            return store.licence(actor)

    def milestones(self, actor: Actor) -> MilestoneList:
        """Derived on read: one query for the entries, one for their private
        places, one directory lookup for their dropzones. Nothing is stored."""
        with self._stores() as store:
            store.snapshot()
            state = store.baseline(actor)
            totals = self._totals(store, actor, state)
            rows = store.entries(actor)
            place_ids = sorted({r.place_id for r in rows if r.place_id is not None})
            places = {p.id: p for p in store.places(actor, place_ids)}
        venue_ids = sorted({r.venue_id for r in rows if r.venue_id is not None})
        venues = self._directory.public_venues(venue_ids) if venue_ids else {}
        found: dict[tuple[str, uuid.UUID], Location] = {}
        entries: list[milestones.Entry] = []
        for r in rows:
            loc = _location(r.venue_id, r.place_id, venues, places)
            found[(loc.kind, loc.id)] = loc
            entries.append(
                milestones.Entry(
                    id=r.id,
                    jumped_on=r.jumped_on,
                    jump_number=r.jump_number,
                    exit_time=r.exit_time,
                    jump_type=r.jump_type,
                    freefall_seconds=r.freefall_seconds,
                    place=(loc.kind, loc.id),
                )
            )
        unchecked = totals.inconsistent
        prior = (
            milestones.Prior(state.prior_jumps, state.before_on)
            if state is not None and not unchecked
            else None
        )
        items = milestones.milestones(entries, prior=prior, count_jumps=not unchecked)
        return MilestoneList(
            items=[
                MilestoneView(m, found.get(m.place) if m.place else None) for m in items
            ],
            counted="unchecked" if unchecked else "with_prior" if prior else "entries",
        )

    # -- writes -----------------------------------------------------------------------

    def set_licence(self, actor: Actor, licence: Licence) -> Licence:
        """A private self-statement for currency guidance; never verified."""
        now = self._clock()
        with self._stores() as store:
            store.set_licence(actor, licence, now)
        return licence

    def set_baseline(
        self,
        actor: Actor,
        prior_jumps: int,
        before_on: date,
        *,
        expected_version: int | None,
    ) -> Summary:
        """Declare (no version) or correct (the version it was based on)."""
        base = policy.baseline(prior_jumps, before_on, self._latest_local_date())
        now = self._clock()
        with self._stores() as store:
            current = store.baseline(actor)
            if current is None:
                # A version names a declaration that has since been removed.
                if expected_version is not None:
                    raise EditConflict()
                if not store.insert_baseline(actor, base, now):
                    raise EditConflict()
                store.record(
                    actor, "declared", _plain(base) | {"source": "manual"}, now
                )
            else:
                if expected_version != current.version:
                    raise EditConflict()
                if _plain(current) != _plain(base):
                    store.update_baseline(
                        actor, base, now, expected_version=current.version
                    )
                    store.record(
                        actor,
                        "corrected",
                        {"from": _plain(current), "to": _plain(base)},
                        now,
                    )
        return self.summary(actor)

    def remove_baseline(self, actor: Actor, *, expected_version: int) -> None:
        now = self._clock()
        with self._stores() as store:
            current = store.baseline(actor)
            if current is None or current.version != expected_version:
                raise EditConflict()
            store.delete_baseline(actor, expected_version=expected_version)
            store.record(actor, "removed", {"from": _plain(current)}, now)

    # -- helpers ----------------------------------------------------------------------

    @staticmethod
    def _totals(
        store: HistoryStore, actor: Actor, state: BaselineState | None
    ) -> Totals:
        recorded = store.count_jumps(actor)
        if state is None:
            return policy.totals(recorded, 0, None)
        base = Baseline(state.prior_jumps, state.before_on)
        return policy.totals(recorded, store.count_before(actor, base.before_on), base)

    def _locations(
        self,
        located: list[tuple[uuid.UUID | None, uuid.UUID | None, int]],
        places: dict[uuid.UUID, PlaceRef],
    ) -> list[tuple[Location, int]]:
        venue_ids = [v for v, _, _ in located if v is not None]
        venues = self._directory.public_venues(venue_ids) if venue_ids else {}
        counts: dict[tuple[str, uuid.UUID], int] = {}
        found: dict[tuple[str, uuid.UUID], Location] = {}
        for venue_id, place_id, jumps in located:
            loc = _location(venue_id, place_id, venues, places)
            key = (loc.kind, loc.id)
            found[key] = loc
            counts[key] = counts.get(key, 0) + jumps
        return sorted(
            ((found[k], n) for k, n in counts.items()),
            key=lambda item: (-item[1], (item[0].name or "").casefold()),
        )


def _location(
    venue_id: uuid.UUID | None,
    place_id: uuid.UUID | None,
    venues: dict[uuid.UUID, Venue],
    places: dict[uuid.UUID, PlaceRef],
) -> Location:
    if venue_id is not None:
        venue = venues.get(venue_id)
        # Venues merged since are counted under the venue they resolve to.
        return Location(
            "venue",
            venue.id if venue else venue_id,
            venue.name if venue else None,
            venue.country if venue else None,
            closed=bool(venue and venue.status.value == "closed"),
        )
    assert place_id is not None
    place = places.get(place_id)
    return Location(
        "place",
        place_id,
        place.name if place else None,
        place.country if place else None,
    )
