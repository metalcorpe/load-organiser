"""Publish, read, narrow and withdraw jump summaries (#157). Rules in `policy`.

Every read of another person's post goes through one SQL rule (`store.readable_by`)
so a profile page, a single card and later feeds (#158) cannot disagree. Anything
a viewer may not read answers the same `not_found` as an unknown id.
"""

import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Protocol

from app.skydiver.access.policy import Actor
from app.skydiver.directory.policy import DirectoryRuleError as RuleError
from app.skydiver.directory.service import DirectoryService, EditConflict, Venue
from app.skydiver.posts import policy
from app.skydiver.posts.policy import Audience, Share
from app.skydiver.social.policy import ReportReason, report_note
from app.skydiver.social.service import (
    NotFound,
    Person,
    ProfileRow,
    SocialRefused,
    SocialService,
)

PAGE = 20


@dataclass(frozen=True)
class Source:
    """The shareable values of one jump version. Nothing else is read."""

    jump_id: uuid.UUID
    version: int
    jumped_on: date
    jump_type: str
    venue_id: uuid.UUID | None
    exit_altitude: int | None
    altitude_unit: str | None
    altitude_datum: str
    freefall_seconds: int | None


@dataclass(frozen=True)
class Post:
    id: uuid.UUID
    owner_person_id: uuid.UUID
    jump_id: uuid.UUID
    source_version: int
    audience: Audience
    jumped_on: date
    jump_type: str | None
    venue_id: uuid.UUID | None
    exit_altitude: int | None
    altitude_unit: str | None
    altitude_datum: str | None
    freefall_seconds: int | None
    caption: str | None
    link: str | None
    version: int
    published_at: datetime


@dataclass(frozen=True)
class Card:
    post: Post
    author: Person
    venue: Venue | None
    is_owner: bool


@dataclass(frozen=True)
class Sharing:
    source: Source
    listed_venue: Venue | None
    profile: ProfileRow | None
    post: Card | None


class PostStore(Protocol):
    def source(self, owner: uuid.UUID, jump_id: uuid.UUID) -> Source | None: ...
    def lock_source(
        self, owner: uuid.UUID, jump_id: uuid.UUID, version: int
    ) -> Source | None:
        """Compare-and-swap on the jump version; serialises with a concurrent edit."""
        ...

    def profile(self, person_id: uuid.UUID) -> ProfileRow | None: ...
    def admit_profile(self, person_id: uuid.UUID, audience: Audience) -> bool:
        """Conditional touch: still visible, unrestricted and (public) discoverable."""
        ...

    def post_for_jump(self, owner: uuid.UUID, jump_id: uuid.UUID) -> Post | None: ...
    def insert_post(self, values: dict[str, Any]) -> Post | None: ...
    def set_audience(
        self,
        owner: uuid.UUID,
        post_id: uuid.UUID,
        audience: Audience,
        now: datetime,
        *,
        expected_version: int,
    ) -> bool: ...
    def delete_post(
        self, owner: uuid.UUID, post_id: uuid.UUID, expected_version: int | None
    ) -> uuid.UUID | None: ...
    def owned(self, owner: uuid.UUID, post_id: uuid.UUID) -> Post | None: ...
    def readable(
        self, viewer: uuid.UUID | None, post_id: uuid.UUID
    ) -> tuple[Post, Person] | None: ...
    def by_owner(
        self,
        viewer: uuid.UUID | None,
        owner: uuid.UUID,
        before: uuid.UUID | None,
        limit: int,
    ) -> list[tuple[Post, Person]]: ...
    def record(
        self,
        owner: uuid.UUID,
        jump_id: uuid.UUID,
        kind: str,
        detail: dict[str, Any],
        now: datetime,
    ) -> None: ...
    def insert_report(self, values: dict[str, Any]) -> bool: ...


StoreFactory = Callable[[], AbstractContextManager[PostStore]]
Clock = Callable[[], datetime]


@dataclass(frozen=True)
class PostPage:
    items: list[Card]
    next_before: uuid.UUID | None


class PostService:
    def __init__(
        self,
        *,
        stores: StoreFactory,
        clock: Clock,
        directory: DirectoryService,
        social: SocialService,
    ) -> None:
        self._stores = stores
        self._clock = clock
        self._directory = directory
        self._social = social

    # -- owner ------------------------------------------------------------------------

    def sharing(self, actor: Actor, jump_id: uuid.UUID) -> Sharing:
        with self._stores() as store:
            source = store.source(actor.person_id, jump_id)
            if source is None:
                raise NotFound()
            profile = store.profile(actor.person_id)
            post = store.post_for_jump(actor.person_id, jump_id)
        listed = self._listed(source.venue_id)
        card = None
        if post is not None and profile is not None:
            card = Card(
                post,
                Person(profile.handle, profile.display_name),
                self._venues([post])[0],
                True,
            )
        return Sharing(source, listed, profile, card)

    def publish(
        self,
        actor: Actor,
        jump_id: uuid.UUID,
        *,
        jump_version: int,
        shares: list[str],
        caption: str | None,
        link: str | None,
        audience: str,
    ) -> Card:
        chosen = policy.shares(shares)
        reach = _audience(audience)
        values: dict[str, Any] = {
            "caption": policy.caption(caption),
            "link": policy.link(link),
        }
        now = self._clock()
        with self._stores() as store:
            seen = store.source(actor.person_id, jump_id)
        if seen is None:
            raise NotFound()
        listed = self._listed(seen.venue_id) if Share.VENUE in chosen else None
        with self._stores() as store:
            profile = store.profile(actor.person_id)
            _may_publish(profile, reach)
            source = store.lock_source(actor.person_id, jump_id, jump_version)
            if source is None:
                if store.source(actor.person_id, jump_id) is None:
                    raise NotFound()
                raise EditConflict()  # the jump changed since the preview
            values.update(_selected(source, chosen, listed))
            if not store.admit_profile(actor.person_id, reach):
                raise EditConflict()  # hidden, restricted or made private meanwhile
            post = store.insert_post(
                {
                    **values,
                    "owner_person_id": actor.person_id,
                    "jump_id": jump_id,
                    "source_version": source.version,
                    "audience": reach.value,
                    "published_at": now,
                    "updated_at": now,
                }
            )
            if post is None:
                raise SocialRefused("already_published")
            store.record(
                actor.person_id, jump_id, "post_published", {"audience": reach}, now
            )
        assert profile is not None
        return Card(
            post,
            Person(profile.handle, profile.display_name),
            self._venues([post])[0],
            True,
        )

    def change_audience(
        self, actor: Actor, post_id: uuid.UUID, audience: str, *, expected_version: int
    ) -> None:
        reach = _audience(audience)
        now = self._clock()
        with self._stores() as store:
            current = store.owned(actor.person_id, post_id)
            if current is None:
                raise NotFound()
            if current.version != expected_version:
                raise EditConflict()
            if reach is current.audience:
                return
            if reach is Audience.PUBLIC:
                # Widening is a new disclosure: the same checks as publishing.
                _may_publish(store.profile(actor.person_id), reach)
                if not store.admit_profile(actor.person_id, reach):
                    raise EditConflict()
            if not store.set_audience(
                actor.person_id, post_id, reach, now, expected_version=expected_version
            ):
                raise EditConflict()
            store.record(
                actor.person_id,
                current.jump_id,
                "post_audience",
                {"from": current.audience.value, "to": reach.value},
                now,
            )

    def unpublish(
        self, actor: Actor, post_id: uuid.UUID, *, expected_version: int | None
    ) -> None:
        now = self._clock()
        with self._stores() as store:
            current = store.owned(actor.person_id, post_id)
            if current is None:
                raise NotFound()
            if expected_version is not None and current.version != expected_version:
                raise EditConflict()
            jump_id = store.delete_post(actor.person_id, post_id, expected_version)
            if jump_id is None:
                raise EditConflict()
            store.record(actor.person_id, jump_id, "post_unpublished", {}, now)

    # -- readers ----------------------------------------------------------------------

    def card(self, viewer: Actor | None, post_id: uuid.UUID) -> Card:
        me = viewer.person_id if viewer else None
        with self._stores() as store:
            found = store.readable(me, post_id)
        if found is None:
            raise NotFound()
        post, author = found
        return Card(post, author, self._venues([post])[0], post.owner_person_id == me)

    def by_person(
        self, viewer: Actor | None, handle: str, before: uuid.UUID | None
    ) -> PostPage:
        # The profile itself must be visible; each post is then checked again in SQL.
        profile = self._social.view(viewer, handle)
        me = viewer.person_id if viewer else None
        with self._stores() as store:
            rows = store.by_owner(me, profile.row.person_id, before, PAGE + 1)
        more = len(rows) > PAGE
        rows = rows[:PAGE]
        venues = self._venues([p for p, _ in rows])
        items = [
            Card(p, a, v, p.owner_person_id == me)
            for (p, a), v in zip(rows, venues, strict=True)
        ]
        return PostPage(items, rows[-1][0].id if more else None)

    def report(
        self, actor: Actor, post_id: uuid.UUID, reason: str, note: str | None
    ) -> bool:
        """True when a new report was opened; False when one is already open."""
        try:
            kind = ReportReason(reason)
        except ValueError:
            raise RuleError("reason_invalid") from None
        text = report_note(note)
        now = self._clock()
        with self._stores() as store:
            found = store.readable(actor.person_id, post_id)
            if found is None:
                raise NotFound()
            post, author = found
            if post.owner_person_id == actor.person_id:
                raise SocialRefused("report_self")
            venue = self._venues([post])[0]
            return store.insert_report(
                {
                    "reporter_person_id": actor.person_id,
                    "target_person_id": post.owner_person_id,
                    "post_key": str(post.id),
                    "reason": kind.value,
                    "note": text,
                    "snapshot": _snapshot(post, author, venue),
                    "status": "open",
                    "created_at": now,
                }
            )

    # -- helpers ----------------------------------------------------------------------

    def _listed(self, venue_id: uuid.UUID | None) -> Venue | None:
        if venue_id is None:
            return None
        return self._directory.public_venues([venue_id]).get(venue_id)

    def _venues(self, posts: list[Post]) -> list[Venue | None]:
        """Read through merges; a venue no longer listed is left out of the card."""
        ids = list({p.venue_id for p in posts if p.venue_id})
        found = self._directory.public_venues(ids) if ids else {}
        return [found.get(p.venue_id) if p.venue_id else None for p in posts]


def _audience(value: str) -> Audience:
    try:
        return Audience(value)
    except ValueError:
        raise RuleError("audience_invalid") from None


def _may_publish(profile: ProfileRow | None, audience: Audience) -> None:
    if profile is None:
        raise SocialRefused("profile_required")
    if profile.hidden:
        raise SocialRefused("profile_hidden")
    if profile.publishing_restricted:
        raise SocialRefused("publishing_restricted")
    if audience is Audience.PUBLIC and not profile.discoverable:
        raise SocialRefused("public_needs_discoverable")


def _selected(
    source: Source, chosen: set[Share], listed: Venue | None
) -> dict[str, Any]:
    """Copy only the selected values. A part with nothing recorded is refused."""
    values: dict[str, Any] = {"jumped_on": source.jumped_on}
    if Share.TYPE in chosen:
        if source.jump_type == "unspecified":
            raise RuleError("type_not_recorded")
        values["jump_type"] = source.jump_type
    if Share.VENUE in chosen:
        if source.venue_id is None or listed is None:
            raise RuleError("venue_not_listed")  # private places are never shared
        values["venue_id"] = listed.id
    if Share.ALTITUDE in chosen:
        if source.exit_altitude is None:
            raise RuleError("altitude_not_recorded")
        values["exit_altitude"] = source.exit_altitude
        values["altitude_unit"] = source.altitude_unit
        values["altitude_datum"] = source.altitude_datum
    if Share.FREEFALL in chosen:
        if source.freefall_seconds is None:
            raise RuleError("freefall_not_recorded")
        values["freefall_seconds"] = source.freefall_seconds
    return values


def _snapshot(post: Post, author: Person, venue: Venue | None) -> dict[str, Any]:
    """What the reviewer sees: the card as reported, nothing from the private jump."""
    return {
        "display_name": author.display_name,
        "post": {
            "jumped_on": post.jumped_on.isoformat(),
            "jump_type": post.jump_type,
            "venue": venue.name if venue else None,
            "exit_altitude": post.exit_altitude,
            "altitude_unit": post.altitude_unit,
            "freefall_seconds": post.freefall_seconds,
            "caption": post.caption,
            "link": post.link,
            "audience": post.audience.value,
        },
    }
