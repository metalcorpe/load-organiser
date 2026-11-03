"""SQL adapter for `ListingStore` (#149). Composition-root only."""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
from typing import Any

from sqlalchemy import Engine, and_, func, or_, select, tuple_, update
from sqlmodel import Session, col

from app.skydiver.access.policy import Actor
from app.skydiver.directory.policy import PUBLIC_STATUSES as PUBLIC_VENUE_STATUSES
from app.skydiver.directory.policy import VenueStatus, search_key
from app.skydiver.directory.service import EditConflict
from app.skydiver.directory.tables import SkydiverVenue
from app.skydiver.opportunities.policy import (
    PUBLIC_STATUSES,
    Category,
    OpportunityStatus,
    ProviderKind,
    ProviderStatus,
)
from app.skydiver.opportunities.service import (
    DueRule,
    ListingEvent,
    ListingStore,
    OpportunityRow,
    Provider,
    SearchQuery,
    StoreFactory,
    VenueRef,
)
from app.skydiver.opportunities.tables import (
    SkydiverListingEvent,
    SkydiverOpportunity,
    SkydiverProvider,
)

_PUBLIC = [s.value for s in PUBLIC_STATUSES]
MAX_MERGE_HOPS = 16


def _like(key: str) -> str:
    escaped = key.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _provider(row: SkydiverProvider) -> Provider:
    return Provider(
        id=row.id,
        name=row.name,
        kind=ProviderKind(row.kind),
        country=row.country,
        website_url=row.website_url,
        status=ProviderStatus(row.status),
        merged_into_id=row.merged_into_id,
        source_url=row.source_url,
        source_note=row.source_note,
        checked_on=row.checked_on,
        updated_at=row.updated_at,
        version=row.version,
        listings_version=row.listings_version,
    )


def _opportunity(row: SkydiverOpportunity) -> OpportunityRow:
    return OpportunityRow(
        id=row.id,
        title=row.title,
        category=Category(row.category),
        provider_id=row.provider_id,
        venue_id=row.venue_id,
        country=row.country,
        location_note=row.location_note,
        starts_on=row.starts_on,
        ends_on=row.ends_on,
        time_zone=row.time_zone,
        expires_at=row.expires_at,
        disciplines=tuple(row.disciplines),
        audience=tuple(row.audience),
        languages=tuple(row.languages),
        summary=row.summary,
        prerequisites=row.prerequisites,
        price_amount=row.price_amount,
        price_currency=row.price_currency,
        price_basis=row.price_basis,
        price_note=row.price_note,
        registration_url=row.registration_url,
        source_url=row.source_url,
        source_note=row.source_note,
        checked_on=row.checked_on,
        status=OpportunityStatus(row.status),
        duplicate_of_id=row.duplicate_of_id,
        updated_at=row.updated_at,
        version=row.version,
    )


def _not_ended(now: datetime) -> Any:
    # Unknown dates (postponed, not yet rescheduled) never expire.
    expires = col(SkydiverOpportunity.expires_at)
    return or_(expires.is_(None), expires > now)


class SqlListingStore:
    def __init__(self, session: Session) -> None:
        self._s = session

    # providers --------------------------------------------------------------------

    def get_provider(self, provider_id: uuid.UUID) -> Provider | None:
        query = select(SkydiverProvider).where(col(SkydiverProvider.id) == provider_id)
        row = self._s.execute(query).scalars().first()
        return _provider(row) if row else None

    def insert_provider(self, values: dict[str, Any], now: datetime) -> uuid.UUID:
        row = SkydiverProvider(
            **values,
            name_key=search_key(values["name"]),
            created_at=now,
            updated_at=now,
        )
        self._s.add(row)
        self._s.flush()
        return row.id

    def update_provider(
        self,
        provider_id: uuid.UUID,
        values: dict[str, Any],
        now: datetime,
        *,
        expected_version: int,
        expected_listings_version: int | None = None,
    ) -> None:
        extra = {"name_key": search_key(values["name"])} if "name" in values else {}
        query = (
            update(SkydiverProvider)
            .where(col(SkydiverProvider.id) == provider_id)
            .where(col(SkydiverProvider.version) == expected_version)
        )
        if expected_listings_version is not None:
            query = query.where(
                col(SkydiverProvider.listings_version) == expected_listings_version
            )
        result = self._s.execute(
            query.values(
                **values, **extra, version=expected_version + 1, updated_at=now
            )
        )
        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise EditConflict()

    def touch_provider_listings(
        self, provider_id: uuid.UUID, expected_listings_version: int
    ) -> None:
        result = self._s.execute(
            update(SkydiverProvider)
            .where(col(SkydiverProvider.id) == provider_id)
            .where(col(SkydiverProvider.status) == ProviderStatus.PUBLISHED.value)
            .where(col(SkydiverProvider.listings_version) == expected_listings_version)
            .values(listings_version=expected_listings_version + 1)
        )
        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise EditConflict()

    def count_live_opportunities(self, provider_id: uuid.UUID, now: datetime) -> int:
        return int(
            self._s.execute(
                select(func.count())
                .select_from(SkydiverOpportunity)
                .where(col(SkydiverOpportunity.provider_id) == provider_id)
                .where(col(SkydiverOpportunity.status).in_(_PUBLIC))
                .where(_not_ended(now))
            ).scalar_one()
        )

    def reassign_provider(
        self, source_id: uuid.UUID, target_id: uuid.UUID, now: datetime
    ) -> list[uuid.UUID]:
        # Row by row in ID order (the order every multi-row writer uses), bumping each
        # version so an edit based on the pre-merge listing is refused.
        candidates = self._s.execute(
            select(col(SkydiverOpportunity.id))
            .where(col(SkydiverOpportunity.provider_id) == source_id)
            .order_by(col(SkydiverOpportunity.id))
        ).scalars()
        moved = []
        for opportunity_id in list(candidates):
            result = self._s.execute(
                update(SkydiverOpportunity)
                .where(col(SkydiverOpportunity.id) == opportunity_id)
                .where(col(SkydiverOpportunity.provider_id) == source_id)
                .values(
                    provider_id=target_id,
                    version=col(SkydiverOpportunity.version) + 1,
                    updated_at=now,
                )
            )
            if result.rowcount == 1:  # type: ignore[attr-defined]
                moved.append(opportunity_id)
        return moved

    # opportunities -----------------------------------------------------------------

    def get_opportunity(self, opportunity_id: uuid.UUID) -> OpportunityRow | None:
        query = select(SkydiverOpportunity).where(
            col(SkydiverOpportunity.id) == opportunity_id
        )
        row = self._s.execute(query).scalars().first()
        return _opportunity(row) if row else None

    def insert_opportunity(self, values: dict[str, Any], now: datetime) -> uuid.UUID:
        row = SkydiverOpportunity(
            **values,
            title_key=search_key(values["title"]),
            created_at=now,
            updated_at=now,
        )
        self._s.add(row)
        self._s.flush()
        return row.id

    def update_opportunity(
        self,
        opportunity_id: uuid.UUID,
        values: dict[str, Any],
        now: datetime,
        *,
        expected_version: int,
    ) -> None:
        extra = {"title_key": search_key(values["title"])} if "title" in values else {}
        result = self._s.execute(
            update(SkydiverOpportunity)
            .where(col(SkydiverOpportunity.id) == opportunity_id)
            .where(col(SkydiverOpportunity.version) == expected_version)
            .values(**values, **extra, version=expected_version + 1, updated_at=now)
        )
        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise EditConflict()

    def search(
        self, query: SearchQuery, after: tuple[str, uuid.UUID] | None, limit: int
    ) -> list[OpportunityRow]:
        o = SkydiverOpportunity
        stmt = select(o).where(col(o.status).in_(_PUBLIC)).where(_not_ended(query.now))
        if query.key:
            pattern = _like(query.key)
            provider_names = select(col(SkydiverProvider.id)).where(
                col(SkydiverProvider.name_key).like(pattern, escape="\\")
            )
            stmt = stmt.where(
                or_(
                    col(o.title_key).like(pattern, escape="\\"),
                    col(o.provider_id).in_(provider_names),
                )
            )
        if query.category:
            stmt = stmt.where(col(o.category) == query.category)
        if query.country:
            stmt = stmt.where(col(o.country) == query.country)
        if query.discipline:
            stmt = stmt.where(col(o.disciplines).contains([query.discipline]))
        if query.audience:
            stmt = stmt.where(col(o.audience).contains([query.audience]))
        if query.provider_id:
            stmt = stmt.where(col(o.provider_id) == query.provider_id)
        if query.venue_id:
            stmt = stmt.where(col(o.venue_id).in_(self._merged_venues(query.venue_id)))
        if query.starts_from:
            # Overlap: still running on or after the date. Unknown dates are excluded.
            stmt = stmt.where(col(o.ends_on) >= query.starts_from)
        if query.starts_until:
            stmt = stmt.where(col(o.starts_on) <= query.starts_until)
        if after:
            stmt = stmt.where(
                tuple_(col(o.sort_on), col(o.id))
                > (date.fromisoformat(after[0]), after[1])
            )
        stmt = stmt.order_by(col(o.sort_on), col(o.id)).limit(limit)
        return [_opportunity(row) for row in self._s.execute(stmt).scalars()]

    def review_providers(
        self,
        *,
        key: str,
        status: str | None,
        checked_before: date | None,
        after: tuple[str, uuid.UUID] | None,
        limit: int,
    ) -> list[tuple[str, Provider]]:
        p = SkydiverProvider
        stmt = select(p)
        if key:
            stmt = stmt.where(col(p.name_key).like(_like(key), escape="\\"))
        if status:
            stmt = stmt.where(col(p.status) == status)
        if checked_before is not None:
            stmt = stmt.where(
                col(p.status) == ProviderStatus.PUBLISHED.value,
                col(p.checked_on) < checked_before,
            )
        if after:
            stmt = stmt.where(tuple_(col(p.name_key), col(p.id)) > after)
        stmt = stmt.order_by(col(p.name_key), col(p.id)).limit(limit)
        return [
            (row.name_key, _provider(row)) for row in self._s.execute(stmt).scalars()
        ]

    def review_opportunities(
        self,
        *,
        key: str,
        status: str | None,
        due: DueRule | None,
        after: tuple[str, uuid.UUID] | None,
        limit: int,
    ) -> list[OpportunityRow]:
        o = SkydiverOpportunity
        stmt = select(o)
        if key:
            stmt = stmt.where(col(o.title_key).like(_like(key), escape="\\"))
        if status:
            stmt = stmt.where(col(o.status) == status)
        if due is not None:
            soon = and_(
                col(o.status) == OpportunityStatus.PUBLISHED.value,
                col(o.starts_on) <= due.starts_until,
                col(o.checked_on) < due.soon_checked_before,
            )
            postponed = and_(
                col(o.status) == OpportunityStatus.POSTPONED.value,
                col(o.checked_on) < due.postponed_checked_before,
            )
            stmt = stmt.where(or_(soon, postponed)).where(_not_ended(due.now))
        if after:
            stmt = stmt.where(
                tuple_(col(o.sort_on), col(o.id))
                > (date.fromisoformat(after[0]), after[1])
            )
        stmt = stmt.order_by(col(o.sort_on), col(o.id)).limit(limit)
        return [_opportunity(row) for row in self._s.execute(stmt).scalars()]

    @staticmethod
    def _merged_venues(venue_id: uuid.UUID) -> Any:
        """The venue and every venue merged into it, directly or through a chain."""
        v = SkydiverVenue
        chain = select(col(v.id)).where(col(v.id) == venue_id).cte(recursive=True)
        chain = chain.union(  # union, not union_all: terminates even on a cycle
            select(col(v.id)).where(col(v.merged_into_id) == chain.c.id)
        )
        return select(chain.c.id)

    # venues (read-only, through the directory's merge redirects) -------------------

    def public_venue(self, venue_id: uuid.UUID) -> VenueRef | None:
        row = self._s.get(SkydiverVenue, venue_id)
        hops = 0
        while row is not None and row.merged_into_id is not None:
            hops += 1
            if hops > MAX_MERGE_HOPS:
                return None
            row = self._s.get(SkydiverVenue, row.merged_into_id)
        if row is None or VenueStatus(row.status) not in PUBLIC_VENUE_STATUSES:
            return None
        return VenueRef(
            id=row.id,
            name=row.name,
            country=row.country,
            locality=row.locality,
            closed=row.status == VenueStatus.CLOSED.value,
        )

    # history ----------------------------------------------------------------------

    def record_event(
        self,
        *,
        provider_id: uuid.UUID | None = None,
        opportunity_id: uuid.UUID | None = None,
        kind: str,
        detail: dict[str, Any],
        actor: Actor,
        now: datetime,
    ) -> None:
        self._s.add(
            SkydiverListingEvent(
                provider_id=provider_id,
                opportunity_id=opportunity_id,
                kind=kind,
                detail=detail,
                actor_account_id=actor.account_id,
                created_at=now,
            )
        )
        self._s.flush()

    def _events(self, column: Any, subject_id: uuid.UUID) -> list[ListingEvent]:
        rows = self._s.execute(
            select(SkydiverListingEvent)
            .where(column == subject_id)
            .order_by(
                col(SkydiverListingEvent.created_at), col(SkydiverListingEvent.id)
            )
        ).scalars()
        return [
            ListingEvent(kind=r.kind, detail=r.detail, created_at=r.created_at)
            for r in rows
        ]

    def provider_events(self, provider_id: uuid.UUID) -> list[ListingEvent]:
        return self._events(col(SkydiverListingEvent.provider_id), provider_id)

    def opportunity_events(self, opportunity_id: uuid.UUID) -> list[ListingEvent]:
        return self._events(col(SkydiverListingEvent.opportunity_id), opportunity_id)


def sql_listing_store_factory(engine: Engine) -> StoreFactory:
    """Unit of work: commit on success, roll back on any exception."""

    @contextmanager
    def stores() -> Iterator[ListingStore]:
        with Session(engine) as session:
            try:
                yield SqlListingStore(session)
            except BaseException:
                session.rollback()
                raise
            session.commit()

    return stores
