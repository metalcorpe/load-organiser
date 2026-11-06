"""Published jump summaries (#157) as plain values.

- Logging stays private. Publishing is a separate action from a preview of one
  jump version: the activity date always, and only the selected type, listed
  dropzone, exit altitude and freefall time, plus an optional caption and link.
  Never notes, private links, gear, serials, jump number, exit time or a private
  place.
- Audience: approved followers (the current approved set, including people
  approved later) or public (anyone, also signed out, while the profile is
  discoverable). Blocks in either direction deny a signed-in reader.
- A source edit that changes a shared value withdraws the post in the same
  transaction; edits to unshared fields leave it as it is. Deleting the jump
  deletes the post. Republishing needs a new preview. Nothing is copied later.
"""

from enum import StrEnum

from app.skydiver.directory import policy as directory
from app.skydiver.directory.policy import DirectoryRuleError as RuleError
from app.skydiver.logbook import policy as logbook

CAPTION_MAX = 280


class Audience(StrEnum):
    FOLLOWERS = "followers"
    PUBLIC = "public"


class Share(StrEnum):
    """Optional parts of a summary. The activity date is always shared."""

    TYPE = "type"
    VENUE = "venue"
    ALTITUDE = "altitude"
    FREEFALL = "freefall"


# Jump fields whose change withdraws a post that shares this part. `None` = always.
SOURCE_FIELDS: dict[str, Share | None] = {
    "jumped_on": None,
    "jump_type": Share.TYPE,
    "venue_id": Share.VENUE,
    "place_id": Share.VENUE,
    "exit_altitude": Share.ALTITUDE,
    "altitude_unit": Share.ALTITUDE,
    "altitude_datum": Share.ALTITUDE,
    "freefall_seconds": Share.FREEFALL,
}


def touched(changed: set[str]) -> tuple[bool, set[Share]]:
    """(the date changed, the optional parts whose source changed)."""
    parts = {part for name in changed if (part := SOURCE_FIELDS.get(name))}
    return "jumped_on" in changed, parts


def caption(value: str | None) -> str | None:
    return directory.optional_text(value, field="caption", maximum=CAPTION_MAX)


def link(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    return logbook.links([value])[0]


def shares(values: list[str] | None) -> set[Share]:
    try:
        return {Share(v) for v in values or []}
    except ValueError:
        raise RuleError("share_invalid") from None
