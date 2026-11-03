"""Private gear (#152): components, dated rig assembly and self-reported servicing.

Owner-only. Every write is compare-and-swap on the component (or rig) version;
creates are idempotent by a client key. A serial is kept exactly as entered and
is compared only within the owner's own gear: nothing here looks across
accounts, so no one else's claim can be revealed, matched or overridden.
"""

import hashlib
import json
import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import Any, Protocol

from app.skydiver.access.policy import Actor
from app.skydiver.directory import policy as directory_policy
from app.skydiver.directory.policy import DirectoryRuleError as RuleError
from app.skydiver.directory.service import EditConflict
from app.skydiver.gear import policy
from app.skydiver.gear.policy import (
    AcquisitionMethod,
    ComponentKind,
    Relation,
    ServiceKind,
)


class NotFound(Exception):
    """Absent and foreign records alike."""


class LimitReached(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class KeyReused(Exception):
    code = "client_key_reused"


@dataclass(frozen=True)
class Component:
    id: uuid.UUID
    kind: ComponentKind
    label: str
    manufacturer: str | None
    model: str | None
    serial: str | None
    serial_key: str | None
    manufactured: str | None
    relation: Relation
    acquisition_method: AcquisitionMethod | None
    acquired: str | None
    notes: str | None
    archived_at: datetime | None
    version: int
    updated_at: datetime
    fingerprint: str = ""


@dataclass(frozen=True)
class Rig:
    id: uuid.UUID
    label: str
    archived_at: datetime | None
    version: int
    fingerprint: str = ""


@dataclass(frozen=True)
class Membership:
    id: uuid.UUID
    rig_id: uuid.UUID
    rig_label: str
    component_id: uuid.UUID
    from_on: date
    until_on: date | None


@dataclass(frozen=True)
class ServiceEntry:
    id: uuid.UUID
    component_id: uuid.UUID
    kind: ServiceKind
    done_on: date
    due_on: date | None
    performed_by: str | None
    notes: str | None
    created_at: datetime
    fingerprint: str = ""


@dataclass(frozen=True)
class GearEvent:
    kind: str
    detail: dict[str, Any]
    created_at: datetime


@dataclass(frozen=True)
class ComponentSummary:
    component: Component
    rig: Membership | None
    next_due: date | None


@dataclass(frozen=True)
class ComponentDetail:
    component: Component
    rig: Membership | None
    rig_history: list[Membership]
    service: list[ServiceEntry]
    events: list[GearEvent]
    same_serial: list[uuid.UUID]


@dataclass(frozen=True)
class RigSummary:
    rig: Rig
    components: list[tuple[Component, Membership]]


class GearStore(Protocol):
    def count_components(self, actor: Actor) -> int: ...
    def component_by_key(
        self, actor: Actor, client_key: uuid.UUID
    ) -> Component | None: ...
    def get_component(
        self, actor: Actor, component_id: uuid.UUID
    ) -> Component | None: ...
    def list_components(self, actor: Actor, *, archived: bool) -> list[Component]: ...
    def insert_component(
        self, actor: Actor, client_key: uuid.UUID, values: dict[str, Any], now: datetime
    ) -> uuid.UUID | None:
        """None when a concurrent request already inserted this client key."""
        ...

    def update_component(
        self,
        actor: Actor,
        component_id: uuid.UUID,
        values: dict[str, Any],
        now: datetime,
        *,
        expected_version: int,
    ) -> None:
        """Compare-and-swap; raises EditConflict if the version moved."""
        ...

    def delete_component(
        self, actor: Actor, component_id: uuid.UUID, *, expected_version: int
    ) -> None: ...
    def same_serial(
        self, actor: Actor, serial_key: str, exclude: uuid.UUID
    ) -> list[uuid.UUID]: ...

    def count_rigs(self, actor: Actor) -> int: ...
    def rig_by_key(self, actor: Actor, client_key: uuid.UUID) -> Rig | None: ...
    def get_rig(self, actor: Actor, rig_id: uuid.UUID) -> Rig | None: ...
    def list_rigs(self, actor: Actor) -> list[Rig]: ...
    def insert_rig(
        self, actor: Actor, client_key: uuid.UUID, values: dict[str, Any], now: datetime
    ) -> uuid.UUID | None:
        """None when a concurrent request already inserted this client key."""
        ...

    def update_rig(
        self,
        actor: Actor,
        rig_id: uuid.UUID,
        values: dict[str, Any],
        now: datetime,
        *,
        expected_version: int,
    ) -> None: ...

    def memberships(
        self, actor: Actor, *, component_id: uuid.UUID | None = None
    ) -> list[Membership]:
        """Newest first."""
        ...

    def close_membership(
        self, actor: Actor, membership_id: uuid.UUID, on: date
    ) -> None: ...
    def open_membership(
        self, actor: Actor, rig_id: uuid.UUID, component_id: uuid.UUID, on: date
    ) -> None: ...

    def count_service(self, actor: Actor, component_id: uuid.UUID) -> int: ...
    def service_by_key(
        self, actor: Actor, client_key: uuid.UUID
    ) -> ServiceEntry | None: ...
    def list_service(
        self, actor: Actor, component_ids: list[uuid.UUID]
    ) -> list[ServiceEntry]:
        """Newest first."""
        ...

    def insert_service(
        self, actor: Actor, client_key: uuid.UUID, values: dict[str, Any], now: datetime
    ) -> uuid.UUID | None:
        """None when a concurrent request already inserted this client key."""
        ...

    def delete_service(
        self, actor: Actor, component_id: uuid.UUID, entry_id: uuid.UUID
    ) -> bool: ...

    def record(
        self,
        actor: Actor,
        component_id: uuid.UUID,
        kind: str,
        detail: dict[str, Any],
        now: datetime,
    ) -> None: ...
    def events(self, actor: Actor, component_id: uuid.UUID) -> list[GearEvent]: ...


StoreFactory = Callable[[], AbstractContextManager[GearStore]]
Clock = Callable[[], datetime]

# Corrections to these keep the earlier value in the owner's history; other fields
# (notably notes) record only that they changed.
_PROVENANCE = {
    "kind",
    "label",
    "manufacturer",
    "model",
    "serial",
    "manufactured",
    "relation",
    "acquisition_method",
    "acquired",
}


def fingerprint(values: dict[str, Any]) -> str:
    canonical = json.dumps(
        {k: None if v is None else str(v) for k, v in sorted(values.items())}
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


class GearService:
    def __init__(self, *, stores: StoreFactory, clock: Clock) -> None:
        self._stores = stores
        self._clock = clock

    def _latest_local_date(self) -> date:
        # The latest calendar date anywhere (UTC+14): "today" for every owner.
        return (self._clock() + timedelta(hours=14)).date()

    # -- components ---------------------------------------------------------------

    def list_components(
        self, actor: Actor, *, archived: bool = False
    ) -> list[ComponentSummary]:
        with self._stores() as store:
            components = store.list_components(actor, archived=archived)
            current = {
                m.component_id: m
                for m in store.memberships(actor)
                if m.until_on is None
            }
            service = store.list_service(actor, [c.id for c in components])
        due: dict[uuid.UUID, date] = {}
        for entry in service:
            if entry.due_on and (
                entry.component_id not in due or entry.due_on > due[entry.component_id]
            ):
                due[entry.component_id] = entry.due_on
        return [
            ComponentSummary(c, current.get(c.id), due.get(c.id)) for c in components
        ]

    def component(self, actor: Actor, component_id: uuid.UUID) -> ComponentDetail:
        with self._stores() as store:
            component = store.get_component(actor, component_id)
            if component is None:
                raise NotFound()
            history = store.memberships(actor, component_id=component_id)
            return ComponentDetail(
                component=component,
                rig=next((m for m in history if m.until_on is None), None),
                rig_history=history,
                service=store.list_service(actor, [component_id]),
                events=store.events(actor, component_id),
                same_serial=store.same_serial(actor, component.serial_key, component_id)
                if component.serial_key
                else [],
            )

    def create_component(
        self, actor: Actor, client_key: uuid.UUID, fields: dict[str, Any]
    ) -> tuple[ComponentDetail, bool]:
        values = self._component_values(fields, partial=False)
        digest = fingerprint(values)
        now = self._clock()
        with self._stores() as store:
            existing = store.component_by_key(actor, client_key)
            if existing is not None:
                if existing.fingerprint != digest:
                    raise KeyReused()
                created, component_id = False, existing.id
            else:
                # Counted, not locked: the owner's own parallel requests could
                # overshoot by their number.
                if store.count_components(actor) >= policy.MAX_COMPONENTS:
                    raise LimitReached("component_limit_reached")
                inserted = store.insert_component(
                    actor, client_key, values | {"fingerprint": digest}, now
                )
                if inserted is None:  # a concurrent retry with the same key won
                    raced = store.component_by_key(actor, client_key)
                    if raced is None or raced.fingerprint != digest:
                        raise KeyReused()
                    created, component_id = False, raced.id
                else:
                    component_id = inserted
                    store.record(actor, component_id, "created", {}, now)
                    created = True
        return self.component(actor, component_id), created

    def update_component(
        self,
        actor: Actor,
        component_id: uuid.UUID,
        fields: dict[str, Any],
        *,
        expected_version: int | None,
    ) -> ComponentDetail:
        values = self._component_values(fields, partial=True)
        now = self._clock()
        with self._stores() as store:
            current = _fresh(store.get_component(actor, component_id), expected_version)
            before = _component_values_of(current)
            merged = {**before, **values}
            policy.check_acquisition(
                Relation(merged["relation"]),
                AcquisitionMethod(merged["acquisition_method"])
                if merged["acquisition_method"]
                else None,
                policy.PartialDate(merged["acquired"]) if merged["acquired"] else None,
            )
            changed = {k: v for k, v in values.items() if before.get(k) != v}
            if changed:
                store.update_component(
                    actor, component_id, changed, now, expected_version=current.version
                )
                store.record(
                    actor,
                    component_id,
                    "corrected",
                    {
                        k: {"from": before[k], "to": changed[k]}
                        if k in _PROVENANCE
                        else "changed"
                        for k in sorted(changed)
                        if k != "serial_key"
                    },
                    now,
                )
        return self.component(actor, component_id)

    def set_archived(
        self,
        actor: Actor,
        component_id: uuid.UUID,
        archived: bool,
        *,
        expected_version: int | None,
    ) -> ComponentDetail:
        """Archived gear stays in history; archiving takes it out of its rig today."""
        now = self._clock()
        with self._stores() as store:
            current = _fresh(store.get_component(actor, component_id), expected_version)
            if (current.archived_at is not None) != archived:
                store.update_component(
                    actor,
                    component_id,
                    {"archived_at": now if archived else None},
                    now,
                    expected_version=current.version,
                )
                if archived:
                    for m in store.memberships(actor, component_id=component_id):
                        if m.until_on is None:
                            store.close_membership(actor, m.id, _ends(m, now))
                store.record(
                    actor, component_id, "archived" if archived else "restored", {}, now
                )
        return self.component(actor, component_id)

    def delete_component(
        self, actor: Actor, component_id: uuid.UUID, *, expected_version: int | None
    ) -> None:
        with self._stores() as store:
            current = _fresh(store.get_component(actor, component_id), expected_version)
            store.delete_component(
                actor, component_id, expected_version=current.version
            )

    # -- rigs -----------------------------------------------------------------------

    def list_rigs(self, actor: Actor) -> list[RigSummary]:
        with self._stores() as store:
            rigs = store.list_rigs(actor)
            components = {
                c.id: c
                for c in store.list_components(actor, archived=False)
                + store.list_components(actor, archived=True)
            }
            current = [m for m in store.memberships(actor) if m.until_on is None]
        return [
            RigSummary(
                rig,
                [
                    (components[m.component_id], m)
                    for m in current
                    if m.rig_id == rig.id and m.component_id in components
                ],
            )
            for rig in rigs
        ]

    def create_rig(
        self, actor: Actor, client_key: uuid.UUID, label: str
    ) -> tuple[Rig, bool]:
        values = {"label": _label(label)}
        digest = fingerprint(values)
        now = self._clock()
        with self._stores() as store:
            existing = store.rig_by_key(actor, client_key)
            if existing is not None:
                if existing.fingerprint != digest:
                    raise KeyReused()
                return existing, False
            if store.count_rigs(actor) >= policy.MAX_RIGS:
                raise LimitReached("rig_limit_reached")
            rig_id = store.insert_rig(
                actor, client_key, values | {"fingerprint": digest}, now
            )
            if rig_id is None:  # a concurrent retry with the same key won
                rig = store.rig_by_key(actor, client_key)
                if rig is None or rig.fingerprint != digest:
                    raise KeyReused()
                return rig, False
            rig = store.get_rig(actor, rig_id)
        assert rig is not None
        return rig, True

    def update_rig(
        self,
        actor: Actor,
        rig_id: uuid.UUID,
        *,
        label: str | None,
        archived: bool | None,
        expected_version: int | None,
    ) -> Rig:
        now = self._clock()
        with self._stores() as store:
            current = _fresh(store.get_rig(actor, rig_id), expected_version)
            values: dict[str, Any] = {}
            if label is not None:
                values["label"] = _label(label)
            if archived is not None and (current.archived_at is not None) != archived:
                values["archived_at"] = now if archived else None
            if values:
                store.update_rig(
                    actor, rig_id, values, now, expected_version=current.version
                )
            if archived:
                # An archived rig keeps its history but holds no current components.
                for m in store.memberships(actor):
                    if m.rig_id == rig_id and m.until_on is None:
                        store.close_membership(actor, m.id, _ends(m, now))
                        component = store.get_component(actor, m.component_id)
                        if component is not None:
                            store.update_component(
                                actor,
                                m.component_id,
                                {},
                                now,
                                expected_version=component.version,
                            )
                            store.record(
                                actor,
                                m.component_id,
                                "rig_removed",
                                {"rig": current.label, "on": _ends(m, now).isoformat()},
                                now,
                            )
            rig = store.get_rig(actor, rig_id)
        assert rig is not None
        return rig

    def place_in_rig(
        self,
        actor: Actor,
        component_id: uuid.UUID,
        rig_id: uuid.UUID | None,
        on: date,
        *,
        expected_version: int | None,
    ) -> ComponentDetail:
        """Dated move: the current assembly ends on `on`; past rigs keep their dates."""
        now = self._clock()
        with self._stores() as store:
            component = _fresh(
                store.get_component(actor, component_id), expected_version
            )
            if component.archived_at is not None:
                raise RuleError("component_archived")
            history = store.memberships(actor, component_id=component_id)
            current = next((m for m in history if m.until_on is None), None)
            # Stints never overlap: a move cannot start before the current stint
            # began or, out of any rig, before the last one ended.
            last = history[0] if history else None
            floor = (last.until_on or last.from_on) if last else None
            policy.check_membership(on, floor, self._latest_local_date())
            rig: Rig | None = None
            if rig_id is not None:
                rig = store.get_rig(actor, rig_id)
                if rig is None or rig.archived_at is not None:
                    raise RuleError("rig_unavailable")
                if current is not None and current.rig_id == rig_id:
                    raise RuleError("already_in_rig")
            elif current is None:
                raise RuleError("not_in_rig")
            # The version bump serializes concurrent moves of the same component.
            store.update_component(
                actor, component_id, {}, now, expected_version=component.version
            )
            if current is not None:
                store.close_membership(actor, current.id, on)
                store.record(
                    actor,
                    component_id,
                    "rig_removed",
                    {"rig": current.rig_label, "on": on.isoformat()},
                    now,
                )
            if rig_id is not None and rig is not None:
                store.open_membership(actor, rig_id, component_id, on)
                store.record(
                    actor,
                    component_id,
                    "rig_installed",
                    {"rig": rig.label, "on": on.isoformat()},
                    now,
                )
        return self.component(actor, component_id)

    # -- service ----------------------------------------------------------------------

    def add_service(
        self,
        actor: Actor,
        component_id: uuid.UUID,
        client_key: uuid.UUID,
        fields: dict[str, Any],
    ) -> tuple[ServiceEntry, bool]:
        kind = _enum(ServiceKind, fields.get("kind"), "kind")
        done_on, due_on = fields.get("done_on"), fields.get("due_on")
        if kind is None or done_on is None:
            raise RuleError("service_incomplete")
        policy.check_service_dates(done_on, due_on, self._latest_local_date())
        values = {
            "component_id": component_id,
            "kind": kind.value,
            "done_on": done_on,
            "due_on": due_on,
            "performed_by": directory_policy.optional_text(
                fields.get("performed_by"),
                field="performed_by",
                maximum=policy.PERFORMED_BY_MAX,
            ),
            "notes": _notes(fields.get("notes")),
        }
        digest = fingerprint(values)
        now = self._clock()
        with self._stores() as store:
            existing = store.service_by_key(actor, client_key)
            if existing is not None:
                if existing.fingerprint != digest:
                    raise KeyReused()
                return existing, False
            component = store.get_component(actor, component_id)
            if component is None:
                raise NotFound()
            if store.count_service(actor, component_id) >= policy.MAX_SERVICE_ENTRIES:
                raise LimitReached("service_limit_reached")
            entry_id = store.insert_service(
                actor, client_key, values | {"fingerprint": digest}, now
            )
            if entry_id is None:  # a concurrent retry with the same key won
                raced = store.service_by_key(actor, client_key)
                if raced is None or raced.fingerprint != digest:
                    raise KeyReused()
                return raced, False
            store.record(
                actor,
                component_id,
                "service_recorded",
                {"kind": kind.value, "done_on": done_on.isoformat()},
                now,
            )
            entry = next(
                e for e in store.list_service(actor, [component_id]) if e.id == entry_id
            )
        return entry, True

    def delete_service(
        self, actor: Actor, component_id: uuid.UUID, entry_id: uuid.UUID
    ) -> None:
        now = self._clock()
        with self._stores() as store:
            if not store.delete_service(actor, component_id, entry_id):
                raise NotFound()
            store.record(actor, component_id, "service_removed", {}, now)

    # -- helpers ----------------------------------------------------------------------

    def _component_values(
        self, raw: dict[str, Any], *, partial: bool
    ) -> dict[str, Any]:
        today = self._latest_local_date()
        values: dict[str, Any] = {}
        if "kind" in raw or not partial:
            kind = _enum(ComponentKind, raw.get("kind"), "kind")
            if kind is None:
                raise RuleError("kind_required")
            values["kind"] = kind.value
        if "label" in raw or not partial:
            values["label"] = _label(raw.get("label") or "")
        for name in ("manufacturer", "model"):
            if name in raw or not partial:
                values[name] = directory_policy.optional_text(
                    raw.get(name), field=name, maximum=policy.TEXT_MAX
                )
        if "serial" in raw or not partial:
            values["serial"] = policy.serial(raw.get("serial"))
            values["serial_key"] = policy.serial_key(values["serial"])
        for name in ("manufactured", "acquired"):
            if name in raw or not partial:
                found = policy.partial_date(raw.get(name), field=name, today=today)
                values[name] = found.text if found else None
        if "relation" in raw or not partial:
            relation = _enum(Relation, raw.get("relation") or "owned", "relation")
            assert relation is not None
            values["relation"] = relation.value
        if "acquisition_method" in raw or not partial:
            method = _enum(
                AcquisitionMethod, raw.get("acquisition_method"), "acquisition_method"
            )
            values["acquisition_method"] = method.value if method else None
        if "notes" in raw or not partial:
            values["notes"] = _notes(raw.get("notes"))
        if not partial:
            policy.check_acquisition(
                Relation(values["relation"]),
                AcquisitionMethod(values["acquisition_method"])
                if values["acquisition_method"]
                else None,
                policy.PartialDate(values["acquired"]) if values["acquired"] else None,
            )
        return values


def _component_values_of(component: Component) -> dict[str, Any]:
    return {
        "kind": component.kind.value,
        "label": component.label,
        "manufacturer": component.manufacturer,
        "model": component.model,
        "serial": component.serial,
        "serial_key": component.serial_key,
        "manufactured": component.manufactured,
        "relation": component.relation.value,
        "acquisition_method": component.acquisition_method.value
        if component.acquisition_method
        else None,
        "acquired": component.acquired,
        "notes": component.notes,
    }


def _ends(stint: Membership, now: datetime) -> date:
    # A stint may start "tomorrow" in UTC terms (some owner's today); ending it
    # earlier than it began would be an invalid, negative stint.
    return max(stint.from_on, now.date())


def _fresh[T: (Component, Rig)](row: T | None, expected: int | None) -> T:
    if row is None:
        raise NotFound()
    if expected is not None and expected != row.version:
        raise EditConflict()
    return row


def _label(value: str) -> str:
    return directory_policy.clean_text(value, field="label", maximum=policy.LABEL_MAX)


def _notes(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    cleaned = value.strip()
    if len(cleaned) > policy.NOTES_MAX:
        raise RuleError("notes_too_long")
    return cleaned


def _enum[E: StrEnum](kind: type[E], value: Any, field: str) -> E | None:
    if value is None or value == "":
        return None
    try:
        return kind(value)
    except ValueError:
        raise RuleError(f"{field}_invalid") from None
