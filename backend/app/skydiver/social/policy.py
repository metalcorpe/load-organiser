"""Profiles, follows, blocks and profile reports (#156) as plain values.

- A profile is opt-in and separate from the account: a stable handle, a display
  name and optional bio, disciplines and home dropzone. Nothing is copied from the
  private account (email, registration name), logbook, gear or totals.
- Who sees a profile: its owner always. Anyone else only while a reviewer has not
  hidden it and, for a signed-in viewer, no block exists in either direction; then
  if it is discoverable (also anonymously) or the viewer is an approved follower.
- Follows always need the followed person's approval. A follow is never access to
  private records; it only admits the follower to follower-shared content (#157).
- A block in either direction removes both follows and denies the other person's
  profile, search result, follow and report routes while signed in.
"""

import re
from dataclasses import dataclass
from enum import StrEnum

from app.skydiver.directory import policy as directory
from app.skydiver.directory.policy import DirectoryRuleError as RuleError

HANDLE = re.compile(r"^[a-z][a-z0-9_]{2,29}$")
RESERVED = frozenset(
    {
        "admin", "administrator", "api", "help", "load_organiser", "loadorganiser",
        "moderator", "new", "official", "organiser", "review", "reviewer", "root",
        "settings", "staff", "support", "system",
    }
)  # fmt: skip
DISPLAY_NAME_MAX = 60
BIO_MAX = 280
DISCIPLINES_MAX = 5
DISCIPLINES = frozenset(
    {
        "belly", "freefly", "angle", "wingsuit", "canopy", "crw", "accuracy",
        "hop_and_pop", "tandem", "training",
    }
)  # fmt: skip
MAX_FOLLOWING = 500  # outgoing follows and requests
MAX_BLOCKS = 500
REPORT_NOTE_MAX = 1000
# Shown to the profile owner; stored in varchar(280) columns.
MODERATION_REASON_MAX = 280
SEARCH_MIN = 2
SEARCH_MAX = 40


class FollowState(StrEnum):
    NONE = "none"
    REQUESTED = "requested"  # the viewer asked; not yet approved
    FOLLOWING = "following"


class ReportReason(StrEnum):
    IMPERSONATION = "impersonation"
    HARASSMENT = "harassment"
    SPAM = "spam"
    INAPPROPRIATE = "inappropriate"
    OTHER = "other"


class Decision(StrEnum):
    NO_ACTION = "no_action"
    HIDE_PROFILE = "hide_profile"
    RESTRICT_PUBLISHING = "restrict_publishing"


def handle(value: str) -> str:
    key = value.strip().lower()
    if not HANDLE.match(key):
        raise RuleError("handle_invalid")
    if key in RESERVED:
        raise RuleError("handle_reserved")
    return key


def display_name(value: str) -> str:
    return directory.clean_text(value, field="display_name", maximum=DISPLAY_NAME_MAX)


def bio(value: str | None) -> str | None:
    return directory.optional_text(value, field="bio", maximum=BIO_MAX)


def disciplines(values: list[str] | None) -> list[str]:
    chosen: list[str] = []
    for value in values or []:
        if value not in DISCIPLINES:
            raise RuleError("discipline_invalid")
        if value not in chosen:
            chosen.append(value)
    if len(chosen) > DISCIPLINES_MAX:
        raise RuleError("too_many_disciplines")
    return chosen


def report_note(value: str | None) -> str | None:
    return directory.optional_text(value, field="note", maximum=REPORT_NOTE_MAX)


def moderation_reason(value: str | None) -> str | None:
    return directory.optional_text(
        value, field="reason", maximum=MODERATION_REASON_MAX
    )


def search_query(value: str) -> str:
    query = " ".join(value.split()).lower()[:SEARCH_MAX]
    if len(query) < SEARCH_MIN:
        raise RuleError("query_too_short")
    return query


@dataclass(frozen=True)
class Facts:
    """Between a viewer and a profile's owner, loaded in one transaction."""

    is_owner: bool = False
    signed_in: bool = False
    approved_follower: bool = False  # the viewer follows the owner, approved
    blocked_either_way: bool = False


def profile_visible(*, discoverable: bool, hidden: bool, facts: Facts) -> bool:
    if facts.is_owner:
        return True
    if hidden:
        return False
    if facts.signed_in and facts.blocked_either_way:
        return False
    return discoverable or (facts.signed_in and facts.approved_follower)


def may_request_follow(
    *, visible: bool, facts: Facts, requester_has_profile: bool
) -> str | None:
    """None when allowed, else the refusal code (a hidden profile reads as absent)."""
    if facts.is_owner:
        return "follow_self"
    if not visible or facts.blocked_either_way:
        return "not_found"
    if not requester_has_profile:
        return "profile_required"
    return None
