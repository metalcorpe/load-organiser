"""Directory use cases (#148). Ports are injected; no FastAPI, SQL or settings here.

Public reads see listed and closed venues only. Reviewers (server-granted role)
maintain venues; every change is recorded as an event. Provisional places are
owner-scoped private records and never create or reveal public data.
"""

import base64
import binascii
import json
import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Protocol

from app.skydiver.access.policy import Actor
from app.skydiver.directory import policy
from app.skydiver.directory.policy import (
    PUBLIC_STATUSES,
    AliasKind,
    DirectoryRuleError,
    VenueStatus,
)

# Working cap on private places per person (design default, not measured capacity).
MAX_PLACES_PER_PERSON = 200
MAX_MERGE_HOPS = 16


class NotFound(Exception):
    """Absent, draft (for the public) or another person's record: indistinguishable."""


class LimitReached(Exception):
    code = "place_limit_reached"


@dataclass(frozen=True)
class Alias:
    name: str
    kind: AliasKind


@dataclass(frozen=True)
class Venue:
    id: uuid.UUID
    name: str
    country: str
    locality: str | None
    latitude: float | None
    longitude: float | None
    status: VenueStatus
    merged_into_id: uuid.UUID | None
    source_url: str | None
    source_note: str | None
    checked_on: date | None
    updated_at: datetime
    aliases: tuple[Alias, ...] = ()


@dataclass(frozen=True)
class VenueEvent:
    kind: str
    detail: dict[str, Any]
    created_at: datetime


@dataclass(frozen=True)
class VenuePage:
    items: list[Venue]
    next_cursor: str | None


@dataclass(frozen=True)
class ResolvedVenue:
    venue: Venue
    # Set when the requested ID was merged into `venue`.
    replaced_id: uuid.UUID | None = None


@dataclass(frozen=True)
class Place:
    id: uuid.UUID
    name: str
    country: str
    venue: Venue | None  # the linked public venue, after merge redirects
    updated_at: datetime


@dataclass(frozen=True)
class VenueInput:
    name: str
    country: str
    source_url: str | None
    checked_on: date | None
    locality: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    source_note: str | None = None
    listed: bool = True


@dataclass(frozen=True)
class VenueChanges:
    """Only fields present in `fields` change (None clears an optional field)."""

    fields: dict[str, Any] = field(default_factory=dict)


class DirectoryStore(Protocol):
    def get_venue(self, venue_id: uuid.UUID, *, lock: bool = False) -> Venue | None: ...
    def search(
        self,
        *,
        key: str,
        country: str | None,
        after: tuple[str, uuid.UUID] | None,
        limit: int,
    ) -> list[tuple[str, Venue]]:
        """Public venues whose name or alias key contains `key`, ordered by name key."""
        ...

    def insert_venue(self, values: dict[str, Any], now: datetime) -> uuid.UUID: ...
    def update_venue(
        self, venue_id: uuid.UUID, values: dict[str, Any], now: datetime
    ) -> None: ...
    def add_alias(
        self, venue_id: uuid.UUID, name: str, kind: AliasKind, now: datetime
    ) -> None: ...
    def copy_aliases(
        self, source_id: uuid.UUID, target_id: uuid.UUID, now: datetime
    ) -> None: ...
    def record_event(
        self,
        venue_id: uuid.UUID,
        kind: str,
        detail: dict[str, Any],
        actor: Actor,
        now: datetime,
    ) -> None: ...
    def events(self, venue_id: uuid.UUID) -> list[VenueEvent]: ...

    def lock_owner(self, actor: Actor) -> None: ...
    def count_places(self, actor: Actor) -> int: ...
    def list_places(
        self, actor: Actor
    ) -> list[tuple[uuid.UUID, str, str, uuid.UUID | None, datetime]]: ...
    def get_place(
        self, actor: Actor, place_id: uuid.UUID, *, lock: bool = False
    ) -> tuple[uuid.UUID, str, str, uuid.UUID | None, datetime] | None: ...
    def insert_place(
        self,
        actor: Actor,
        *,
        name: str,
        country: str,
        venue_id: uuid.UUID | None,
        now: datetime,
    ) -> uuid.UUID: ...
    def update_place(
        self, actor: Actor, place_id: uuid.UUID, values: dict[str, Any], now: datetime
    ) -> None: ...
    def delete_place(self, actor: Actor, place_id: uuid.UUID) -> None: ...


StoreFactory = Callable[[], AbstractContextManager[DirectoryStore]]
Clock = Callable[[], datetime]


def encode_cursor(key: str, venue_id: uuid.UUID) -> str:
    raw = json.dumps([key, str(venue_id)], separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[str, uuid.UUID]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        key, venue_id = json.loads(base64.urlsafe_b64decode(padded))
        return str(key), uuid.UUID(str(venue_id))
    except (ValueError, TypeError, binascii.Error) as error:
        raise DirectoryRuleError("cursor_invalid") from error


class DirectoryService:
    def __init__(self, *, stores: StoreFactory, clock: Clock) -> None:
        self._stores = stores
        self._clock = clock

    # -- public -------------------------------------------------------------------

    def search(
        self,
        *,
        query: str | None,
        country: str | None,
        cursor: str | None,
        limit: int | None,
    ) -> VenuePage:
        key = policy.search_key(query or "")[: policy.QUERY_MAX]
        code = policy.country_code(country) if country else None
        after = decode_cursor(cursor) if cursor else None
        size = policy.page_size(limit)
        with self._stores() as store:
            rows = store.search(key=key, country=code, after=after, limit=size + 1)
        items = [venue for _, venue in rows[:size]]
        next_cursor = None
        if len(rows) > size:
            last_key, last = rows[size - 1]
            next_cursor = encode_cursor(last_key, last.id)
        return VenuePage(items=items, next_cursor=next_cursor)

    def public_venue(self, venue_id: uuid.UUID) -> ResolvedVenue:
        with self._stores() as store:
            venue = self._resolve(store, venue_id)
        if venue is None or venue.status not in PUBLIC_STATUSES:
            raise NotFound()
        return ResolvedVenue(
            venue=venue, replaced_id=venue_id if venue.id != venue_id else None
        )

    def public_venues(self, venue_ids: list[uuid.UUID]) -> dict[uuid.UUID, Venue]:
        """Merge-resolved public venues for these IDs, in one session; others omitted."""
        found: dict[uuid.UUID, Venue] = {}
        with self._stores() as store:
            for venue_id in venue_ids:
                venue = self._resolve(store, venue_id)
                if venue is not None and venue.status in PUBLIC_STATUSES:
                    found[venue_id] = venue
        return found

    # -- reviewer -----------------------------------------------------------------

    def reviewer_venue(
        self, actor: Actor, venue_id: uuid.UUID
    ) -> tuple[Venue, list[VenueEvent]]:
        with self._stores() as store:
            venue = store.get_venue(venue_id)
            if venue is None:
                raise NotFound()
            return venue, store.events(venue_id)

    def create_venue(self, actor: Actor, data: VenueInput) -> Venue:
        now = self._clock()
        values = self._validated(
            {
                "name": data.name,
                "country": data.country,
                "locality": data.locality,
                "latitude": data.latitude,
                "longitude": data.longitude,
                "source_url": data.source_url,
                "source_note": data.source_note,
                "checked_on": data.checked_on,
            },
            now,
        )
        status = VenueStatus.LISTED if data.listed else VenueStatus.DRAFT
        self._require_source(status, values)
        values["status"] = status.value
        with self._stores() as store:
            venue_id = store.insert_venue(values, now)
            store.record_event(
                venue_id, "created", {"status": status.value}, actor, now
            )
            venue = store.get_venue(venue_id)
        assert venue is not None
        return venue

    def update_venue(
        self, actor: Actor, venue_id: uuid.UUID, changes: VenueChanges
    ) -> Venue:
        now = self._clock()
        values = self._validated(dict(changes.fields), now)
        with self._stores() as store:
            current = store.get_venue(venue_id, lock=True)
            if current is None:
                raise NotFound()
            if current.status is VenueStatus.MERGED:
                raise DirectoryRuleError("venue_merged")
            merged = {**_venue_values(current), **values}
            self._require_source(current.status, merged)
            changed = {
                k: v for k, v in values.items() if _venue_values(current)[k] != v
            }
            if not changed:
                return current
            store.update_venue(venue_id, changed, now)
            if "name" in changed:
                # A rename keeps the identity; the previous name stays searchable.
                store.add_alias(venue_id, current.name, AliasKind.FORMER, now)
                store.record_event(
                    venue_id,
                    "renamed",
                    {"from": current.name, "to": changed["name"]},
                    actor,
                    now,
                )
            location = {"country", "locality", "latitude", "longitude"} & set(changed)
            if location:
                store.record_event(
                    venue_id,
                    "relocated",
                    {k: _json(changed[k]) for k in sorted(location)},
                    actor,
                    now,
                )
            source = {"source_url", "source_note", "checked_on"} & set(changed)
            if source:
                store.record_event(
                    venue_id,
                    "source_updated",
                    {k: _json(changed[k]) for k in sorted(source)},
                    actor,
                    now,
                )
            venue = store.get_venue(venue_id)
        assert venue is not None
        return venue

    def add_alias(self, actor: Actor, venue_id: uuid.UUID, name: str) -> Venue:
        now = self._clock()
        alias = policy.clean_text(name, field="alias", maximum=policy.ALIAS_MAX)
        with self._stores() as store:
            current = store.get_venue(venue_id, lock=True)
            if current is None:
                raise NotFound()
            if current.status is VenueStatus.MERGED:
                raise DirectoryRuleError("venue_merged")
            store.add_alias(venue_id, alias, AliasKind.ALTERNATE, now)
            store.record_event(venue_id, "alias_added", {"alias": alias}, actor, now)
            venue = store.get_venue(venue_id)
        assert venue is not None
        return venue

    def set_status(
        self, actor: Actor, venue_id: uuid.UUID, status: VenueStatus
    ) -> Venue:
        now = self._clock()
        with self._stores() as store:
            current = store.get_venue(venue_id, lock=True)
            if current is None:
                raise NotFound()
            policy.check_transition(current.status, status)
            if current.status is status:
                return current
            self._require_source(status, _venue_values(current))
            store.update_venue(venue_id, {"status": status.value}, now)
            store.record_event(
                venue_id,
                "status_changed",
                {"from": current.status.value, "to": status.value},
                actor,
                now,
            )
            venue = store.get_venue(venue_id)
        assert venue is not None
        return venue

    def merge(self, actor: Actor, source_id: uuid.UUID, target_id: uuid.UUID) -> Venue:
        """Reviewed duplicate merge. References to the source keep resolving."""
        now = self._clock()
        with self._stores() as store:
            # Stable lock order, so concurrent opposite merges cannot deadlock.
            first, second = sorted((source_id, target_id))
            locked = {first: store.get_venue(first, lock=True)}
            if second != first:
                locked[second] = store.get_venue(second, lock=True)
            source, target = locked.get(source_id), locked.get(target_id)
            if source is None or target is None:
                raise NotFound()
            policy.check_merge(
                policy.MergeCheck(
                    source_status=source.status,
                    target_status=target.status,
                    same_venue=source_id == target_id,
                )
            )
            store.update_venue(
                source_id,
                {"status": VenueStatus.MERGED.value, "merged_into_id": target_id},
                now,
            )
            store.add_alias(target_id, source.name, AliasKind.MERGED, now)
            store.copy_aliases(source_id, target_id, now)
            store.record_event(
                source_id, "merged_into", {"target": str(target_id)}, actor, now
            )
            store.record_event(
                target_id,
                "merged_from",
                {"source": str(source_id), "name": source.name},
                actor,
                now,
            )
            venue = store.get_venue(target_id)
        assert venue is not None
        return venue

    # -- provisional places (owner) -------------------------------------------------

    def list_places(self, actor: Actor) -> list[Place]:
        with self._stores() as store:
            return [self._place(store, row) for row in store.list_places(actor)]

    def create_place(
        self,
        actor: Actor,
        *,
        name: str,
        country: str,
        venue_id: uuid.UUID | None = None,
    ) -> Place:
        now = self._clock()
        clean = policy.clean_text(name, field="name", maximum=policy.NAME_MAX)
        code = policy.country_code(country)
        with self._stores() as store:
            store.lock_owner(actor)
            if store.count_places(actor) >= MAX_PLACES_PER_PERSON:
                raise LimitReached()
            link = self._linkable(store, venue_id) if venue_id else None
            place_id = store.insert_place(
                actor, name=clean, country=code, venue_id=link, now=now
            )
            row = store.get_place(actor, place_id)
            assert row is not None
            return self._place(store, row)

    def update_place(
        self, actor: Actor, place_id: uuid.UUID, fields: dict[str, Any]
    ) -> Place:
        now = self._clock()
        values: dict[str, Any] = {}
        if "name" in fields:
            values["name"] = policy.clean_text(
                fields["name"] or "", field="name", maximum=policy.NAME_MAX
            )
        if "country" in fields:
            values["country"] = policy.country_code(fields["country"] or "")
        with self._stores() as store:
            if store.get_place(actor, place_id, lock=True) is None:
                raise NotFound()
            if "venue_id" in fields:
                values["venue_id"] = (
                    self._linkable(store, fields["venue_id"])
                    if fields["venue_id"]
                    else None
                )
            if values:
                store.update_place(actor, place_id, values, now)
            row = store.get_place(actor, place_id)
            assert row is not None
            return self._place(store, row)

    def delete_place(self, actor: Actor, place_id: uuid.UUID) -> None:
        with self._stores() as store:
            if store.get_place(actor, place_id, lock=True) is None:
                raise NotFound()
            store.delete_place(actor, place_id)

    # -- helpers ------------------------------------------------------------------

    def _resolve(self, store: DirectoryStore, venue_id: uuid.UUID) -> Venue | None:
        venue = store.get_venue(venue_id)
        hops = 0
        while venue is not None and venue.merged_into_id is not None:
            hops += 1
            if hops > MAX_MERGE_HOPS:
                return None
            venue = store.get_venue(venue.merged_into_id)
        return venue

    def _linkable(self, store: DirectoryStore, venue_id: uuid.UUID) -> uuid.UUID:
        venue = self._resolve(store, venue_id)
        if venue is None or venue.status not in PUBLIC_STATUSES:
            # The owner may only link to public venues; drafts stay invisible.
            raise DirectoryRuleError("venue_not_listed")
        return venue.id

    def _place(
        self,
        store: DirectoryStore,
        row: tuple[uuid.UUID, str, str, uuid.UUID | None, datetime],
    ) -> Place:
        place_id, name, country, venue_id, updated_at = row
        venue = self._resolve(store, venue_id) if venue_id else None
        if venue is not None and venue.status not in PUBLIC_STATUSES:
            venue = None
        return Place(
            id=place_id, name=name, country=country, venue=venue, updated_at=updated_at
        )

    def _validated(self, raw: dict[str, Any], now: datetime) -> dict[str, Any]:
        values: dict[str, Any] = {}
        if "name" in raw:
            values["name"] = policy.clean_text(
                raw["name"] or "", field="name", maximum=policy.NAME_MAX
            )
        if "country" in raw:
            values["country"] = policy.country_code(raw["country"] or "")
        if "locality" in raw:
            values["locality"] = policy.optional_text(
                raw["locality"], field="locality", maximum=policy.LOCALITY_MAX
            )
        if "latitude" in raw or "longitude" in raw:
            lat, lon = policy.coordinates(raw.get("latitude"), raw.get("longitude"))
            values["latitude"], values["longitude"] = lat, lon
        if "source_url" in raw:
            values["source_url"] = (
                policy.source_url(raw["source_url"]) if raw["source_url"] else None
            )
        if "source_note" in raw:
            values["source_note"] = policy.optional_text(
                raw["source_note"], field="source_note", maximum=policy.SOURCE_NOTE_MAX
            )
        if "checked_on" in raw:
            values["checked_on"] = (
                policy.checked_on(raw["checked_on"], now.date())
                if raw["checked_on"]
                else None
            )
        return values

    @staticmethod
    def _require_source(status: VenueStatus, values: dict[str, Any]) -> None:
        if status is not VenueStatus.DRAFT and not (
            values.get("source_url") and values.get("checked_on")
        ):
            raise DirectoryRuleError("source_required")


def _venue_values(venue: Venue) -> dict[str, Any]:
    return {
        "name": venue.name,
        "country": venue.country,
        "locality": venue.locality,
        "latitude": venue.latitude,
        "longitude": venue.longitude,
        "source_url": venue.source_url,
        "source_note": venue.source_note,
        "checked_on": venue.checked_on,
    }


def _json(value: Any) -> Any:
    return value.isoformat() if isinstance(value, date) else value
