"""Export/restore rules (#155) as plain values. No framework or persistence imports.

`check` validates a parsed archive completely before anything is written: unique
IDs, reference closure inside the archive, the same field rules the API applies to
each record, and the per-account limits. A problem is reported by position and
rule code only (e.g. `jumps[3].deployment_above_exit`), never with the record's
content. `remap` rewrites archive IDs inside history details to the new ones.
"""

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Any

from app.skydiver.directory import policy as directory
from app.skydiver.directory.policy import DirectoryRuleError as RuleError
from app.skydiver.gear import policy as gear
from app.skydiver.gear.policy import AcquisitionMethod, Relation
from app.skydiver.history import policy as history
from app.skydiver.logbook import policy as logbook
from app.skydiver.logbook.policy import AltitudeDatum, AltitudeUnit
from app.skydiver.records.format import ArchiveV1

RAW_MAX_BYTES = 8 * 1024 * 1024  # uncompressed input, at the web and API boundaries
NORMALIZED_MAX_BYTES = 4 * 1024 * 1024  # the personal-export budget
PLAN_SPAN_MAX_DAYS = 366
MAX_PLACES = 200


class ArchiveInvalid(Exception):
    code = "archive_invalid"

    def __init__(self, problem: str) -> None:
        super().__init__(problem)
        self.problem = problem


@dataclass(frozen=True)
class Counts:
    places: int
    components: int
    rigs: int
    service_entries: int
    jumps: int
    baseline: int
    saved_listings: int
    plans: int


def counts(archive: ArchiveV1) -> Counts:
    r = archive.records
    return Counts(
        places=len(r.places),
        components=len(r.components),
        rigs=len(r.rigs),
        service_entries=len(r.service_entries),
        jumps=len(r.jumps),
        baseline=1 if r.baseline else 0,
        saved_listings=len(r.saved_listings),
        plans=len(r.plans),
    )


def _unique(section: str, ids: list[uuid.UUID]) -> set[uuid.UUID]:
    seen: set[uuid.UUID] = set()
    for i, item in enumerate(ids):
        if item in seen:
            raise ArchiveInvalid(f"{section}[{i}].duplicate_id")
        seen.add(item)
    return seen


def _text(where: str, field: str, value: str | None, maximum: int) -> None:
    """Single-line text must already be in the form the API stores (trimmed,
    whitespace collapsed, NFC), so a restore holds only values the API accepts."""
    if value is None:
        return
    if (
        _rule(where, lambda: directory.clean_text(value, field=field, maximum=maximum))
        != value
    ):
        raise ArchiveInvalid(f"{where}.{field}_invalid")


def _country(where: str, value: str) -> None:
    if _rule(where, lambda: directory.country_code(value)) != value:
        raise ArchiveInvalid(f"{where}.country_invalid")


def _rule(where: str, call: Any) -> Any:
    try:
        return call()
    except RuleError as error:
        raise ArchiveInvalid(f"{where}.{error.code}") from None


def check(archive: ArchiveV1, today: date) -> None:
    """Raise ArchiveInvalid for the first problem; return quietly when restorable.

    `today` is the latest calendar date anywhere (UTC+14), as for new records.
    """
    r = archive.records
    venues = _unique("references.venues", [v.id for v in archive.references.venues])
    listings = _unique(
        "references.listings", [o.id for o in archive.references.listings]
    )
    for i, v in enumerate(archive.references.venues):
        _text(f"references.venues[{i}]", "name", v.name, directory.NAME_MAX)
        _country(f"references.venues[{i}]", v.country)
    for i, o in enumerate(archive.references.listings):
        _text(f"references.listings[{i}]", "title", o.title, 200)
    places = _unique("places", [p.id for p in r.places])
    components = _unique("components", [c.id for c in r.components])
    rigs = _unique("rigs", [g.id for g in r.rigs])
    _unique("service_entries", [s.id for s in r.service_entries])
    jumps = _unique("jumps", [j.id for j in r.jumps])
    _unique("saved_listings", [s.opportunity_id for s in r.saved_listings])

    for i, p in enumerate(r.places):
        _text(f"places[{i}]", "name", p.name, directory.NAME_MAX)
        _country(f"places[{i}]", p.country)
        if p.venue_id is not None and p.venue_id not in venues:
            raise ArchiveInvalid(f"places[{i}].venue_unknown")

    for i, c in enumerate(r.components):
        where = f"components[{i}]"
        _text(where, "label", c.label, gear.LABEL_MAX)
        _text(where, "manufacturer", c.manufacturer, gear.TEXT_MAX)
        _text(where, "model", c.model, gear.TEXT_MAX)
        _rule(where, lambda c=c: gear.partial_date(c.manufactured, field="manufactured", today=today))  # fmt: skip
        acquired = _rule(where, lambda c=c: gear.partial_date(c.acquired, field="acquired", today=today))  # fmt: skip
        _rule(where, lambda c=c: gear.serial(c.serial))
        method = (
            AcquisitionMethod(c.acquisition_method) if c.acquisition_method else None
        )
        _rule(
            where,
            lambda c=c, m=method, a=acquired: gear.check_acquisition(
                Relation(c.relation), m, a
            ),
        )
        _rule(where, lambda c=c: gear.repack_interval(c.repack_interval_days))
        _rule(where, lambda c=c: gear.end_of_life(c.end_of_life_on))

    per_component: dict[uuid.UUID, int] = defaultdict(int)
    for i, g in enumerate(r.rigs):
        _text(f"rigs[{i}]", "label", g.label, gear.LABEL_MAX)

    for i, s in enumerate(r.service_entries):
        if s.component_id not in components:
            raise ArchiveInvalid(f"service_entries[{i}].component_unknown")
        _text(
            f"service_entries[{i}]",
            "performed_by",
            s.performed_by,
            gear.PERFORMED_BY_MAX,
        )
        _rule(
            f"service_entries[{i}]",
            lambda s=s: gear.check_service_dates(s.done_on, s.due_on, today),
        )
        per_component[s.component_id] += 1
        if per_component[s.component_id] > gear.MAX_SERVICE_ENTRIES:
            raise ArchiveInvalid(f"service_entries[{i}].too_many_for_component")

    stints: dict[uuid.UUID, list[tuple[Any, Any, int]]] = defaultdict(list)
    for i, m in enumerate(r.rig_stints):
        if m.rig_id not in rigs:
            raise ArchiveInvalid(f"rig_stints[{i}].rig_unknown")
        if m.component_id not in components:
            raise ArchiveInvalid(f"rig_stints[{i}].component_unknown")
        if m.from_on > today or (m.until_on is not None and m.until_on < m.from_on):
            raise ArchiveInvalid(f"rig_stints[{i}].dates_invalid")
        stints[m.component_id].append((m.from_on, m.until_on, i))
    for spans in stints.values():
        spans.sort(key=lambda s: s[0])
        for (_, until, _), (start, _, i) in zip(spans, spans[1:], strict=False):
            # Never in two rigs at once: each stint ends before (or as) the next starts.
            if until is None or until > start:
                raise ArchiveInvalid(f"rig_stints[{i}].overlaps")

    for i, e in enumerate(r.gear_events):
        if e.component_id not in components:
            raise ArchiveInvalid(f"gear_events[{i}].component_unknown")

    for i, j in enumerate(r.jumps):
        _check_jump(f"jumps[{i}]", j, today, venues, places, components)

    for i, ev in enumerate(r.jump_events):
        if ev.jump_id not in jumps:
            raise ArchiveInvalid(f"jump_events[{i}].jump_unknown")

    if r.baseline is not None:
        b = r.baseline
        _rule("baseline", lambda: history.baseline(b.prior_jumps, b.before_on, today))

    for i, saved in enumerate(r.saved_listings):
        _text(f"saved_listings[{i}]", "title", saved.title, 200)
        if saved.opportunity_id not in listings:
            raise ArchiveInvalid(f"saved_listings[{i}].listing_unknown")

    for i, plan in enumerate(r.plans):
        where = f"plans[{i}]"
        _text(where, "title", plan.title, 120)
        _text(where, "note", plan.note, 500)
        if plan.ends_on < plan.starts_on:
            raise ArchiveInvalid(f"{where}.dates_invalid")
        if (plan.ends_on - plan.starts_on).days >= PLAN_SPAN_MAX_DAYS:
            raise ArchiveInvalid(f"{where}.span_too_long")
        links = [plan.opportunity_id, plan.venue_id, plan.place_id]
        if sum(link is not None for link in links) > 1:
            raise ArchiveInvalid(f"{where}.too_many_links")
        if plan.opportunity_id is not None and plan.opportunity_id not in listings:
            raise ArchiveInvalid(f"{where}.listing_unknown")
        if plan.venue_id is not None and plan.venue_id not in venues:
            raise ArchiveInvalid(f"{where}.venue_unknown")
        if plan.place_id is not None and plan.place_id not in places:
            raise ArchiveInvalid(f"{where}.place_unknown")


def _check_jump(
    where: str,
    j: Any,
    today: date,
    venues: set[uuid.UUID],
    places: set[uuid.UUID],
    components: set[uuid.UUID],
) -> None:
    if (j.venue_id is None) == (j.place_id is None):
        raise ArchiveInvalid(f"{where}.location_required")
    if j.venue_id is not None and j.venue_id not in venues:
        raise ArchiveInvalid(f"{where}.venue_unknown")
    if j.place_id is not None and j.place_id not in places:
        raise ArchiveInvalid(f"{where}.place_unknown")
    _rule(where, lambda: logbook.jump_date(j.jumped_on, today))
    _rule(where, lambda: logbook.jump_number(j.jump_number))
    at, zone = _rule(where, lambda: logbook.exit_time(j.exit_time, j.time_zone))
    if (at, zone) != (j.exit_time, j.time_zone):
        raise ArchiveInvalid(f"{where}.exit_time_invalid")  # a zone needs a time
    heights = _rule(
        where,
        lambda: logbook.altitudes(
            j.exit_altitude,
            j.deployment_altitude,
            AltitudeUnit(j.altitude_unit) if j.altitude_unit else None,
            AltitudeDatum(j.altitude_datum),
        ),
    )
    if (heights.unit.value if heights.unit else None) != j.altitude_unit or (
        heights.datum.value != j.altitude_datum
    ):
        raise ArchiveInvalid(f"{where}.altitudes_incomplete")
    _rule(where, lambda: logbook.freefall_seconds(j.freefall_seconds))
    _rule(where, lambda: logbook.other_gear(j.other_gear))
    _text(where, "aircraft", j.aircraft, logbook.AIRCRAFT_MAX)
    _rule(where, lambda: logbook.notes(j.notes))
    if _rule(where, lambda: logbook.links(list(j.links))) != list(j.links):
        raise ArchiveInvalid(f"{where}.link_invalid")
    if len(set(j.component_ids)) != len(j.component_ids):
        raise ArchiveInvalid(f"{where}.duplicate_component")
    if any(c not in components for c in j.component_ids):
        raise ArchiveInvalid(f"{where}.component_unknown")


def remap(value: Any, ids: dict[str, str]) -> Any:
    """Archive IDs inside a history detail, replaced by the restored records' IDs."""
    if isinstance(value, str):
        return ids.get(value, value)
    if isinstance(value, list):
        return [remap(v, ids) for v in value]
    if isinstance(value, dict):
        return {k: remap(v, ids) for k, v in value.items()}
    return value
