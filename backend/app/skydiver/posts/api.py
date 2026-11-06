"""HTTP adapter for published jump summaries (#157).

`GET /posts/{id}` and `GET /people/{handle}/posts` serve anonymous and signed-in
readers; a post the reader may not see answers the same 404 `not_found` as an
unknown id. Publishing and changes need a confirmed email. Responses are never
shared-cached, so an unpublished or narrowed post is not served from a cache.
"""

import uuid
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.skydiver.access.http import AccessDependencies
from app.skydiver.access.policy import Actor
from app.skydiver.directory.policy import DirectoryRuleError
from app.skydiver.directory.service import EditConflict, Venue
from app.skydiver.identity.policy import ThrottleRule
from app.skydiver.identity.service import IdentityService, Throttled
from app.skydiver.posts.service import Card, PostService
from app.skydiver.social.api import (
    NO_STORE,
    REPORT_RULE,
    Problem,
    ReportIn,
    ReportReceivedOut,
    _problem,
)
from app.skydiver.social.service import NotFound, SocialRefused

PREFIX = "/api/skydiver/v1"
PUBLISH_RULE = ThrottleRule("post_publish", 50, timedelta(days=1))

Share = Literal["type", "venue", "altitude", "freefall"]
AudienceIn = Literal["followers", "public"]

_ERRORS: dict[int | str, dict[str, Any]] = {
    code: {"model": Problem} for code in (401, 403, 404, 409, 422, 429)
}


class PostVenueOut(BaseModel):
    id: uuid.UUID
    name: str
    country: str


class AuthorOut(BaseModel):
    handle: str
    display_name: str


class ExitAltitudeOut(BaseModel):
    value: int
    unit: Literal["ft", "m"]
    datum: Literal["unspecified", "agl", "msl"]


class PostOut(BaseModel):
    id: uuid.UUID
    author: AuthorOut
    jumped_on: date = Field(description="The activity date, not the publish time.")
    jump_type: str | None
    venue: PostVenueOut | None
    exit_altitude: ExitAltitudeOut | None
    freefall_seconds: int | None
    caption: str | None
    link: str | None
    published_at: datetime
    audience: AudienceIn
    is_owner: bool
    version: int | None = Field(default=None, description="Owner only.")
    jump_id: uuid.UUID | None = Field(default=None, description="Owner only.")


class PostPageOut(BaseModel):
    items: list[PostOut]
    next_before: uuid.UUID | None


class SourceOut(BaseModel):
    """The shareable values of the jump now; preview them before publishing."""

    id: uuid.UUID
    version: int
    jumped_on: date
    jump_type: str
    listed_venue: PostVenueOut | None = Field(
        description="Only a listed dropzone can be shared; a private place never."
    )
    has_private_place: bool
    exit_altitude: ExitAltitudeOut | None
    freefall_seconds: int | None


class SharingProfileOut(BaseModel):
    handle: str
    discoverable: bool
    hidden: bool
    publishing_restricted: bool


class SharingOut(BaseModel):
    jump: SourceOut
    profile: SharingProfileOut | None
    post: PostOut | None


class PublishIn(BaseModel):
    jump_version: Annotated[int, Field(ge=1)] = Field(
        description="The jump version that was previewed."
    )
    shares: Annotated[list[Share], Field(max_length=4)] = []
    caption: Annotated[str, Field(max_length=2000)] | None = None
    link: Annotated[str, Field(max_length=2048)] | None = None
    audience: AudienceIn


class AudienceChangeIn(BaseModel):
    audience: AudienceIn
    version: Annotated[int, Field(ge=1)]


def _venue(v: Venue | None) -> PostVenueOut | None:
    return PostVenueOut(id=v.id, name=v.name, country=v.country) if v else None


def _altitude(
    value: int | None, unit: str | None, datum: str | None
) -> ExitAltitudeOut | None:
    if value is None or unit is None:
        return None
    return ExitAltitudeOut(value=value, unit=unit, datum=datum or "unspecified")  # type: ignore[arg-type]


def _post(card: Card) -> PostOut:
    p = card.post
    return PostOut(
        id=p.id,
        author=AuthorOut(
            handle=card.author.handle, display_name=card.author.display_name
        ),
        jumped_on=p.jumped_on,
        jump_type=p.jump_type,
        venue=_venue(card.venue),
        exit_altitude=_altitude(p.exit_altitude, p.altitude_unit, p.altitude_datum),
        freefall_seconds=p.freefall_seconds,
        caption=p.caption,
        link=p.link,
        published_at=p.published_at,
        audience=p.audience.value,
        is_owner=card.is_owner,
        version=p.version if card.is_owner else None,
        jump_id=p.jump_id if card.is_owner else None,
    )


def create_router(
    *,
    service: Callable[[], PostService],
    identity: Callable[[], IdentityService],
    access: AccessDependencies,
) -> APIRouter:
    router = APIRouter(prefix=PREFIX, tags=["skydiver-posts"], responses=_ERRORS)

    def no_store(response: Response) -> None:
        response.headers["cache-control"] = "no-store"

    deps = [Depends(no_store)]
    Viewer = Annotated[Actor | None, Depends(access.optional_actor)]
    Reader = Annotated[Actor, Depends(access.actor)]
    Writer = Annotated[Actor, Depends(access.verified_actor)]
    Errors = (NotFound, EditConflict, SocialRefused, DirectoryRuleError, Throttled)

    def consume(rule: ThrottleRule, actor: Actor) -> None:
        identity().consume(rule=rule, key=str(actor.account_id))

    def done() -> Response:
        return Response(status_code=status.HTTP_204_NO_CONTENT, headers=NO_STORE)

    # -- owner ------------------------------------------------------------------------

    @router.get(
        "/me/jumps/{jump_id}/sharing",
        operation_id="getJumpSharing",
        response_model=SharingOut,
        dependencies=deps,
    )
    def get_sharing(jump_id: uuid.UUID, actor: Reader) -> SharingOut | JSONResponse:
        try:
            found = service().sharing(actor, jump_id)
        except Errors as error:
            return _problem(error)
        s, profile = found.source, found.profile
        return SharingOut(
            jump=SourceOut(
                id=s.jump_id,
                version=s.version,
                jumped_on=s.jumped_on,
                jump_type=s.jump_type,
                listed_venue=_venue(found.listed_venue),
                has_private_place=s.venue_id is None,
                exit_altitude=_altitude(
                    s.exit_altitude, s.altitude_unit, s.altitude_datum
                ),
                freefall_seconds=s.freefall_seconds,
            ),
            profile=SharingProfileOut(
                handle=profile.handle,
                discoverable=profile.discoverable,
                hidden=profile.hidden,
                publishing_restricted=profile.publishing_restricted,
            )
            if profile
            else None,
            post=_post(found.post) if found.post else None,
        )

    @router.post(
        "/me/jumps/{jump_id}/post",
        operation_id="publishJump",
        response_model=PostOut,
        status_code=status.HTTP_201_CREATED,
        dependencies=deps,
    )
    def publish(
        jump_id: uuid.UUID, body: PublishIn, actor: Writer
    ) -> PostOut | JSONResponse:
        try:
            consume(PUBLISH_RULE, actor)
            card = service().publish(
                actor,
                jump_id,
                jump_version=body.jump_version,
                shares=list(body.shares),
                caption=body.caption,
                link=body.link,
                audience=body.audience,
            )
        except Errors as error:
            return _problem(error)
        return _post(card)

    @router.put(
        "/me/posts/{post_id}/audience",
        operation_id="changePostAudience",
        status_code=status.HTTP_204_NO_CONTENT,
        response_class=Response,
        dependencies=deps,
    )
    def change_audience(
        post_id: uuid.UUID, body: AudienceChangeIn, actor: Writer
    ) -> Response:
        try:
            service().change_audience(
                actor, post_id, body.audience, expected_version=body.version
            )
        except Errors as error:
            return _problem(error)
        return done()

    @router.delete(
        "/me/posts/{post_id}",
        operation_id="unpublishPost",
        status_code=status.HTTP_204_NO_CONTENT,
        response_class=Response,
        dependencies=deps,
    )
    def unpublish(
        post_id: uuid.UUID,
        actor: Writer,
        version: Annotated[int | None, Query(ge=1)] = None,
    ) -> Response:
        try:
            service().unpublish(actor, post_id, expected_version=version)
        except Errors as error:
            return _problem(error)
        return done()

    # -- readers ----------------------------------------------------------------------

    @router.get(
        "/posts/{post_id}",
        operation_id="getPost",
        response_model=PostOut,
        dependencies=deps,
    )
    def get_post(post_id: uuid.UUID, viewer: Viewer) -> PostOut | JSONResponse:
        try:
            return _post(service().card(viewer, post_id))
        except Errors as error:
            return _problem(error)

    @router.get(
        "/people/{handle}/posts",
        operation_id="listPersonPosts",
        response_model=PostPageOut,
        dependencies=deps,
    )
    def list_posts(
        handle: str, viewer: Viewer, before: uuid.UUID | None = None
    ) -> PostPageOut | JSONResponse:
        try:
            page = service().by_person(viewer, handle, before)
        except Errors as error:
            return _problem(error)
        return PostPageOut(
            items=[_post(c) for c in page.items], next_before=page.next_before
        )

    @router.post(
        "/posts/{post_id}/reports",
        operation_id="reportPost",
        response_model=ReportReceivedOut,
        status_code=status.HTTP_202_ACCEPTED,
        dependencies=deps,
    )
    def report(
        post_id: uuid.UUID, body: ReportIn, actor: Writer
    ) -> ReportReceivedOut | JSONResponse:
        try:
            consume(REPORT_RULE, actor)
            service().report(actor, post_id, body.reason, body.note)
        except Errors as error:
            return _problem(error)
        return ReportReceivedOut()

    return router
