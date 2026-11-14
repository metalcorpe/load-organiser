"""SQL adapter for `DirectoryStore` (#148). Composition-root only."""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Engine, and_, delete, exists, func, or_, select, tuple_, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col

from app.skydiver.access.policy import Actor
from app.skydiver.access.sql import get_owned, lock_owner, owned
from app.skydiver.directory.policy import (
    PUBLIC_STATUSES,
    AliasKind,
    DirectoryRuleError,
    VenueStatus,
    search_key,
)
from app.skydiver.directory.service import (
    Alias,
    DirectoryStore,
    EditConflict,
    StoreFactory,
    Venue,
    VenueEvent,
    VenuePoint,
)
from app.skydiver.directory.tables import (
    SkydiverProvisionalPlace,
    SkydiverVenue,
    SkydiverVenueAlias,
    SkydiverVenueEvent,
)

PlaceRow = tuple[uuid.UUID, str, str, uuid.UUID | None, datetime]


def _float(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def _like(key: str) -> str:
    escaped = key.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


class SqlDirectoryStore:
    def __init__(self, session: Session) -> None:
        self._s = session

    # venues -----------------------------------------------------------------------

    def _venue(self, row: SkydiverVenue) -> Venue:
        aliases = self._s.execute(
            select(col(SkydiverVenueAlias.alias), col(SkydiverVenueAlias.kind))
            .where(col(SkydiverVenueAlias.venue_id) == row.id)
            .order_by(col(SkydiverVenueAlias.alias_key))
        ).all()
        return Venue(
            id=row.id,
            name=row.name,
            country=row.country,
            locality=row.locality,
            latitude=_float(row.latitude),
            longitude=_float(row.longitude),
            status=VenueStatus(row.status),
            merged_into_id=row.merged_into_id,
            source_url=row.source_url,
            source_note=row.source_note,
            checked_on=row.checked_on,
            updated_at=row.updated_at,
            version=row.version,
            aliases=tuple(Alias(name=a, kind=AliasKind(k)) for a, k in aliases),
        )

    def get_venue(self, venue_id: uuid.UUID) -> Venue | None:
        query = select(SkydiverVenue).where(col(SkydiverVenue.id) == venue_id)
        row = self._s.execute(query).scalars().first()
        return self._venue(row) if row else None

    @staticmethod
    def _public(
        query: Any, key: str, country: str | None, after: tuple[str, uuid.UUID] | None
    ) -> Any:
        """Filters shared by the public list and the map: the same venues in both."""
        query = query.where(
            col(SkydiverVenue.status).in_([s.value for s in PUBLIC_STATUSES])
        )
        if key:
            pattern = _like(key)
            query = query.where(
                or_(
                    col(SkydiverVenue.name_key).like(pattern, escape="\\"),
                    exists().where(
                        and_(
                            col(SkydiverVenueAlias.venue_id) == SkydiverVenue.id,
                            col(SkydiverVenueAlias.alias_key).like(
                                pattern, escape="\\"
                            ),
                        )
                    ),
                )
            )
        if country:
            query = query.where(col(SkydiverVenue.country) == country)
        if after:
            query = query.where(
                tuple_(col(SkydiverVenue.name_key), col(SkydiverVenue.id)) > after
            )
        return query.order_by(col(SkydiverVenue.name_key), col(SkydiverVenue.id))

    def search(
        self,
        *,
        key: str,
        country: str | None,
        after: tuple[str, uuid.UUID] | None,
        limit: int,
    ) -> list[tuple[str, Venue]]:
        query = self._public(select(SkydiverVenue), key, country, after)
        rows = self._s.execute(query.limit(limit)).scalars().all()
        return [(row.name_key, self._venue(row)) for row in rows]

    def points(
        self,
        *,
        key: str,
        country: str | None,
        after: tuple[str, uuid.UUID] | None,
        limit: int,
    ) -> list[tuple[str, VenuePoint]]:
        # Columns only: no alias query per row, unlike `search`.
        columns = select(
            col(SkydiverVenue.name_key),
            col(SkydiverVenue.id),
            col(SkydiverVenue.name),
            col(SkydiverVenue.country),
            col(SkydiverVenue.locality),
            col(SkydiverVenue.latitude),
            col(SkydiverVenue.longitude),
            col(SkydiverVenue.status),
        ).where(col(SkydiverVenue.latitude).is_not(None))
        query = self._public(columns, key, country, after)
        rows = self._s.execute(query.limit(limit)).all()
        return [
            (
                row.name_key,
                VenuePoint(
                    id=row.id,
                    name=row.name,
                    country=row.country,
                    locality=row.locality,
                    latitude=float(row.latitude),
                    longitude=float(row.longitude),
                    closed=row.status == VenueStatus.CLOSED.value,
                ),
            )
            for row in rows
        ]

    def review_venues(
        self,
        *,
        key: str,
        status: VenueStatus | None,
        checked_before: date | None,
        after: tuple[str, uuid.UUID] | None,
        limit: int,
    ) -> list[tuple[str, Venue]]:
        query = select(SkydiverVenue)
        if key:
            query = query.where(
                col(SkydiverVenue.name_key).like(_like(key), escape="\\")
            )
        if status is not None:
            query = query.where(col(SkydiverVenue.status) == status.value)
        if checked_before is not None:
            query = query.where(
                col(SkydiverVenue.status) == VenueStatus.LISTED.value,
                col(SkydiverVenue.checked_on) < checked_before,
            )
        if after:
            query = query.where(
                tuple_(col(SkydiverVenue.name_key), col(SkydiverVenue.id)) > after
            )
        query = query.order_by(col(SkydiverVenue.name_key), col(SkydiverVenue.id))
        rows = self._s.execute(query.limit(limit)).scalars().all()
        return [(row.name_key, self._venue(row)) for row in rows]

    def insert_venue(self, values: dict[str, Any], now: datetime) -> uuid.UUID:
        row = SkydiverVenue(
            **values,
            name_key=search_key(values["name"]),
            created_at=now,
            updated_at=now,
        )
        self._s.add(row)
        self._s.flush()
        return row.id

    def update_venue(
        self,
        venue_id: uuid.UUID,
        values: dict[str, Any],
        now: datetime,
        *,
        expected_version: int,
    ) -> None:
        extra = {"name_key": search_key(values["name"])} if "name" in values else {}
        result = self._s.execute(
            update(SkydiverVenue)
            .where(col(SkydiverVenue.id) == venue_id)
            .where(col(SkydiverVenue.version) == expected_version)
            .values(**values, **extra, version=expected_version + 1, updated_at=now)
        )
        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise EditConflict()

    def add_alias(
        self, venue_id: uuid.UUID, name: str, kind: AliasKind, now: datetime
    ) -> None:
        self._s.execute(
            insert(SkydiverVenueAlias)
            .values(
                id=uuid.uuid4(),
                venue_id=venue_id,
                alias=name,
                alias_key=search_key(name),
                kind=kind.value,
                created_at=now,
            )
            .on_conflict_do_nothing(constraint="uq_skydiver_venue_alias")
        )

    def copy_aliases(
        self, source_id: uuid.UUID, target_id: uuid.UUID, now: datetime
    ) -> None:
        for alias in self._s.execute(
            select(col(SkydiverVenueAlias.alias)).where(
                col(SkydiverVenueAlias.venue_id) == source_id
            )
        ).scalars():
            self.add_alias(target_id, alias, AliasKind.MERGED, now)

    def record_event(
        self,
        venue_id: uuid.UUID,
        kind: str,
        detail: dict[str, Any],
        actor: Actor,
        now: datetime,
    ) -> None:
        self._s.add(
            SkydiverVenueEvent(
                venue_id=venue_id,
                kind=kind,
                detail=detail,
                actor_account_id=actor.account_id,
                created_at=now,
            )
        )
        self._s.flush()

    def events(self, venue_id: uuid.UUID) -> list[VenueEvent]:
        rows = self._s.execute(
            select(SkydiverVenueEvent)
            .where(col(SkydiverVenueEvent.venue_id) == venue_id)
            .order_by(col(SkydiverVenueEvent.created_at), col(SkydiverVenueEvent.id))
        ).scalars()
        return [
            VenueEvent(kind=r.kind, detail=r.detail, created_at=r.created_at)
            for r in rows
        ]

    # provisional places (owner-scoped via access.sql) -------------------------------

    def lock_owner(self, actor: Actor) -> None:
        lock_owner(self._s, actor)

    def count_places(self, actor: Actor) -> int:
        return int(
            self._s.execute(
                select(func.count()).select_from(
                    owned(SkydiverProvisionalPlace, actor).subquery()
                )
            ).scalar_one()
        )

    @staticmethod
    def _place_row(row: SkydiverProvisionalPlace) -> PlaceRow:
        return (row.id, row.name, row.country, row.venue_id, row.updated_at)

    def list_places(self, actor: Actor) -> list[PlaceRow]:
        rows = self._s.execute(
            owned(SkydiverProvisionalPlace, actor).order_by(
                func.lower(col(SkydiverProvisionalPlace.name)),
                col(SkydiverProvisionalPlace.id),
            )
        ).scalars()
        return [self._place_row(row) for row in rows]

    def get_place(
        self, actor: Actor, place_id: uuid.UUID, *, lock: bool = False
    ) -> PlaceRow | None:
        row = get_owned(
            self._s, SkydiverProvisionalPlace, place_id, actor, for_update=lock
        )
        return self._place_row(row) if row else None

    def insert_place(
        self,
        actor: Actor,
        *,
        name: str,
        country: str,
        venue_id: uuid.UUID | None,
        now: datetime,
    ) -> uuid.UUID:
        row = SkydiverProvisionalPlace(
            owner_person_id=actor.person_id,
            name=name,
            country=country,
            venue_id=venue_id,
            created_at=now,
            updated_at=now,
        )
        self._s.add(row)
        self._s.flush()
        return row.id

    def update_place(
        self, actor: Actor, place_id: uuid.UUID, values: dict[str, Any], now: datetime
    ) -> None:
        self._s.execute(
            update(SkydiverProvisionalPlace)
            .where(col(SkydiverProvisionalPlace.id) == place_id)
            .where(col(SkydiverProvisionalPlace.owner_person_id) == actor.person_id)
            .values(**values, updated_at=now)
        )

    def delete_place(self, actor: Actor, place_id: uuid.UUID) -> None:
        try:
            self._s.execute(
                delete(SkydiverProvisionalPlace)
                .where(col(SkydiverProvisionalPlace.id) == place_id)
                .where(col(SkydiverProvisionalPlace.owner_person_id) == actor.person_id)
            )
        except IntegrityError as error:
            # A logged jump is at this place (#153); plans let go of it, jumps don't.
            if getattr(error.orig, "sqlstate", None) == "23503":
                raise DirectoryRuleError("place_in_use") from None
            raise


def sql_directory_store_factory(engine: Engine) -> StoreFactory:
    """Unit of work: commit on success, roll back on any exception."""

    @contextmanager
    def stores() -> Iterator[DirectoryStore]:
        with Session(engine) as session:
            try:
                yield SqlDirectoryStore(session)
            except BaseException:
                session.rollback()
                raise
            session.commit()

    return stores
