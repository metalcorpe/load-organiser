"""HTTP adapter for profiles, follows, blocks and profile reports (#156).

`GET /people/{handle}` serves anonymous and signed-in viewers alike; any profile
the viewer may not see answers the same 404 `not_found` as an unknown handle.
Everything else needs a session; changes need a confirmed email. Reviewer routes
(`/social/...`) need the reviewer role and show public profile fields only.
"""

import uuid
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.skydiver.access.http import AccessDependencies
from app.skydiver.access.policy import Actor, Role
from app.skydiver.directory.policy import DirectoryRuleError
from app.skydiver.directory.service import EditConflict, Venue
from app.skydiver.identity.policy import ThrottleRule
from app.skydiver.identity.service import IdentityService, Throttled
from app.skydiver.social.service import (
    NotFound,
    OwnProfile,
    Person,
    ProfileRow,
    Report,
    SocialRefused,
    SocialService,
)

PREFIX = "/api/skydiver/v1"
NO_STORE = {"cache-control": "no-store"}

FOLLOW_RULE = ThrottleRule("follow_request", 50, timedelta(days=1))
REPORT_RULE = ThrottleRule("social_report", 10, timedelta(days=1))
SEARCH_RULE = ThrottleRule("people_search", 120, timedelta(hours=1))

Discipline = Literal[
    "belly", "freefly", "angle", "wingsuit", "canopy", "crw", "accuracy",
    "hop_and_pop", "tandem", "training",
]  # fmt: skip
Handle = Annotated[str, Field(max_length=40)]


class Problem(BaseModel):
    detail: str


class ProfileIn(BaseModel):
    handle: Handle | None = Field(
        default=None, description="Required when creating; fixed afterwards."
    )
    display_name: Annotated[str, Field(max_length=200)]
    bio: Annotated[str, Field(max_length=2000)] | None = None
    disciplines: Annotated[list[Discipline], Field(max_length=10)] = []
    home_venue_id: uuid.UUID | None = None
    discoverable: bool = False
    version: Annotated[int, Field(ge=1)] | None = Field(
        default=None, description="Omit to create; the current version to edit."
    )


class HomeVenueOut(BaseModel):
    id: uuid.UUID
    name: str
    country: str


class PersonOut(BaseModel):
    handle: str
    display_name: str
    since: datetime | None = None


class PublicProfileOut(BaseModel):
    handle: str
    display_name: str
    bio: str | None
    disciplines: list[str]
    home_venue: HomeVenueOut | None


class OwnProfileOut(PublicProfileOut):
    discoverable: bool
    hidden: bool = Field(description="Hidden by a reviewer: no one else sees it.")
    publishing_restricted: bool
    moderation_reason: str | None
    pending_requests: int
    version: int


class ProfileViewOut(PublicProfileOut):
    is_self: bool
    follow_state: Literal["none", "requested", "following"]
    follows_you: Literal["none", "requested", "following"]


class FollowOut(BaseModel):
    state: Literal["none", "requested", "following"]


class ReportIn(BaseModel):
    reason: Literal["impersonation", "harassment", "spam", "inappropriate", "other"]
    note: Annotated[str, Field(max_length=4000)] | None = None


class ReportReceivedOut(BaseModel):
    status: Literal["received"] = "received"


class ReportOut(BaseModel):
    id: uuid.UUID
    reporter: PersonOut | None
    target: PersonOut
    reason: str
    note: str | None
    snapshot: dict[str, Any]
    status: Literal["open", "closed"]
    decision: str | None
    decision_reason: str | None
    created_at: datetime
    decided_at: datetime | None
    target_hidden: bool
    target_publishing_restricted: bool
    post_id: uuid.UUID | None = Field(
        default=None, description="Set when the report is about a published jump."
    )
    post_live: bool = False


class DecisionIn(BaseModel):
    decision: Literal["no_action", "hide_profile", "restrict_publishing", "remove_post"]
    reason: Annotated[str, Field(max_length=1000)] | None = None


class ModerationIn(BaseModel):
    hidden: bool
    publishing_restricted: bool
    reason: Annotated[str, Field(max_length=1000)]


_ERRORS: dict[int | str, dict[str, Any]] = {
    code: {"model": Problem} for code in (401, 403, 404, 409, 422, 429)
}


def _venue(v: Venue | None) -> HomeVenueOut | None:
    return HomeVenueOut(id=v.id, name=v.name, country=v.country) if v else None


def _public(row: ProfileRow, venue: Venue | None) -> dict[str, Any]:
    return {
        "handle": row.handle,
        "display_name": row.display_name,
        "bio": row.bio,
        "disciplines": list(row.disciplines),
        "home_venue": _venue(venue),
    }


def _own(p: OwnProfile) -> OwnProfileOut:
    r = p.row
    return OwnProfileOut(
        **_public(r, p.home_venue),
        discoverable=r.discoverable,
        hidden=r.hidden,
        publishing_restricted=r.publishing_restricted,
        moderation_reason=r.moderation_reason
        if r.hidden or r.publishing_restricted
        else None,
        pending_requests=p.pending_requests,
        version=r.version,
    )


def _person(p: Person) -> PersonOut:
    return PersonOut(handle=p.handle, display_name=p.display_name, since=p.since)


def _report(r: Report) -> ReportOut:
    return ReportOut(
        id=r.id,
        reporter=_person(r.reporter) if r.reporter else None,
        target=_person(r.target),
        reason=r.reason,
        note=r.note,
        snapshot=r.snapshot,
        status=r.status,  # type: ignore[arg-type]
        decision=r.decision,
        decision_reason=r.decision_reason,
        created_at=r.created_at,
        decided_at=r.decided_at,
        target_hidden=r.target_hidden,
        target_publishing_restricted=r.target_publishing_restricted,
        post_id=r.post_id,
        post_live=r.post_live,
    )


def _problem(error: Exception) -> JSONResponse:
    headers = dict(NO_STORE)
    if isinstance(error, NotFound):
        code, body = status.HTTP_404_NOT_FOUND, {"detail": "not_found"}
    elif isinstance(error, EditConflict):
        code, body = status.HTTP_409_CONFLICT, {"detail": error.code}
    elif isinstance(error, SocialRefused):
        code, body = status.HTTP_409_CONFLICT, {"detail": error.code}
    elif isinstance(error, DirectoryRuleError):
        code, body = status.HTTP_422_UNPROCESSABLE_CONTENT, {"detail": error.code}
    elif isinstance(error, Throttled):
        code, body = status.HTTP_429_TOO_MANY_REQUESTS, {"detail": error.code}
        headers["retry-after"] = str(error.retry_after_seconds)
    else:
        raise error
    return JSONResponse(body, status_code=code, headers=headers)


def create_router(
    *,
    service: Callable[[], SocialService],
    identity: Callable[[], IdentityService],
    access: AccessDependencies,
) -> APIRouter:
    router = APIRouter(prefix=PREFIX, tags=["skydiver-social"], responses=_ERRORS)

    def no_store(response: Response) -> None:
        response.headers["cache-control"] = "no-store"

    deps = [Depends(no_store)]
    Viewer = Annotated[Actor | None, Depends(access.optional_actor)]
    Reader = Annotated[Actor, Depends(access.actor)]
    Writer = Annotated[Actor, Depends(access.verified_actor)]
    Reviewer = Annotated[Actor, Depends(access.role(Role.REVIEWER))]
    Errors = (NotFound, EditConflict, SocialRefused, DirectoryRuleError, Throttled)

    def consume(rule: ThrottleRule, actor: Actor) -> None:
        identity().consume(rule=rule, key=str(actor.account_id))

    def done() -> Response:
        return Response(status_code=status.HTTP_204_NO_CONTENT, headers=NO_STORE)

    # -- own profile ------------------------------------------------------------------

    @router.get(
        "/me/profile",
        operation_id="getOwnProfile",
        response_model=OwnProfileOut | None,
        dependencies=deps,
    )
    def get_own_profile(actor: Reader) -> OwnProfileOut | None:
        own = service().own_profile(actor)
        return _own(own) if own else None

    @router.put(
        "/me/profile",
        operation_id="saveOwnProfile",
        response_model=OwnProfileOut,
        dependencies=deps,
    )
    def save_own_profile(
        body: ProfileIn, actor: Writer
    ) -> OwnProfileOut | JSONResponse:
        try:
            own = service().save_profile(
                actor,
                body.model_dump(exclude={"version"}),
                expected_version=body.version,
            )
        except Errors as error:
            return _problem(error)
        return _own(own)

    @router.get(
        "/me/people/{relation}",
        operation_id="listMyPeople",
        response_model=list[PersonOut],
        dependencies=deps,
    )
    def list_people(
        relation: Literal["requests", "followers", "following", "blocked"],
        actor: Reader,
    ) -> list[PersonOut]:
        return [_person(p) for p in service().people(actor, relation)]

    # -- people -----------------------------------------------------------------------

    @router.get(
        "/people",
        operation_id="searchPeople",
        response_model=list[PersonOut],
        dependencies=deps,
    )
    def search_people(
        actor: Reader, q: Annotated[str, Query(max_length=80)] = ""
    ) -> list[PersonOut] | JSONResponse:
        try:
            consume(SEARCH_RULE, actor)
            return [_person(p) for p in service().search(actor, q)]
        except Errors as error:
            return _problem(error)

    @router.get(
        "/people/{handle}",
        operation_id="getPerson",
        response_model=ProfileViewOut,
        dependencies=deps,
    )
    def get_person(handle: str, viewer: Viewer) -> ProfileViewOut | JSONResponse:
        try:
            v = service().view(viewer, handle)
        except Errors as error:
            return _problem(error)
        return ProfileViewOut(
            **_public(v.row, v.home_venue),
            is_self=v.is_self,
            follow_state=v.follow_state.value,
            follows_you=v.follows_you.value,
        )

    @router.put(
        "/people/{handle}/follow",
        operation_id="followPerson",
        response_model=FollowOut,
        dependencies=deps,
    )
    def follow(handle: str, actor: Writer) -> FollowOut | JSONResponse:
        try:
            consume(FOLLOW_RULE, actor)
            state = service().request_follow(actor, handle)
        except Errors as error:
            return _problem(error)
        return FollowOut(state=state.value)

    @router.delete(
        "/people/{handle}/follow",
        operation_id="unfollowPerson",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=deps,
    )
    def unfollow(handle: str, actor: Writer) -> Response:
        try:
            service().stop_following(actor, handle)
        except Errors as error:
            return _problem(error)
        return done()

    @router.post(
        "/me/people/requests/{handle}/approve",
        operation_id="approveFollower",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=deps,
    )
    def approve(handle: str, actor: Writer) -> Response:
        try:
            service().approve(actor, handle)
        except Errors as error:
            return _problem(error)
        return done()

    @router.delete(
        "/me/people/requests/{handle}",
        operation_id="rejectFollower",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=deps,
    )
    def reject(handle: str, actor: Writer) -> Response:
        try:
            service().reject(actor, handle)
        except Errors as error:
            return _problem(error)
        return done()

    @router.delete(
        "/me/people/followers/{handle}",
        operation_id="removeFollower",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=deps,
    )
    def remove_follower(handle: str, actor: Writer) -> Response:
        try:
            service().remove_follower(actor, handle)
        except Errors as error:
            return _problem(error)
        return done()

    @router.put(
        "/people/{handle}/block",
        operation_id="blockPerson",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=deps,
    )
    def block(handle: str, actor: Writer) -> Response:
        try:
            service().block(actor, handle)
        except Errors as error:
            return _problem(error)
        return done()

    @router.delete(
        "/people/{handle}/block",
        operation_id="unblockPerson",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=deps,
    )
    def unblock(handle: str, actor: Writer) -> Response:
        try:
            service().unblock(actor, handle)
        except Errors as error:
            return _problem(error)
        return done()

    @router.post(
        "/people/{handle}/reports",
        operation_id="reportPerson",
        response_model=ReportReceivedOut,
        status_code=status.HTTP_202_ACCEPTED,
        dependencies=deps,
    )
    def report(
        handle: str, body: ReportIn, actor: Writer
    ) -> ReportReceivedOut | JSONResponse:
        try:
            consume(REPORT_RULE, actor)
            service().report(actor, handle, body.reason, body.note)
        except Errors as error:
            return _problem(error)
        # The same answer for a new and a repeated report: received, not resolved.
        return ReportReceivedOut()

    # -- reviewer ---------------------------------------------------------------------

    @router.get(
        "/social/reports",
        operation_id="listSocialReports",
        response_model=list[ReportOut],
        dependencies=deps,
    )
    def list_reports(
        _reviewer: Reviewer, status_: Annotated[str, Query(alias="status")] = "open"
    ) -> list[ReportOut] | JSONResponse:
        try:
            return [_report(r) for r in service().reports(status_)]
        except Errors as error:
            return _problem(error)

    @router.post(
        "/social/reports/{report_id}/decision",
        operation_id="decideSocialReport",
        response_model=ReportOut,
        dependencies=deps,
    )
    def decide(
        report_id: uuid.UUID, body: DecisionIn, reviewer: Reviewer
    ) -> ReportOut | JSONResponse:
        try:
            decided = service().decide(reviewer, report_id, body.decision, body.reason)
        except Errors as error:
            return _problem(error)
        return _report(decided)

    @router.put(
        "/social/profiles/{handle}/moderation",
        operation_id="moderateProfile",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=deps,
    )
    def moderate(handle: str, body: ModerationIn, _reviewer: Reviewer) -> Response:
        try:
            service().moderate(
                handle,
                hidden=body.hidden,
                publishing_restricted=body.publishing_restricted,
                reason=body.reason,
            )
        except Errors as error:
            return _problem(error)
        return done()

    return router
