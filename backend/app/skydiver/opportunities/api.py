"""HTTP adapter for providers and opportunities (#149). Called by the SvelteKit server.

- Public:   GET /opportunities, GET /opportunities/{id}, GET /providers/{id}
- Reviewer: /directory/providers..., /directory/opportunities...   (role `reviewer`)

Public responses carry curated listing fields only: no reviewer, account, history or
internal status. Registration happens at `registration_url`; nothing here books.
"""

import uuid
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.skydiver.access.http import AccessDependencies
from app.skydiver.access.policy import Actor, Role
from app.skydiver.directory.policy import DirectoryRuleError
from app.skydiver.opportunities.policy import (
    OpportunityStatus,
    ProviderStatus,
)
from app.skydiver.opportunities.service import (
    ListingEvent,
    NotFound,
    Opportunity,
    OpportunityFilter,
    OpportunityRow,
    OpportunityService,
    Provider,
)

PREFIX = "/api/skydiver/v1"
NO_STORE = {"cache-control": "no-store"}

Name = Annotated[str, Field(min_length=1, max_length=200)]
Title = Annotated[str, Field(min_length=1, max_length=240)]
Country = Annotated[str, Field(min_length=2, max_length=2)]
Url = Annotated[str, Field(max_length=2048)]
Note = Annotated[str, Field(max_length=400)]
LongText = Annotated[str, Field(max_length=1500)]
Zone = Annotated[str, Field(max_length=64)]
Tags = Annotated[list[Annotated[str, Field(max_length=16)]], Field(max_length=16)]

CategoryName = Literal["event", "boogie", "camp", "course"]
DisciplineName = Literal[
    "belly", "freefly", "angle", "wingsuit", "canopy", "crw", "accuracy"
]
AudienceName = Literal["students", "licensed", "experienced"]
PriceBasisName = Literal["per_person", "per_jump", "per_day"]
ProviderKindName = Literal["organization", "person"]


class Problem(BaseModel):
    detail: str


# -- public shapes ---------------------------------------------------------------------


class ProviderOut(BaseModel):
    """A published organiser identity, as sourced. Not an endorsement or credential."""

    id: uuid.UUID
    name: str
    kind: ProviderKindName
    country: str | None
    website_url: str | None
    source_url: str
    source_note: str | None
    checked_on: date


class ProviderDetailOut(BaseModel):
    provider: ProviderOut
    replaced_id: uuid.UUID | None = Field(
        description="Set when the requested provider was merged into `provider`."
    )


class ProviderRefOut(BaseModel):
    id: uuid.UUID
    name: str
    kind: ProviderKindName
    listed: bool = Field(description="False when the provider has no public page.")


class OpportunityVenueOut(BaseModel):
    id: uuid.UUID
    name: str
    country: str
    locality: str | None
    closed: bool


class OpportunityOut(BaseModel):
    """A sourced dated opportunity. Not inventory: availability is not known here."""

    id: uuid.UUID
    title: str
    category: CategoryName
    status: Literal["published", "postponed", "cancelled"]
    ended: bool = Field(description="The end date has passed in `time_zone`.")
    provider: ProviderRefOut
    venue: OpportunityVenueOut | None
    country: str
    location_note: str | None
    starts_on: date | None = Field(
        description="Null only while postponed without dates."
    )
    ends_on: date | None = Field(description="Inclusive, in `time_zone`.")
    time_zone: str | None = Field(description="IANA zone of the schedule.")
    disciplines: list[DisciplineName] = Field(description="Empty: not stated.")
    audience: list[AudienceName] = Field(description="Empty: not stated.")
    languages: list[str] = Field(description="ISO 639-1 codes. Empty: not stated.")
    summary: str | None
    prerequisites: str | None = Field(description="As stated by the source.")
    price_amount: str | None = Field(description="Decimal string; null: not stated.")
    price_currency: str | None
    price_basis: PriceBasisName | None
    price_note: str | None
    registration_url: str = Field(description="External registration or contact page.")
    source_url: str
    source_note: str | None
    checked_on: date


class OpportunityPageOut(BaseModel):
    items: list[OpportunityOut]
    next_cursor: str | None


class OpportunityDetailOut(BaseModel):
    opportunity: OpportunityOut
    replaced_id: uuid.UUID | None = Field(
        description="Set when the requested listing was consolidated into this one."
    )


# -- reviewer shapes -------------------------------------------------------------------


class EventOut(BaseModel):
    kind: str
    detail: dict[str, Any]
    created_at: datetime


class ReviewerProviderOut(BaseModel):
    id: uuid.UUID
    name: str
    kind: ProviderKindName
    country: str | None
    website_url: str | None
    status: Literal["draft", "published", "archived", "merged"]
    merged_into_id: uuid.UUID | None
    source_url: str | None
    source_note: str | None
    checked_on: date | None
    updated_at: datetime
    events: list[EventOut]


class ReviewerOpportunityOut(BaseModel):
    id: uuid.UUID
    title: str
    category: CategoryName
    status: Literal[
        "draft",
        "review",
        "published",
        "postponed",
        "cancelled",
        "archived",
        "duplicate",
    ]
    duplicate_of_id: uuid.UUID | None
    provider_id: uuid.UUID
    venue_id: uuid.UUID | None
    country: str
    location_note: str | None
    starts_on: date | None
    ends_on: date | None
    time_zone: str | None
    expires_at: datetime | None
    disciplines: list[str]
    audience: list[str]
    languages: list[str]
    summary: str | None
    prerequisites: str | None
    price_amount: str | None
    price_currency: str | None
    price_basis: str | None
    price_note: str | None
    registration_url: str | None
    source_url: str | None
    source_note: str | None
    checked_on: date | None
    updated_at: datetime
    events: list[EventOut]


class ProviderCreateIn(BaseModel):
    name: Name
    kind: ProviderKindName
    country: Country | None = None
    website_url: Url | None = None
    source_url: Url | None = None
    source_note: Note | None = None
    checked_on: date | None = None
    publish: bool = Field(default=False, description="False creates a draft.")


class ProviderUpdateIn(BaseModel):
    name: Name | None = None
    kind: ProviderKindName | None = None
    country: Country | None = None
    website_url: Url | None = None
    source_url: Url | None = None
    source_note: Note | None = None
    checked_on: date | None = None


class ProviderStatusIn(BaseModel):
    status: Literal["draft", "published", "archived"]


class ProviderMergeIn(BaseModel):
    into: uuid.UUID = Field(description="The provider that remains.")


class OpportunityFields(BaseModel):
    venue_id: uuid.UUID | None = None
    location_note: Note | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    time_zone: Zone | None = None
    disciplines: Tags | None = None
    audience: Tags | None = None
    languages: Tags | None = None
    summary: LongText | None = None
    prerequisites: LongText | None = None
    price_amount: Decimal | None = Field(default=None, max_digits=10, decimal_places=2)
    price_currency: Annotated[str, Field(max_length=3)] | None = None
    price_basis: PriceBasisName | None = None
    price_note: Note | None = None
    registration_url: Url | None = None
    source_url: Url | None = None
    source_note: Note | None = None
    checked_on: date | None = None


class OpportunityCreateIn(OpportunityFields):
    """New listings are drafts; publish with the status operation."""

    title: Title
    category: CategoryName
    provider_id: uuid.UUID
    country: Country


class OpportunityUpdateIn(OpportunityFields):
    title: Title | None = None
    category: CategoryName | None = None
    provider_id: uuid.UUID | None = None
    country: Country | None = None


class OpportunityStatusIn(BaseModel):
    status: Literal[
        "draft", "review", "published", "postponed", "cancelled", "archived"
    ]


class DuplicateIn(BaseModel):
    of: uuid.UUID = Field(description="The listing that remains.")


_ERRORS: dict[int | str, dict[str, Any]] = {
    code: {"model": Problem} for code in (401, 403, 404, 422)
}


def _amount(value: Decimal | None) -> str | None:
    return f"{value:.2f}" if value is not None else None


def _public_provider(provider: Provider) -> ProviderOut:
    assert provider.source_url is not None and provider.checked_on is not None
    return ProviderOut(
        id=provider.id,
        name=provider.name,
        kind=provider.kind.value,
        country=provider.country,
        website_url=provider.website_url,
        source_url=provider.source_url,
        source_note=provider.source_note,
        checked_on=provider.checked_on,
    )


def _public(item: Opportunity) -> OpportunityOut:
    row, provider, venue = item.row, item.provider, item.venue
    assert row.registration_url and row.source_url and row.checked_on
    return OpportunityOut(
        id=row.id,
        title=row.title,
        category=row.category.value,
        status=row.status.value,  # type: ignore[arg-type]  # public statuses only
        ended=item.ended,
        provider=ProviderRefOut(
            id=provider.id,
            name=provider.name,
            kind=provider.kind.value,
            listed=provider.status is ProviderStatus.PUBLISHED,
        ),
        venue=OpportunityVenueOut(
            id=venue.id,
            name=venue.name,
            country=venue.country,
            locality=venue.locality,
            closed=venue.closed,
        )
        if venue
        else None,
        country=row.country,
        location_note=row.location_note,
        starts_on=row.starts_on,
        ends_on=row.ends_on,
        time_zone=row.time_zone,
        disciplines=list(row.disciplines),  # type: ignore[arg-type]
        audience=list(row.audience),  # type: ignore[arg-type]
        languages=list(row.languages),
        summary=row.summary,
        prerequisites=row.prerequisites,
        price_amount=_amount(row.price_amount),
        price_currency=row.price_currency,
        price_basis=row.price_basis,  # type: ignore[arg-type]
        price_note=row.price_note,
        registration_url=row.registration_url,
        source_url=row.source_url,
        source_note=row.source_note,
        checked_on=row.checked_on,
    )


def _events(events: list[ListingEvent]) -> list[EventOut]:
    return [
        EventOut(kind=e.kind, detail=e.detail, created_at=e.created_at) for e in events
    ]


def _reviewer_provider(
    provider: Provider, events: list[ListingEvent]
) -> ReviewerProviderOut:
    return ReviewerProviderOut(
        id=provider.id,
        name=provider.name,
        kind=provider.kind.value,
        country=provider.country,
        website_url=provider.website_url,
        status=provider.status.value,
        merged_into_id=provider.merged_into_id,
        source_url=provider.source_url,
        source_note=provider.source_note,
        checked_on=provider.checked_on,
        updated_at=provider.updated_at,
        events=_events(events),
    )


def _reviewer_opportunity(
    row: OpportunityRow, events: list[ListingEvent]
) -> ReviewerOpportunityOut:
    return ReviewerOpportunityOut(
        id=row.id,
        title=row.title,
        category=row.category.value,
        status=row.status.value,
        duplicate_of_id=row.duplicate_of_id,
        provider_id=row.provider_id,
        venue_id=row.venue_id,
        country=row.country,
        location_note=row.location_note,
        starts_on=row.starts_on,
        ends_on=row.ends_on,
        time_zone=row.time_zone,
        expires_at=row.expires_at,
        disciplines=list(row.disciplines),
        audience=list(row.audience),
        languages=list(row.languages),
        summary=row.summary,
        prerequisites=row.prerequisites,
        price_amount=_amount(row.price_amount),
        price_currency=row.price_currency,
        price_basis=row.price_basis,
        price_note=row.price_note,
        registration_url=row.registration_url,
        source_url=row.source_url,
        source_note=row.source_note,
        checked_on=row.checked_on,
        updated_at=row.updated_at,
        events=_events(events),
    )


def _problem(error: Exception) -> JSONResponse:
    if isinstance(error, NotFound):
        code, detail = status.HTTP_404_NOT_FOUND, "not_found"
    elif isinstance(error, DirectoryRuleError):
        code, detail = status.HTTP_422_UNPROCESSABLE_CONTENT, error.code
    else:
        raise error
    return JSONResponse({"detail": detail}, status_code=code, headers=NO_STORE)


def create_router(
    *,
    service: Callable[[], OpportunityService],
    access: AccessDependencies,
) -> APIRouter:
    router = APIRouter(
        prefix=PREFIX, tags=["skydiver-opportunities"], responses=_ERRORS
    )

    def no_store(response: Response) -> None:
        response.headers["cache-control"] = "no-store"

    deps = [Depends(no_store)]
    Reviewer = Annotated[Actor, Depends(access.role(Role.REVIEWER))]
    Errors = (NotFound, DirectoryRuleError)

    # -- public -------------------------------------------------------------------

    @router.get(
        "/opportunities",
        operation_id="searchOpportunities",
        response_model=OpportunityPageOut,
        dependencies=deps,
    )
    def search_opportunities(
        q: Annotated[str | None, Query(max_length=200)] = None,
        category: Annotated[CategoryName | None, Query()] = None,
        country: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
        discipline: Annotated[DisciplineName | None, Query()] = None,
        audience: Annotated[AudienceName | None, Query()] = None,
        provider: Annotated[uuid.UUID | None, Query()] = None,
        venue: Annotated[uuid.UUID | None, Query()] = None,
        starts_from: Annotated[
            date | None,
            Query(alias="from", description="Still running on or after this date."),
        ] = None,
        starts_until: Annotated[
            date | None,
            Query(alias="to", description="Starting on or before this date."),
        ] = None,
        cursor: Annotated[str | None, Query(max_length=512)] = None,
        limit: Annotated[int | None, Query(ge=1, le=50)] = None,
    ) -> OpportunityPageOut | JSONResponse:
        """Upcoming public opportunities (not yet ended), soonest first."""
        try:
            page = service().search(
                OpportunityFilter(
                    query=q,
                    category=category,
                    country=country,
                    discipline=discipline,
                    audience=audience,
                    provider_id=provider,
                    venue_id=venue,
                    starts_from=starts_from,
                    starts_until=starts_until,
                ),
                cursor=cursor,
                limit=limit,
            )
        except Errors as error:
            return _problem(error)
        return OpportunityPageOut(
            items=[_public(i) for i in page.items], next_cursor=page.next_cursor
        )

    @router.get(
        "/opportunities/{opportunity_id}",
        operation_id="getOpportunity",
        response_model=OpportunityDetailOut,
        dependencies=deps,
    )
    def get_opportunity(
        opportunity_id: uuid.UUID,
    ) -> OpportunityDetailOut | JSONResponse:
        try:
            resolved = service().public_opportunity(opportunity_id)
        except Errors as error:
            return _problem(error)
        return OpportunityDetailOut(
            opportunity=_public(resolved.value), replaced_id=resolved.replaced_id
        )

    @router.get(
        "/providers/{provider_id}",
        operation_id="getProvider",
        response_model=ProviderDetailOut,
        dependencies=deps,
    )
    def get_provider(provider_id: uuid.UUID) -> ProviderDetailOut | JSONResponse:
        try:
            resolved = service().public_provider(provider_id)
        except Errors as error:
            return _problem(error)
        return ProviderDetailOut(
            provider=_public_provider(resolved.value), replaced_id=resolved.replaced_id
        )

    # -- reviewer: providers --------------------------------------------------------

    def provider_view(provider_id: uuid.UUID) -> ReviewerProviderOut:
        return _reviewer_provider(*service().reviewer_provider(provider_id))

    @router.post(
        "/directory/providers",
        operation_id="createProvider",
        status_code=status.HTTP_201_CREATED,
        response_model=ReviewerProviderOut,
        dependencies=deps,
    )
    def create_provider(
        body: ProviderCreateIn, actor: Reviewer
    ) -> ReviewerProviderOut | JSONResponse:
        fields = body.model_dump(exclude={"publish"})
        try:
            provider = service().create_provider(actor, fields, publish=body.publish)
        except Errors as error:
            return _problem(error)
        return provider_view(provider.id)

    @router.get(
        "/directory/providers/{provider_id}",
        operation_id="reviewProvider",
        response_model=ReviewerProviderOut,
        dependencies=deps,
    )
    def review_provider(
        provider_id: uuid.UUID, _actor: Reviewer
    ) -> ReviewerProviderOut | JSONResponse:
        try:
            return provider_view(provider_id)
        except Errors as error:
            return _problem(error)

    @router.patch(
        "/directory/providers/{provider_id}",
        operation_id="updateProvider",
        response_model=ReviewerProviderOut,
        dependencies=deps,
    )
    def update_provider(
        provider_id: uuid.UUID, body: ProviderUpdateIn, actor: Reviewer
    ) -> ReviewerProviderOut | JSONResponse:
        try:
            service().update_provider(
                actor, provider_id, body.model_dump(exclude_unset=True)
            )
        except Errors as error:
            return _problem(error)
        return provider_view(provider_id)

    @router.post(
        "/directory/providers/{provider_id}/status",
        operation_id="setProviderStatus",
        response_model=ReviewerProviderOut,
        dependencies=deps,
    )
    def set_provider_status(
        provider_id: uuid.UUID, body: ProviderStatusIn, actor: Reviewer
    ) -> ReviewerProviderOut | JSONResponse:
        try:
            service().set_provider_status(
                actor, provider_id, ProviderStatus(body.status)
            )
        except Errors as error:
            return _problem(error)
        return provider_view(provider_id)

    @router.post(
        "/directory/providers/{provider_id}/merge",
        operation_id="mergeProvider",
        response_model=ReviewerProviderOut,
        dependencies=deps,
    )
    def merge_provider(
        provider_id: uuid.UUID, body: ProviderMergeIn, actor: Reviewer
    ) -> ReviewerProviderOut | JSONResponse:
        try:
            provider = service().merge_providers(actor, provider_id, body.into)
        except Errors as error:
            return _problem(error)
        return provider_view(provider.id)

    # -- reviewer: opportunities ----------------------------------------------------

    def opportunity_view(opportunity_id: uuid.UUID) -> ReviewerOpportunityOut:
        return _reviewer_opportunity(*service().reviewer_opportunity(opportunity_id))

    @router.post(
        "/directory/opportunities",
        operation_id="createOpportunity",
        status_code=status.HTTP_201_CREATED,
        response_model=ReviewerOpportunityOut,
        dependencies=deps,
    )
    def create_opportunity(
        body: OpportunityCreateIn, actor: Reviewer
    ) -> ReviewerOpportunityOut | JSONResponse:
        try:
            row = service().create_opportunity(actor, body.model_dump())
        except Errors as error:
            return _problem(error)
        return opportunity_view(row.id)

    @router.get(
        "/directory/opportunities/{opportunity_id}",
        operation_id="reviewOpportunity",
        response_model=ReviewerOpportunityOut,
        dependencies=deps,
    )
    def review_opportunity(
        opportunity_id: uuid.UUID, _actor: Reviewer
    ) -> ReviewerOpportunityOut | JSONResponse:
        try:
            return opportunity_view(opportunity_id)
        except Errors as error:
            return _problem(error)

    @router.patch(
        "/directory/opportunities/{opportunity_id}",
        operation_id="updateOpportunity",
        response_model=ReviewerOpportunityOut,
        dependencies=deps,
    )
    def update_opportunity(
        opportunity_id: uuid.UUID, body: OpportunityUpdateIn, actor: Reviewer
    ) -> ReviewerOpportunityOut | JSONResponse:
        try:
            service().update_opportunity(
                actor, opportunity_id, body.model_dump(exclude_unset=True)
            )
        except Errors as error:
            return _problem(error)
        return opportunity_view(opportunity_id)

    @router.post(
        "/directory/opportunities/{opportunity_id}/status",
        operation_id="setOpportunityStatus",
        response_model=ReviewerOpportunityOut,
        dependencies=deps,
    )
    def set_opportunity_status(
        opportunity_id: uuid.UUID, body: OpportunityStatusIn, actor: Reviewer
    ) -> ReviewerOpportunityOut | JSONResponse:
        try:
            service().set_opportunity_status(
                actor, opportunity_id, OpportunityStatus(body.status)
            )
        except Errors as error:
            return _problem(error)
        return opportunity_view(opportunity_id)

    @router.post(
        "/directory/opportunities/{opportunity_id}/duplicate",
        operation_id="markOpportunityDuplicate",
        response_model=ReviewerOpportunityOut,
        dependencies=deps,
    )
    def mark_duplicate(
        opportunity_id: uuid.UUID, body: DuplicateIn, actor: Reviewer
    ) -> ReviewerOpportunityOut | JSONResponse:
        """Consolidate this listing into `of`; its ID keeps resolving there."""
        try:
            row = service().mark_duplicate(actor, opportunity_id, body.of)
        except Errors as error:
            return _problem(error)
        return opportunity_view(row.id)

    return router
