"""Provider and opportunity use cases (#149). Ports are injected; no FastAPI or SQL.

Public reads see published providers and published/postponed/cancelled opportunities.
Reviewers (server-granted role) maintain both; every change is recorded as a
reviewer-only event. Public results never carry reviewer accounts or history.
"""

import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Protocol

from app.skydiver.access.policy import Actor
from app.skydiver.directory import policy as directory_policy
from app.skydiver.directory.policy import DirectoryRuleError as RuleError
from app.skydiver.directory.service import decode_cursor, encode_cursor
from app.skydiver.opportunities import policy
from app.skydiver.opportunities.policy import (
    PUBLIC_PROVIDER_STATUSES,
    PUBLIC_STATUSES,
    Audience,
    Category,
    Discipline,
    OpportunityStatus,
    ProviderKind,
    ProviderStatus,
)

MAX_REDIRECT_HOPS = 16


class NotFound(Exception):
    """Absent, or not public for a public read: indistinguishable."""


@dataclass(frozen=True)
class VenueRef:
    """A public (listed or closed) venue after merge resolution."""

    id: uuid.UUID
    name: str
    country: str
    locality: str | None
    closed: bool


@dataclass(frozen=True)
class Provider:
    id: uuid.UUID
    name: str
    kind: ProviderKind
    country: str | None
    website_url: str | None
    status: ProviderStatus
    merged_into_id: uuid.UUID | None
    source_url: str | None
    source_note: str | None
    checked_on: date | None
    updated_at: datetime


@dataclass(frozen=True)
class OpportunityRow:
    """Stored values; references are raw IDs."""

    id: uuid.UUID
    title: str
    category: Category
    provider_id: uuid.UUID
    venue_id: uuid.UUID | None
    country: str
    location_note: str | None
    starts_on: date | None
    ends_on: date | None
    time_zone: str | None
    expires_at: datetime | None
    disciplines: tuple[str, ...]
    audience: tuple[str, ...]
    languages: tuple[str, ...]
    summary: str | None
    prerequisites: str | None
    price_amount: Decimal | None
    price_currency: str | None
    price_basis: str | None
    price_note: str | None
    registration_url: str | None
    source_url: str | None
    source_note: str | None
    checked_on: date | None
    status: OpportunityStatus
    duplicate_of_id: uuid.UUID | None
    updated_at: datetime


@dataclass(frozen=True)
class Opportunity:
    row: OpportunityRow
    provider: Provider
    venue: VenueRef | None  # public venue, merge-resolved; None if unlinked or hidden
    ended: bool


@dataclass(frozen=True)
class ListingEvent:
    kind: str
    detail: dict[str, Any]
    created_at: datetime


@dataclass(frozen=True)
class OpportunityPage:
    items: list[Opportunity]
    next_cursor: str | None


@dataclass(frozen=True)
class Resolved[T]:
    value: T
    replaced_id: uuid.UUID | None = None


@dataclass(frozen=True)
class OpportunityFilter:
    query: str | None = None
    category: str | None = None
    country: str | None = None
    discipline: str | None = None
    audience: str | None = None
    provider_id: uuid.UUID | None = None
    venue_id: uuid.UUID | None = None
    starts_from: date | None = None
    starts_until: date | None = None


@dataclass(frozen=True)
class SearchQuery:
    """Validated filter handed to the store."""

    key: str
    category: str | None
    country: str | None
    discipline: str | None
    audience: str | None
    provider_id: uuid.UUID | None
    venue_id: uuid.UUID | None
    starts_from: date | None
    starts_until: date | None
    now: datetime


PROVIDER_FIELDS = (
    "name",
    "kind",
    "country",
    "website_url",
    "source_url",
    "source_note",
    "checked_on",
)
OPPORTUNITY_FIELDS = (
    "title",
    "category",
    "provider_id",
    "venue_id",
    "country",
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
    "source_note",
    "checked_on",
)
_SCHEDULE = {"starts_on", "ends_on", "time_zone"}


class ListingStore(Protocol):
    def get_provider(
        self, provider_id: uuid.UUID, *, lock: bool = False
    ) -> Provider | None: ...
    def insert_provider(self, values: dict[str, Any], now: datetime) -> uuid.UUID: ...
    def update_provider(
        self, provider_id: uuid.UUID, values: dict[str, Any], now: datetime
    ) -> None: ...
    def count_live_opportunities(self, provider_id: uuid.UUID, now: datetime) -> int:
        """Public opportunities of the provider that have not ended."""
        ...

    def reassign_provider(
        self, source_id: uuid.UUID, target_id: uuid.UUID, now: datetime
    ) -> list[uuid.UUID]: ...

    def get_opportunity(
        self, opportunity_id: uuid.UUID, *, lock: bool = False
    ) -> OpportunityRow | None: ...
    def insert_opportunity(
        self, values: dict[str, Any], now: datetime
    ) -> uuid.UUID: ...
    def update_opportunity(
        self, opportunity_id: uuid.UUID, values: dict[str, Any], now: datetime
    ) -> None: ...
    def search(
        self, query: SearchQuery, after: tuple[str, uuid.UUID] | None, limit: int
    ) -> list[OpportunityRow]:
        """Public, not-ended opportunities ordered by (sort_on, id)."""
        ...

    def public_venue(self, venue_id: uuid.UUID) -> VenueRef | None:
        """The listed/closed venue `venue_id` resolves to through merges, if any."""
        ...

    def record_event(
        self,
        *,
        provider_id: uuid.UUID | None = None,
        opportunity_id: uuid.UUID | None = None,
        kind: str,
        detail: dict[str, Any],
        actor: Actor,
        now: datetime,
    ) -> None: ...
    def provider_events(self, provider_id: uuid.UUID) -> list[ListingEvent]: ...
    def opportunity_events(self, opportunity_id: uuid.UUID) -> list[ListingEvent]: ...


StoreFactory = Callable[[], AbstractContextManager[ListingStore]]
Clock = Callable[[], datetime]


class OpportunityService:
    def __init__(self, *, stores: StoreFactory, clock: Clock) -> None:
        self._stores = stores
        self._clock = clock

    # -- public -------------------------------------------------------------------

    def search(
        self, filters: OpportunityFilter, *, cursor: str | None, limit: int | None
    ) -> OpportunityPage:
        now = self._clock()
        query = SearchQuery(
            key=directory_policy.search_key(filters.query or "")[
                : directory_policy.QUERY_MAX
            ],
            category=_enum(Category, filters.category, "category"),
            country=directory_policy.country_code(filters.country)
            if filters.country
            else None,
            discipline=_enum(Discipline, filters.discipline, "discipline"),
            audience=_enum(Audience, filters.audience, "audience"),
            provider_id=filters.provider_id,
            venue_id=filters.venue_id,
            starts_from=filters.starts_from,
            starts_until=filters.starts_until,
            now=now,
        )
        if (
            query.starts_from
            and query.starts_until
            and query.starts_until < query.starts_from
        ):
            raise RuleError("dates_out_of_order")
        after = _decode(cursor) if cursor else None
        size = directory_policy.page_size(limit)
        with self._stores() as store:
            if query.venue_id is not None and (
                venue := store.public_venue(query.venue_id)
            ):
                query = replace(query, venue_id=venue.id)  # filter by the survivor
            if query.provider_id is not None and (
                provider := self._resolve_provider(store, query.provider_id)
            ):
                query = replace(query, provider_id=provider.id)
            rows = store.search(query, after, size + 1)
            items = [self._public(store, row, now) for row in rows[:size]]
        next_cursor = None
        if len(rows) > size:
            last = rows[size - 1]
            next_cursor = encode_cursor(
                policy.sort_on(last.starts_on).isoformat(), last.id
            )
        return OpportunityPage(items=items, next_cursor=next_cursor)

    def public_opportunity(self, opportunity_id: uuid.UUID) -> Resolved[Opportunity]:
        """Ended opportunities stay readable by ID, labelled ended; drafts do not."""
        found = self.public_opportunities([opportunity_id])[opportunity_id]
        if found is None:
            raise NotFound()
        return found

    def public_opportunities(
        self, opportunity_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, Resolved[Opportunity] | None]:
        """Current public state of each ID (None when not public), in one session."""
        now = self._clock()
        found: dict[uuid.UUID, Resolved[Opportunity] | None] = {}
        with self._stores() as store:
            for opportunity_id in opportunity_ids:
                row = store.get_opportunity(opportunity_id)
                hops = 0
                while row is not None and (target := row.duplicate_of_id) is not None:
                    hops += 1
                    row = (
                        store.get_opportunity(target)
                        if hops <= MAX_REDIRECT_HOPS
                        else None
                    )
                if row is None or row.status not in PUBLIC_STATUSES:
                    found[opportunity_id] = None
                    continue
                found[opportunity_id] = Resolved(
                    self._public(store, row, now),
                    opportunity_id if row.id != opportunity_id else None,
                )
        return found

    def public_provider(self, provider_id: uuid.UUID) -> Resolved[Provider]:
        with self._stores() as store:
            provider = self._resolve_provider(store, provider_id)
        if provider is None or provider.status not in PUBLIC_PROVIDER_STATUSES:
            raise NotFound()
        return Resolved(provider, provider_id if provider.id != provider_id else None)

    # -- reviewer: providers --------------------------------------------------------

    def reviewer_provider(
        self, provider_id: uuid.UUID
    ) -> tuple[Provider, list[ListingEvent]]:
        with self._stores() as store:
            provider = store.get_provider(provider_id)
            if provider is None:
                raise NotFound()
            return provider, store.provider_events(provider_id)

    def create_provider(
        self, actor: Actor, fields: dict[str, Any], *, publish: bool
    ) -> Provider:
        now = self._clock()
        values = _provider_values(fields, now)
        for required in ("name", "kind"):
            if required not in values:
                raise RuleError(f"{required}_required")
        status = ProviderStatus.PUBLISHED if publish else ProviderStatus.DRAFT
        _require_provider_source(status, values)
        values["status"] = status.value
        with self._stores() as store:
            provider_id = store.insert_provider(values, now)
            store.record_event(
                provider_id=provider_id,
                kind="created",
                detail={"status": status.value},
                actor=actor,
                now=now,
            )
            provider = store.get_provider(provider_id)
        assert provider is not None
        return provider

    def update_provider(
        self, actor: Actor, provider_id: uuid.UUID, fields: dict[str, Any]
    ) -> Provider:
        now = self._clock()
        values = _provider_values(fields, now)
        with self._stores() as store:
            current = store.get_provider(provider_id, lock=True)
            if current is None:
                raise NotFound()
            if current.status is ProviderStatus.MERGED:
                raise RuleError("provider_merged")
            before = _provider_dict(current)
            _require_provider_source(current.status, {**before, **values})
            changed = {k: v for k, v in values.items() if before[k] != v}
            if changed:
                store.update_provider(provider_id, changed, now)
                store.record_event(
                    provider_id=provider_id,
                    kind="updated",
                    detail={k: _json(v) for k, v in sorted(changed.items())},
                    actor=actor,
                    now=now,
                )
            provider = store.get_provider(provider_id)
        assert provider is not None
        return provider

    def set_provider_status(
        self, actor: Actor, provider_id: uuid.UUID, status: ProviderStatus
    ) -> Provider:
        now = self._clock()
        with self._stores() as store:
            current = store.get_provider(provider_id, lock=True)
            if current is None:
                raise NotFound()
            if current.status is status:
                return current
            policy.check_provider_transition(current.status, status)
            _require_provider_source(status, _provider_dict(current))
            if status not in PUBLIC_PROVIDER_STATUSES and (
                store.count_live_opportunities(provider_id, now) > 0
            ):
                # Public listings must keep a public organiser until they end or move.
                raise RuleError("provider_in_use")
            store.update_provider(provider_id, {"status": status.value}, now)
            store.record_event(
                provider_id=provider_id,
                kind="status_changed",
                detail={"from": current.status.value, "to": status.value},
                actor=actor,
                now=now,
            )
            provider = store.get_provider(provider_id)
        assert provider is not None
        return provider

    def merge_providers(
        self, actor: Actor, source_id: uuid.UUID, target_id: uuid.UUID
    ) -> Provider:
        """Reviewed duplicate merge: listings move to the target; the source redirects."""
        now = self._clock()
        with self._stores() as store:
            first, second = sorted((source_id, target_id))
            locked = {first: store.get_provider(first, lock=True)}
            if second != first:
                locked[second] = store.get_provider(second, lock=True)
            source, target = locked.get(source_id), locked.get(target_id)
            if source is None or target is None:
                raise NotFound()
            policy.check_provider_merge(
                policy.ProviderMergeCheck(
                    source_status=source.status,
                    target_status=target.status,
                    same=source_id == target_id,
                )
            )
            moved = store.reassign_provider(source_id, target_id, now)
            store.update_provider(
                source_id,
                {"status": ProviderStatus.MERGED.value, "merged_into_id": target_id},
                now,
            )
            store.record_event(
                provider_id=source_id,
                kind="merged_into",
                detail={"target": str(target_id)},
                actor=actor,
                now=now,
            )
            store.record_event(
                provider_id=target_id,
                kind="merged_from",
                detail={"source": str(source_id), "name": source.name},
                actor=actor,
                now=now,
            )
            for opportunity_id in moved:
                store.record_event(
                    opportunity_id=opportunity_id,
                    kind="provider_merged",
                    detail={"from": str(source_id), "to": str(target_id)},
                    actor=actor,
                    now=now,
                )
            provider = store.get_provider(target_id)
        assert provider is not None
        return provider

    # -- reviewer: opportunities ----------------------------------------------------

    def reviewer_opportunity(
        self, opportunity_id: uuid.UUID
    ) -> tuple[OpportunityRow, list[ListingEvent]]:
        with self._stores() as store:
            row = store.get_opportunity(opportunity_id)
            if row is None:
                raise NotFound()
            return row, store.opportunity_events(opportunity_id)

    def create_opportunity(
        self, actor: Actor, fields: dict[str, Any]
    ) -> OpportunityRow:
        """New listings start as drafts; publication is an explicit status change."""
        now = self._clock()
        values = self._opportunity_values(fields, now)
        for required in ("title", "category", "provider_id", "country"):
            if values.get(required) is None:
                raise RuleError(f"{required}_required")
        full = {**_EMPTY_OPPORTUNITY, **values}
        _check_shape(full)
        values = {k: full[k] for k in values} | _derived(full)
        values["status"] = OpportunityStatus.DRAFT.value
        with self._stores() as store:
            values["provider_id"] = self._lock_provider(store, values["provider_id"])
            values["venue_id"] = self._linkable_venue(store, values.get("venue_id"))
            opportunity_id = store.insert_opportunity(values, now)
            store.record_event(
                opportunity_id=opportunity_id,
                kind="created",
                detail={"status": OpportunityStatus.DRAFT.value},
                actor=actor,
                now=now,
            )
            row = store.get_opportunity(opportunity_id)
        assert row is not None
        return row

    def update_opportunity(
        self, actor: Actor, opportunity_id: uuid.UUID, fields: dict[str, Any]
    ) -> OpportunityRow:
        now = self._clock()
        values = self._opportunity_values(fields, now)
        with self._stores() as store:
            if "provider_id" in values:
                values["provider_id"] = self._existing_provider(
                    store, values["provider_id"]
                )
            current = self._lock_listing(
                store, opportunity_id, values.get("provider_id")
            )
            if current.status is OpportunityStatus.DUPLICATE:
                raise RuleError("opportunity_duplicate")
            before = _opportunity_dict(current)
            if "venue_id" in values:
                values["venue_id"] = self._linkable_venue(store, values["venue_id"])
            full = {**before, **values}
            _check_shape(full)
            changed = {k: full[k] for k in values if before[k] != full[k]}
            if not changed:
                return current
            self._check_public(store, current.status, full)
            if _SCHEDULE & set(changed):
                changed.update(_derived(full))
            store.update_opportunity(opportunity_id, changed, now)
            self._record_changes(store, opportunity_id, before, changed, actor, now)
            row = store.get_opportunity(opportunity_id)
        assert row is not None
        return row

    def set_opportunity_status(
        self, actor: Actor, opportunity_id: uuid.UUID, status: OpportunityStatus
    ) -> OpportunityRow:
        now = self._clock()
        with self._stores() as store:
            current = self._lock_listing(store, opportunity_id)
            if current.status is status:
                return current
            policy.check_transition(current.status, status)
            full = _opportunity_dict(current)
            changes: dict[str, Any] = {"status": status.value}
            if status is OpportunityStatus.POSTPONED and full["starts_on"] is not None:
                # The announced dates no longer hold: clear them so the listing
                # neither expires on nor shows the old schedule. History keeps them.
                cleared = {"starts_on": None, "ends_on": None}
                changes |= cleared | _derived({**full, **cleared})
                self._record_changes(store, opportunity_id, full, cleared, actor, now)
                full |= cleared
            self._check_public(store, status, full)
            store.update_opportunity(opportunity_id, changes, now)
            store.record_event(
                opportunity_id=opportunity_id,
                kind="status_changed",
                detail={"from": current.status.value, "to": status.value},
                actor=actor,
                now=now,
            )
            row = store.get_opportunity(opportunity_id)
        assert row is not None
        return row

    def mark_duplicate(
        self, actor: Actor, source_id: uuid.UUID, target_id: uuid.UUID
    ) -> OpportunityRow:
        """Consolidate a duplicate listing; its ID keeps resolving to the target."""
        now = self._clock()
        with self._stores() as store:
            first, second = sorted((source_id, target_id))
            locked = {first: store.get_opportunity(first, lock=True)}
            if second != first:
                locked[second] = store.get_opportunity(second, lock=True)
            source, target = locked.get(source_id), locked.get(target_id)
            if source is None or target is None:
                raise NotFound()
            policy.check_duplicate(
                policy.DuplicateCheck(
                    source_status=source.status,
                    target_status=target.status,
                    same=source_id == target_id,
                )
            )
            store.update_opportunity(
                source_id,
                {
                    "status": OpportunityStatus.DUPLICATE.value,
                    "duplicate_of_id": target_id,
                },
                now,
            )
            store.record_event(
                opportunity_id=source_id,
                kind="duplicate_of",
                detail={"target": str(target_id), "previous": source.status.value},
                actor=actor,
                now=now,
            )
            store.record_event(
                opportunity_id=target_id,
                kind="duplicate_absorbed",
                detail={"source": str(source_id), "source_url": source.source_url},
                actor=actor,
                now=now,
            )
            row = store.get_opportunity(target_id)
        assert row is not None
        return row

    # -- helpers ------------------------------------------------------------------

    def _public(
        self, store: ListingStore, row: OpportunityRow, now: datetime
    ) -> Opportunity:
        provider = self._resolve_provider(store, row.provider_id)
        assert provider is not None  # provider_id is a non-null foreign key
        venue = store.public_venue(row.venue_id) if row.venue_id else None
        ended = row.expires_at is not None and row.expires_at <= now
        return Opportunity(row=row, provider=provider, venue=venue, ended=ended)

    def _resolve_provider(
        self, store: ListingStore, provider_id: uuid.UUID
    ) -> Provider | None:
        provider = store.get_provider(provider_id)
        hops = 0
        while provider is not None and provider.merged_into_id is not None:
            hops += 1
            if hops > MAX_REDIRECT_HOPS:
                return None
            provider = store.get_provider(provider.merged_into_id)
        return provider

    def _existing_provider(
        self, store: ListingStore, provider_id: uuid.UUID
    ) -> uuid.UUID:
        provider = self._resolve_provider(store, provider_id)
        if provider is None:
            raise RuleError("provider_unknown")
        return provider.id

    def _lock_provider(self, store: ListingStore, provider_id: uuid.UUID) -> uuid.UUID:
        """Resolve and lock a provider so archiving or merging it waits for us."""
        resolved = self._existing_provider(store, provider_id)
        locked = store.get_provider(resolved, lock=True)
        if locked is None or locked.merged_into_id is not None:
            raise RuleError("opportunity_changed")  # merged meanwhile; retry
        return resolved

    def _lock_listing(
        self,
        store: ListingStore,
        opportunity_id: uuid.UUID,
        new_provider: uuid.UUID | None = None,
    ) -> OpportunityRow:
        """Lock providers before the listing: the order merges and archiving use."""
        peek = store.get_opportunity(opportunity_id)
        if peek is None:
            raise NotFound()
        for provider_id in sorted({peek.provider_id, new_provider or peek.provider_id}):
            if provider_id == new_provider:
                self._lock_provider(store, provider_id)
            else:
                store.get_provider(provider_id, lock=True)
        current = store.get_opportunity(opportunity_id, lock=True)
        if current is None:
            raise NotFound()
        if current.provider_id != peek.provider_id:
            raise RuleError("opportunity_changed")  # a provider merge moved it; retry
        return current

    def _check_public(
        self, store: ListingStore, status: OpportunityStatus, full: dict[str, Any]
    ) -> None:
        if status not in PUBLIC_STATUSES:
            return
        provider = store.get_provider(full["provider_id"])
        venue_public = full["venue_id"] is not None and (
            store.public_venue(full["venue_id"]) is not None
        )
        policy.check_publishable(
            policy.PublicationFacts(
                status=status,
                has_source=bool(full["source_url"] and full["checked_on"]),
                has_registration=bool(full["registration_url"]),
                has_dates=full["starts_on"] is not None,
                has_location=venue_public or bool(full["location_note"]),
                provider_public=provider is not None
                and provider.status in PUBLIC_PROVIDER_STATUSES,
            )
        )

    def _opportunity_values(self, raw: dict[str, Any], now: datetime) -> dict[str, Any]:
        values: dict[str, Any] = {}
        text = directory_policy.clean_text
        optional = directory_policy.optional_text
        if "title" in raw:
            values["title"] = text(
                raw["title"] or "", field="title", maximum=policy.TITLE_MAX
            )
        if "category" in raw:
            values["category"] = _enum(Category, raw["category"] or "", "category")
        if "provider_id" in raw:
            if raw["provider_id"] is None:
                raise RuleError("provider_id_required")
            values["provider_id"] = raw["provider_id"]
        if "venue_id" in raw:
            values["venue_id"] = raw["venue_id"]  # resolved in the store transaction
        if "country" in raw:
            values["country"] = directory_policy.country_code(raw["country"] or "")
        for name, maximum in (
            ("location_note", policy.LOCATION_NOTE_MAX),
            ("summary", policy.SUMMARY_MAX),
            ("prerequisites", policy.PREREQUISITES_MAX),
            ("price_note", policy.PRICE_NOTE_MAX),
            ("source_note", directory_policy.SOURCE_NOTE_MAX),
        ):
            if name in raw:
                values[name] = optional(raw[name], field=name, maximum=maximum)
        for name in ("starts_on", "ends_on", "time_zone"):
            if name in raw:
                values[name] = raw[name] or None
        if "disciplines" in raw:
            values["disciplines"] = policy.tags(
                raw["disciplines"] or [], Discipline, field="disciplines"
            )
        if "audience" in raw:
            values["audience"] = policy.tags(
                raw["audience"] or [], Audience, field="audience"
            )
        if "languages" in raw:
            values["languages"] = policy.languages(raw["languages"] or [])
        for name in ("price_amount", "price_currency", "price_basis"):
            if name in raw:
                values[name] = raw[name] if raw[name] not in ("", None) else None
        for name in ("registration_url", "source_url"):
            if name in raw:
                values[name] = (
                    directory_policy.source_url(raw[name]) if raw[name] else None
                )
        if "checked_on" in raw:
            values["checked_on"] = (
                directory_policy.checked_on(raw["checked_on"], now.date())
                if raw["checked_on"]
                else None
            )
        return values

    @staticmethod
    def _linkable_venue(
        store: ListingStore, venue_id: uuid.UUID | None
    ) -> uuid.UUID | None:
        if venue_id is None:
            return None
        venue = store.public_venue(venue_id)
        if venue is None:
            raise RuleError("venue_not_listed")
        return venue.id

    def _record_changes(
        self,
        store: ListingStore,
        opportunity_id: uuid.UUID,
        before: dict[str, Any],
        changed: dict[str, Any],
        actor: Actor,
        now: datetime,
    ) -> None:
        def emit(kind: str, keys: set[str]) -> None:
            store.record_event(
                opportunity_id=opportunity_id,
                kind=kind,
                detail={
                    k: {"from": _json(before[k]), "to": _json(changed[k])}
                    for k in sorted(keys)
                },
                actor=actor,
                now=now,
            )

        visible = {
            k for k in changed if k in OPPORTUNITY_FIELDS and before[k] != changed[k]
        }
        schedule = _SCHEDULE & visible
        if schedule:
            # Schedule revisions are recorded separately so they can be told apart.
            emit("rescheduled", schedule)
        if rest := visible - schedule:
            emit("updated", rest)


_EMPTY_OPPORTUNITY: dict[str, Any] = dict.fromkeys(OPPORTUNITY_FIELDS) | {
    "disciplines": [],
    "audience": [],
    "languages": [],
}


def _check_shape(full: dict[str, Any]) -> None:
    """Whole-record checks that do not depend on status."""
    dates = policy.schedule(full["starts_on"], full["ends_on"], full["time_zone"])
    full["time_zone"] = dates.time_zone
    stated = policy.price(
        full["price_amount"], full["price_currency"], full["price_basis"]
    )
    full["price_amount"] = stated.amount
    full["price_currency"] = stated.currency
    full["price_basis"] = stated.basis.value if stated.basis else None


def _derived(full: dict[str, Any]) -> dict[str, Any]:
    return {
        "time_zone": full["time_zone"],
        "expires_at": policy.expires_at(full["ends_on"], full["time_zone"]),
        "sort_on": policy.sort_on(full["starts_on"]),
    }


def _provider_values(raw: dict[str, Any], now: datetime) -> dict[str, Any]:
    values: dict[str, Any] = {}
    if "name" in raw:
        values["name"] = directory_policy.clean_text(
            raw["name"] or "", field="name", maximum=directory_policy.NAME_MAX
        )
    if "kind" in raw:
        values["kind"] = _enum(ProviderKind, raw["kind"] or "", "kind")
    if "country" in raw:
        values["country"] = (
            directory_policy.country_code(raw["country"]) if raw["country"] else None
        )
    for name in ("website_url", "source_url"):
        if name in raw:
            values[name] = directory_policy.source_url(raw[name]) if raw[name] else None
    if "source_note" in raw:
        values["source_note"] = directory_policy.optional_text(
            raw["source_note"],
            field="source_note",
            maximum=directory_policy.SOURCE_NOTE_MAX,
        )
    if "checked_on" in raw:
        values["checked_on"] = (
            directory_policy.checked_on(raw["checked_on"], now.date())
            if raw["checked_on"]
            else None
        )
    return values


def _require_provider_source(status: ProviderStatus, values: dict[str, Any]) -> None:
    if status in PUBLIC_PROVIDER_STATUSES and not (
        values.get("source_url") and values.get("checked_on")
    ):
        raise RuleError("source_required")


def _provider_dict(provider: Provider) -> dict[str, Any]:
    return {
        "name": provider.name,
        "kind": provider.kind.value,
        "country": provider.country,
        "website_url": provider.website_url,
        "source_url": provider.source_url,
        "source_note": provider.source_note,
        "checked_on": provider.checked_on,
    }


def _opportunity_dict(row: OpportunityRow) -> dict[str, Any]:
    values = {name: getattr(row, name) for name in OPPORTUNITY_FIELDS}
    values["category"] = row.category.value
    for name in ("disciplines", "audience", "languages"):
        values[name] = list(values[name])
    return values


def _enum[T: Any](kind: type[T], value: str | None, field: str) -> str | None:
    if value is None:
        return None
    try:
        return str(kind(value).value)
    except ValueError as error:
        raise RuleError(f"{field}_invalid") from error


def _decode(cursor: str) -> tuple[str, uuid.UUID]:
    key, item_id = decode_cursor(cursor)
    try:
        date.fromisoformat(key)
    except ValueError as error:
        raise RuleError("cursor_invalid") from error
    return key, item_id


def _json(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal | uuid.UUID):
        return str(value)
    return value
