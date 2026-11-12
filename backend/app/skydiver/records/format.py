"""Personal-records export format v1 (#155): the documented archive schema.

One JSON object, UTF-8, compact. Every list is bounded and every object refuses
unknown keys, so an archive can carry nothing beyond these records: no account,
password, session, role, follow, publication or other person's data. IDs inside an
archive only link its own records to each other; a restore allocates new ones.
`references` holds snapshots of the public venues and listings the records point
to, used when such a reference is no longer public at restore time.

Dates are ISO calendar dates (never shifted by a time zone), instants are UTC ISO
8601, altitudes keep the unit and datum they were entered with, and every text is
as the owner entered it. See docs/product/export-format.md.
"""

import uuid
from datetime import date, time
from typing import Annotated, Any, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

FORMAT = "load-organiser.personal-records"
VERSION = 1

Text = Annotated[str, Field(min_length=1)]
Country = Annotated[str, Field(pattern=r"^[A-Z]{2}$")]
Partial = Annotated[str, Field(pattern=r"^\d{4}(-\d{2}(-\d{2})?)?$")]
Instant = AwareDatetime


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PlaceV1(_Strict):
    id: uuid.UUID
    name: Annotated[Text, Field(max_length=120)]
    country: Country
    venue_id: uuid.UUID | None = None
    created_at: Instant
    updated_at: Instant


class ComponentV1(_Strict):
    id: uuid.UUID
    kind: Literal["container", "main", "reserve", "aad", "other"]
    label: Annotated[Text, Field(max_length=80)]
    manufacturer: Annotated[str, Field(max_length=80)] | None = None
    model: Annotated[str, Field(max_length=80)] | None = None
    serial: Annotated[str, Field(max_length=120)] | None = None
    manufactured: Partial | None = None
    relation: Literal["owned", "borrowed", "rented"]
    acquisition_method: Literal["purchase", "gift", "inheritance", "other"] | None = (
        None
    )
    acquired: Partial | None = None
    notes: Annotated[str, Field(max_length=1000)] | None = None
    # Added within v1 as optional, so earlier v1 files still restore (none set).
    repack_interval_days: Annotated[int, Field(ge=1, le=730)] | None = None
    end_of_life_on: date | None = None
    archived_at: Instant | None = None
    created_at: Instant
    updated_at: Instant


class RigV1(_Strict):
    id: uuid.UUID
    label: Annotated[Text, Field(max_length=80)]
    archived_at: Instant | None = None
    created_at: Instant
    updated_at: Instant


class RigStintV1(_Strict):
    rig_id: uuid.UUID
    component_id: uuid.UUID
    from_on: date
    until_on: date | None = None


class ServiceEntryV1(_Strict):
    id: uuid.UUID
    component_id: uuid.UUID
    kind: Literal["repack", "inspection", "maintenance", "aad_service", "other"]
    done_on: date
    due_on: date | None = None
    performed_by: Annotated[str, Field(max_length=120)] | None = None
    notes: Annotated[str, Field(max_length=1000)] | None = None
    created_at: Instant


GearEventKind = Literal[
    "created", "corrected", "archived", "restored", "rig_removed", "rig_installed",
    "service_recorded", "service_removed", "from_export",
]  # fmt: skip


class GearEventV1(_Strict):
    component_id: uuid.UUID
    kind: GearEventKind
    detail: dict[str, Any]
    created_at: Instant


JumpTypeV1 = Literal[
    "unspecified", "belly", "freefly", "angle", "wingsuit", "canopy", "crw",
    "accuracy", "hop_and_pop", "tandem", "training", "other",
]  # fmt: skip


class JumpV1(_Strict):
    id: uuid.UUID
    jumped_on: date
    venue_id: uuid.UUID | None = None
    place_id: uuid.UUID | None = None
    jump_type: JumpTypeV1
    jump_number: int | None = None
    exit_time: time | None = None
    time_zone: Annotated[str, Field(max_length=64)] | None = None
    exit_altitude: int | None = None
    deployment_altitude: int | None = None
    altitude_unit: Literal["ft", "m"] | None = None
    altitude_datum: Literal["unspecified", "agl", "msl"] = "unspecified"
    freefall_seconds: int | None = None
    other_gear: Annotated[str, Field(max_length=200)] | None = None
    notes: Annotated[str, Field(max_length=2000)] | None = None
    links: Annotated[list[Annotated[str, Field(max_length=2048)]], Field(max_length=5)]
    component_ids: Annotated[list[uuid.UUID], Field(max_length=10)]
    source: Literal["manual", "restored", "imported"]
    created_at: Instant
    updated_at: Instant


JumpEventKind = Literal[
    "created", "corrected", "from_export",
    # Sharing is part of the jump's private history (posts/service.py). Restore
    # copies these entries as history only; it never republishes a post.
    "post_published", "post_audience", "post_unpublished",
]  # fmt: skip


class JumpEventV1(_Strict):
    jump_id: uuid.UUID
    kind: JumpEventKind
    detail: dict[str, Any]
    created_at: Instant


class BaselineV1(_Strict):
    prior_jumps: Annotated[int, Field(ge=0, le=100_000)]
    before_on: date
    source: Literal["manual", "restored"]
    created_at: Instant
    updated_at: Instant


class BaselineEventV1(_Strict):
    kind: Literal["declared", "corrected", "removed", "from_export"]
    detail: dict[str, Any]
    created_at: Instant


class SavedListingV1(_Strict):
    opportunity_id: uuid.UUID
    title: Annotated[Text, Field(max_length=200)]
    created_at: Instant


class PlanV1(_Strict):
    title: Annotated[Text, Field(max_length=120)]
    starts_on: date
    ends_on: date
    note: Annotated[str, Field(max_length=500)] | None = None
    opportunity_id: uuid.UUID | None = None
    venue_id: uuid.UUID | None = None
    place_id: uuid.UUID | None = None
    created_at: Instant
    updated_at: Instant


class RecordsV1(_Strict):
    places: Annotated[list[PlaceV1], Field(max_length=200)]
    components: Annotated[list[ComponentV1], Field(max_length=50)]
    rigs: Annotated[list[RigV1], Field(max_length=20)]
    rig_stints: Annotated[list[RigStintV1], Field(max_length=5_000)]
    service_entries: Annotated[list[ServiceEntryV1], Field(max_length=5_000)]
    gear_events: Annotated[list[GearEventV1], Field(max_length=20_000)]
    jumps: Annotated[list[JumpV1], Field(max_length=2_000)]
    jump_events: Annotated[list[JumpEventV1], Field(max_length=40_000)]
    baseline: BaselineV1 | None = None
    baseline_events: Annotated[list[BaselineEventV1], Field(max_length=1_000)]
    saved_listings: Annotated[list[SavedListingV1], Field(max_length=200)]
    plans: Annotated[list[PlanV1], Field(max_length=100)]
    # The licence the owner stated for currency guidance; absent or null: none.
    # Added within v1 as optional, so earlier v1 files still restore.
    licence: Literal["student", "a", "b", "c", "d"] | None = None


class VenueRefV1(_Strict):
    id: uuid.UUID
    name: Annotated[Text, Field(max_length=120)]
    country: Country


class ListingRefV1(_Strict):
    id: uuid.UUID
    title: Annotated[Text, Field(max_length=200)]


class ReferencesV1(_Strict):
    venues: Annotated[list[VenueRefV1], Field(max_length=2_500)]
    listings: Annotated[list[ListingRefV1], Field(max_length=500)]


class ArchiveV1(_Strict):
    format: Literal["load-organiser.personal-records"]
    version: Literal[1]
    exported_at: Instant
    records: RecordsV1
    references: ReferencesV1
