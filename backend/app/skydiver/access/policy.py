"""Authorization rules for the beta. Plain values in, decisions out.

Conventions every feature follows:

- Ownership: a personal record belongs to a person (`owner_person_id`). The owner is
  taken from the verified session, never from a request body, file or legacy row.
- Private records: only the owner may read or change them. No role, including
  reviewer, grants access to another person's private records.
- Private writes need a confirmed email address; reads do not.
- Roles are granted by the server (`skydiver_role_grant`). Legacy `is_superuser`
  is not a beta role.
- Shared content: visibility is decided by `may_view` from facts the caller loads
  in the same transaction (approved follow, a block in either direction).
- Denials of a specific object are indistinguishable from absence (404), so a
  probe cannot tell private, blocked, withdrawn and missing apart.
"""

import uuid
from dataclasses import dataclass
from enum import StrEnum


class Role(StrEnum):
    # Reviews listing corrections and reports (#151, #162). Scoped to those cases.
    REVIEWER = "reviewer"


class Audience(StrEnum):
    PRIVATE = "private"
    FOLLOWERS = "followers"
    PUBLIC = "public"


@dataclass(frozen=True)
class Actor:
    """The authenticated caller, resolved by the backend for this request."""

    account_id: uuid.UUID
    person_id: uuid.UUID
    email_verified: bool
    roles: frozenset[Role] = frozenset()

    def has(self, role: Role) -> bool:
        return role in self.roles


def actor_roles(granted: frozenset[str]) -> frozenset[Role]:
    """Known roles only; an unknown stored value grants nothing."""
    known = {role.value for role in Role}
    return frozenset(Role(value) for value in granted if value in known)


def owns(actor: Actor | None, owner_person_id: uuid.UUID) -> bool:
    return actor is not None and actor.person_id == owner_person_id


@dataclass(frozen=True)
class Relationship:
    """Facts between viewer and owner, loaded by the caller in one transaction."""

    approved_follower: bool = False
    blocked_either_way: bool = False


def may_view(
    viewer: Actor | None,
    *,
    owner_person_id: uuid.UUID,
    audience: Audience,
    active: bool,
    relationship: Relationship = Relationship(),
) -> bool:
    """Whether `viewer` (None = anonymous) may see one item owned by someone.

    The owner always sees their own item. Others need it active and an audience
    that admits them. Public items stay anonymously visible; a block only denies
    the authenticated viewer it applies to.
    """
    if owns(viewer, owner_person_id):
        return True
    if not active:
        return False
    if audience is Audience.PUBLIC:
        return viewer is None or not relationship.blocked_either_way
    if audience is Audience.FOLLOWERS:
        return (
            viewer is not None
            and relationship.approved_follower
            and not relationship.blocked_either_way
        )
    return False
