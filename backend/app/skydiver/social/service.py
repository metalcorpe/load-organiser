"""Profiles, follows, blocks and profile reports (#156).

Every read evaluates visibility from facts loaded in the same transaction, and a
person who may not see a profile gets the same `not_found` as for a handle that
does not exist. A target is resolved by handle only when the caller may see it
or already has a follow or block with that person, so non-discoverable profiles
cannot be probed. Writes are conditional statements (compare-and-swap): approving
a request only succeeds while it is still pending and no block exists; blocking
deletes both follows in its own transaction. Nothing here reads private records.
"""

import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from app.skydiver.access.policy import Actor
from app.skydiver.directory.policy import DirectoryRuleError as RuleError
from app.skydiver.directory.service import DirectoryService, EditConflict, Venue
from app.skydiver.social import policy
from app.skydiver.social.policy import Decision, Facts, FollowState, ReportReason

SEARCH_LIMIT = 20
LIST_LIMIT = 500
REPORTS_PAGE = 50


class NotFound(Exception):
    """Absent, hidden, blocked and not discoverable alike."""

    code = "not_found"


class SocialRefused(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ProfileRow:
    person_id: uuid.UUID
    handle: str
    display_name: str
    bio: str | None
    disciplines: tuple[str, ...]
    home_venue_id: uuid.UUID | None
    discoverable: bool
    hidden: bool
    publishing_restricted: bool
    moderation_reason: str | None
    version: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class Person:
    """Who someone is in a list: handle and display name only."""

    handle: str
    display_name: str
    since: datetime | None = None


@dataclass(frozen=True)
class OwnProfile:
    row: ProfileRow
    home_venue: Venue | None
    pending_requests: int


@dataclass(frozen=True)
class ProfileView:
    row: ProfileRow
    home_venue: Venue | None
    is_self: bool
    follow_state: FollowState  # the viewer towards this person
    follows_you: FollowState  # this person towards the viewer
    blocked_by_you: bool


@dataclass(frozen=True)
class Report:
    id: uuid.UUID
    reporter: Person | None
    target: Person
    reason: str
    note: str | None
    snapshot: dict[str, Any]
    status: str
    decision: str | None
    decision_reason: str | None
    created_at: datetime
    decided_at: datetime | None
    target_hidden: bool
    target_publishing_restricted: bool
    post_id: uuid.UUID | None = None  # set for a report about a post (#157)
    post_live: bool = False  # the reported post is still published


class SocialStore(Protocol):
    def profile(self, person_id: uuid.UUID) -> ProfileRow | None: ...
    def profile_by_handle(self, handle: str) -> ProfileRow | None: ...
    def insert_profile(
        self, person_id: uuid.UUID, values: dict[str, Any], now: datetime
    ) -> bool:
        """False when the handle is taken (or a profile already exists)."""
        ...

    def update_profile(
        self,
        person_id: uuid.UUID,
        values: dict[str, Any],
        now: datetime,
        *,
        expected_version: int,
    ) -> None:
        """Compare-and-swap; raises EditConflict if the version moved."""
        ...

    def moderate_profile(
        self, person_id: uuid.UUID, values: dict[str, Any]
    ) -> None: ...
    def follow_status(self, follower: uuid.UUID, followee: uuid.UUID) -> str | None: ...
    def blocks(self, blocker: uuid.UUID, blocked: uuid.UUID) -> bool: ...
    def insert_follow(
        self, follower: uuid.UUID, followee: uuid.UUID, now: datetime
    ) -> bool:
        """A pending request unless one exists or a block exists either way."""
        ...

    def approve_follow(
        self, follower: uuid.UUID, followee: uuid.UUID, now: datetime
    ) -> bool:
        """Only a still-pending request with no block either way."""
        ...

    def delete_follow(
        self, follower: uuid.UUID, followee: uuid.UUID, status: str | None
    ) -> bool: ...
    def count_following(self, follower: uuid.UUID) -> int: ...
    def count_pending(self, followee: uuid.UUID) -> int: ...
    def insert_block(
        self, blocker: uuid.UUID, blocked: uuid.UUID, now: datetime
    ) -> None:
        """Also deletes follows in both directions."""
        ...

    def delete_block(self, blocker: uuid.UUID, blocked: uuid.UUID) -> bool: ...
    def count_blocks(self, blocker: uuid.UUID) -> int: ...
    def people(self, person_id: uuid.UUID, relation: str, limit: int) -> list[Person]:
        """requests | followers | following | blocked, newest first."""
        ...

    def search(self, viewer: uuid.UUID, query: str, limit: int) -> list[Person]: ...
    def insert_report(self, values: dict[str, Any]) -> bool:
        """False when the same reporter already has an open report on the target."""
        ...

    def reports(self, status: str, limit: int) -> list[Report]: ...
    def report(self, report_id: uuid.UUID) -> Report | None: ...
    def remove_post(self, post_id: uuid.UUID, reason: str, now: datetime) -> bool:
        """Delete a reported post and tell its owner on the jump's history."""
        ...

    def close_report(
        self,
        report_id: uuid.UUID,
        decision: str,
        reason: str | None,
        reviewer: uuid.UUID,
        now: datetime,
    ) -> bool:
        """Compare-and-swap on `status = 'open'`."""
        ...


StoreFactory = Callable[[], AbstractContextManager[SocialStore]]
Clock = Callable[[], datetime]


class SocialService:
    def __init__(
        self, *, stores: StoreFactory, clock: Clock, directory: DirectoryService
    ) -> None:
        self._stores = stores
        self._clock = clock
        self._directory = directory

    # -- own profile -----------------------------------------------------------------

    def own_profile(self, actor: Actor) -> OwnProfile | None:
        with self._stores() as store:
            row = store.profile(actor.person_id)
            pending = store.count_pending(actor.person_id) if row else 0
        if row is None:
            return None
        return OwnProfile(row, self._venue(row.home_venue_id), pending)

    def save_profile(
        self, actor: Actor, fields: dict[str, Any], *, expected_version: int | None
    ) -> OwnProfile:
        values: dict[str, Any] = {
            "display_name": policy.display_name(fields.get("display_name") or ""),
            "bio": policy.bio(fields.get("bio")),
            "disciplines": policy.disciplines(fields.get("disciplines")),
            "discoverable": bool(fields.get("discoverable")),
            "home_venue_id": None,
        }
        if (venue_id := fields.get("home_venue_id")) is not None:
            venue = self._directory.public_venues([venue_id]).get(venue_id)
            if venue is None:
                raise RuleError("venue_not_listed")
            values["home_venue_id"] = venue.id
        now = self._clock()
        with self._stores() as store:
            current = store.profile(actor.person_id)
            if current is None:
                if expected_version is not None:
                    raise EditConflict()
                raw_handle = fields.get("handle")
                if not raw_handle:
                    raise RuleError("handle_required")
                values["handle"] = policy.handle(raw_handle)
                if not store.insert_profile(actor.person_id, values, now):
                    if store.profile(actor.person_id) is not None:
                        raise EditConflict()  # created concurrently, e.g. another tab
                    raise RuleError("handle_taken")
            else:
                if expected_version != current.version:
                    raise EditConflict()
                if (
                    fields.get("handle")
                    and policy.handle(fields["handle"]) != current.handle
                ):
                    raise RuleError("handle_fixed")
                store.update_profile(
                    actor.person_id, values, now, expected_version=current.version
                )
        own = self.own_profile(actor)
        assert own is not None
        return own

    # -- viewing ---------------------------------------------------------------------

    def view(self, viewer: Actor | None, handle: str) -> ProfileView:
        with self._stores() as store:
            row, facts = self._visible(store, viewer, handle)
            if viewer is None or facts.is_owner:
                follow = follows_you = FollowState.NONE
                blocked = False
            else:
                follow = _state(store.follow_status(viewer.person_id, row.person_id))
                follows_you = _state(
                    store.follow_status(row.person_id, viewer.person_id)
                )
                blocked = False  # a visible profile has no block either way
        return ProfileView(
            row,
            self._venue(row.home_venue_id),
            facts.is_owner,
            follow,
            follows_you,
            blocked,
        )

    def search(self, actor: Actor, query: str) -> list[Person]:
        text = policy.search_query(query)
        with self._stores() as store:
            return store.search(actor.person_id, text, SEARCH_LIMIT)

    def people(self, actor: Actor, relation: str) -> list[Person]:
        with self._stores() as store:
            return store.people(actor.person_id, relation, LIST_LIMIT)

    # -- follows ---------------------------------------------------------------------

    def request_follow(self, actor: Actor, handle: str) -> FollowState:
        now = self._clock()
        with self._stores() as store:
            target = store.profile_by_handle(_key(handle))
            facts = (
                self._facts(store, actor, target) if target else Facts(signed_in=True)
            )
            visible = target is not None and policy.profile_visible(
                discoverable=target.discoverable, hidden=target.hidden, facts=facts
            )
            mine = store.profile(actor.person_id)
            refusal = policy.may_request_follow(
                visible=visible,
                facts=facts,
                requester_has_profile=mine is not None,
            )
            if refusal == "not_found" or target is None:
                raise NotFound()
            if refusal:
                raise SocialRefused(refusal)
            if mine is not None and mine.hidden:
                # A hidden profile would reappear to the person asked.
                raise SocialRefused("profile_hidden")
            existing = store.follow_status(actor.person_id, target.person_id)
            if existing is not None:
                return _state(existing)
            if store.count_following(actor.person_id) >= policy.MAX_FOLLOWING:
                raise SocialRefused("follow_limit_reached")
            inserted = store.insert_follow(actor.person_id, target.person_id, now)
            status = store.follow_status(actor.person_id, target.person_id)
            if not inserted and status is None:
                raise NotFound()  # a block was committed in between
            return _state(status)

    def stop_following(self, actor: Actor, handle: str) -> None:
        """Cancel a request or unfollow. Idempotent for anyone the caller can reach."""
        with self._stores() as store:
            target = self._reachable(store, actor, handle)
            store.delete_follow(actor.person_id, target.person_id, None)

    def approve(self, actor: Actor, handle: str) -> None:
        now = self._clock()
        with self._stores() as store:
            requester = self._reachable(store, actor, handle)
            if requester.hidden:
                raise NotFound()  # hidden by a reviewer: not listed, not approvable
            if store.follow_status(requester.person_id, actor.person_id) == "approved":
                return
            if not store.approve_follow(requester.person_id, actor.person_id, now):
                raise NotFound()  # withdrawn, or a block exists: nothing to approve

    def reject(self, actor: Actor, handle: str) -> None:
        with self._stores() as store:
            requester = self._reachable(store, actor, handle)
            store.delete_follow(requester.person_id, actor.person_id, "pending")

    def remove_follower(self, actor: Actor, handle: str) -> None:
        with self._stores() as store:
            follower = self._reachable(store, actor, handle)
            store.delete_follow(follower.person_id, actor.person_id, None)

    # -- blocks and reports ----------------------------------------------------------

    def block(self, actor: Actor, handle: str) -> None:
        now = self._clock()
        with self._stores() as store:
            target = self._reachable(store, actor, handle)
            if target.person_id == actor.person_id:
                raise SocialRefused("block_self")
            if store.blocks(actor.person_id, target.person_id):
                return
            if store.count_blocks(actor.person_id) >= policy.MAX_BLOCKS:
                raise SocialRefused("block_limit_reached")
            store.insert_block(actor.person_id, target.person_id, now)

    def unblock(self, actor: Actor, handle: str) -> None:
        with self._stores() as store:
            target = store.profile_by_handle(_key(handle))
            if target is None or not store.delete_block(
                actor.person_id, target.person_id
            ):
                raise NotFound()

    def report(self, actor: Actor, handle: str, reason: str, note: str | None) -> bool:
        """True when a new report was opened; False when one is already open."""
        try:
            kind = ReportReason(reason)
        except ValueError:
            raise RuleError("reason_invalid") from None
        text = policy.report_note(note)
        now = self._clock()
        with self._stores() as store:
            target = self._reachable(store, actor, handle)
            if target.person_id == actor.person_id:
                raise SocialRefused("report_self")
            return store.insert_report(
                {
                    "reporter_person_id": actor.person_id,
                    "target_person_id": target.person_id,
                    "reason": kind.value,
                    "note": text,
                    # What the reporter saw: public profile fields only.
                    "snapshot": {
                        "handle": target.handle,
                        "display_name": target.display_name,
                        "bio": target.bio,
                        "disciplines": list(target.disciplines),
                    },
                    "status": "open",
                    "created_at": now,
                }
            )

    # -- reviewer --------------------------------------------------------------------

    def reports(self, status: str) -> list[Report]:
        if status not in ("open", "closed"):
            raise RuleError("status_invalid")
        with self._stores() as store:
            return store.reports(status, REPORTS_PAGE)

    def decide(
        self, reviewer: Actor, report_id: uuid.UUID, decision: str, reason: str | None
    ) -> Report:
        try:
            outcome = Decision(decision)
        except ValueError:
            raise RuleError("decision_invalid") from None
        why = policy.moderation_reason(reason)
        if outcome is not Decision.NO_ACTION and not why:
            raise RuleError("reason_required")
        now = self._clock()
        with self._stores() as store:
            current = store.report(report_id)
            if current is None:
                raise NotFound()
            if outcome is Decision.REMOVE_POST and current.post_id is None:
                raise RuleError("decision_invalid")  # a profile report has no post
            if not store.close_report(
                report_id, outcome.value, why, reviewer.account_id, now
            ):
                raise EditConflict()  # already decided by another reviewer
            if outcome is Decision.REMOVE_POST:
                assert current.post_id is not None and why is not None
                store.remove_post(current.post_id, why, now)  # gone already is fine
            target = store.profile_by_handle(current.target.handle)
            if target is not None and outcome is Decision.HIDE_PROFILE:
                store.moderate_profile(
                    target.person_id, {"hidden_at": now, "moderation_reason": why}
                )
            elif target is not None and outcome is Decision.RESTRICT_PUBLISHING:
                store.moderate_profile(
                    target.person_id,
                    {"publishing_restricted_at": now, "moderation_reason": why},
                )
            decided = store.report(report_id)
        assert decided is not None
        return decided

    def moderate(
        self,
        handle: str,
        *,
        hidden: bool,
        publishing_restricted: bool,
        reason: str | None,
    ) -> None:
        """Reviewer reversal or direct action, always with a recorded reason."""
        why = policy.moderation_reason(reason)
        if not why:
            raise RuleError("reason_required")
        now = self._clock()
        with self._stores() as store:
            target = store.profile_by_handle(_key(handle))
            if target is None:
                raise NotFound()
            store.moderate_profile(
                target.person_id,
                {
                    "hidden_at": now if hidden else None,
                    "publishing_restricted_at": now if publishing_restricted else None,
                    "moderation_reason": why,
                },
            )

    # -- helpers ---------------------------------------------------------------------

    def _facts(
        self, store: SocialStore, viewer: Actor | None, owner: ProfileRow
    ) -> Facts:
        if viewer is None:
            return Facts()
        me, them = viewer.person_id, owner.person_id
        if me == them:
            return Facts(is_owner=True, signed_in=True)
        return Facts(
            signed_in=True,
            approved_follower=store.follow_status(me, them) == "approved",
            blocked_either_way=store.blocks(me, them) or store.blocks(them, me),
        )

    def _visible(
        self, store: SocialStore, viewer: Actor | None, handle: str
    ) -> tuple[ProfileRow, Facts]:
        row = store.profile_by_handle(_key(handle))
        if row is None:
            raise NotFound()
        facts = self._facts(store, viewer, row)
        if not policy.profile_visible(
            discoverable=row.discoverable, hidden=row.hidden, facts=facts
        ):
            raise NotFound()
        return row, facts

    def _reachable(self, store: SocialStore, actor: Actor, handle: str) -> ProfileRow:
        """Visible to the actor, or already connected by a follow or the actor's block.

        A person who blocked the actor is never reachable by them.
        """
        row = store.profile_by_handle(_key(handle))
        if row is None:
            raise NotFound()
        me, them = actor.person_id, row.person_id
        if me != them and store.blocks(them, me):
            raise NotFound()
        connected = (
            store.blocks(me, them)
            or store.follow_status(me, them) is not None
            or store.follow_status(them, me) is not None
        )
        if not connected:
            facts = self._facts(store, actor, row)
            if not policy.profile_visible(
                discoverable=row.discoverable, hidden=row.hidden, facts=facts
            ):
                raise NotFound()
        return row

    def _venue(self, venue_id: uuid.UUID | None) -> Venue | None:
        if venue_id is None:
            return None
        return self._directory.public_venues([venue_id]).get(venue_id)


def _key(handle: str) -> str:
    return handle.strip().lower()[:40]


def _state(status: str | None) -> FollowState:
    if status == "approved":
        return FollowState.FOLLOWING
    if status == "pending":
        return FollowState.REQUESTED
    return FollowState.NONE
