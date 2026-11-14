"""Directory rules (#148). Plain values only; no FastAPI, SQL or settings.

Identity rules:
- A venue's UUID never changes. A rename keeps the venue and records the previous
  name as a `former` alias; a relocation changes location fields on the same venue.
- A duplicate is resolved only by an explicit reviewed merge: the source venue
  becomes `merged` and points at the target. References to the source keep their
  ID and are resolved to the target when read, so no private record is rewritten.
- Names never merge automatically: equal names in different places stay distinct.
- Closing keeps a venue selectable and visible as historical, so past records
  remain meaningful.
"""

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from urllib.parse import urlsplit

from app.skydiver.directory.countries import ISO_COUNTRIES

NAME_MAX = 120
LOCALITY_MAX = 120
ALIAS_MAX = 120
SOURCE_URL_MAX = 2048
SOURCE_NOTE_MAX = 280
# Source-stated details (owner decision 2026-11-14): who runs the place, its season and
# aircraft. They name the operator; they do not claim, endorse or verify anything.
OPERATORS_MAX = 4
OPERATOR_NAME_MAX = 120
DETAIL_MAX = 160
PAGE_DEFAULT = 20
PAGE_MAX = 50
# Map points are small (no aliases or sources); one page covers a continent's dropzones.
POINTS_PAGE_DEFAULT = 1000
POINTS_PAGE_MAX = 1000
QUERY_MAX = 80
# Review cadence (release brief, operating default): recheck listed profiles after
# 60 days without a successful source check.
PROFILE_RECHECK_DAYS = 60


class VenueStatus(StrEnum):
    DRAFT = "draft"  # reviewer-only; not public
    LISTED = "listed"
    CLOSED = "closed"  # historical: public and selectable, labelled closed
    MERGED = "merged"  # resolved to `merged_into`


PUBLIC_STATUSES = frozenset({VenueStatus.LISTED, VenueStatus.CLOSED})


class AliasKind(StrEnum):
    ALTERNATE = "alternate"  # another current name or spelling
    FORMER = "former"  # recorded automatically on rename
    MERGED = "merged"  # the name of a venue merged into this one


class DirectoryRuleError(ValueError):
    """A request that breaks a directory rule; `code` is the API error detail."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def clean_text(value: str, *, field: str, maximum: int) -> str:
    """Trim and collapse whitespace; reject empty or over-long values."""
    cleaned = " ".join(unicodedata.normalize("NFC", value).split())
    if not cleaned:
        raise DirectoryRuleError(f"{field}_required")
    if len(cleaned) > maximum:
        raise DirectoryRuleError(f"{field}_too_long")
    return cleaned


def optional_text(value: str | None, *, field: str, maximum: int) -> str | None:
    if value is None or not value.strip():
        return None
    return clean_text(value, field=field, maximum=maximum)


def country_code(value: str) -> str:
    code = value.strip().upper()
    if code not in ISO_COUNTRIES:
        raise DirectoryRuleError("country_invalid")
    return code


def coordinates(
    latitude: float | None, longitude: float | None
) -> tuple[float | None, float | None]:
    if (latitude is None) != (longitude is None):
        raise DirectoryRuleError("coordinates_incomplete")
    if latitude is None or longitude is None:
        return None, None
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise DirectoryRuleError("coordinates_invalid")
    return round(latitude, 6), round(longitude, 6)


def source_url(value: str) -> str:
    """Listed venues are source-backed: an absolute http(s) URL is required."""
    return web_url(value, code="source_url_invalid")


def web_url(value: str, *, code: str) -> str:
    """An absolute http(s) URL without credentials, refused with `code` otherwise."""
    url = value.strip()
    parts = urlsplit(url)
    if (
        len(url) > SOURCE_URL_MAX
        or parts.scheme not in ("http", "https")
        or not parts.hostname
        or parts.username
        or parts.password
    ):
        raise DirectoryRuleError(code)
    return url


def operators(raw: object) -> list[dict[str, str | None]]:
    """Who runs the place, as its source states: up to OPERATORS_MAX names, each with
    an optional web link. Repeated names (case- and accent-insensitive) are refused."""
    if not isinstance(raw, list | tuple):
        raise DirectoryRuleError("operators_invalid")
    if len(raw) > OPERATORS_MAX:
        raise DirectoryRuleError("operators_too_many")
    cleaned: list[dict[str, str | None]] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            raise DirectoryRuleError("operators_invalid")
        name = clean_text(
            str(item.get("name") or ""),
            field="operator_name",
            maximum=OPERATOR_NAME_MAX,
        )
        if search_key(name) in seen:
            raise DirectoryRuleError("operator_repeated")
        seen.add(search_key(name))
        url = item.get("url")
        cleaned.append(
            {
                "name": name,
                "url": web_url(str(url), code="operator_url_invalid") if url else None,
            }
        )
    return cleaned


def checked_on(value: date, today: date) -> date:
    if value > today:
        raise DirectoryRuleError("checked_on_in_future")
    return value


def search_key(text: str) -> str:
    """Accent- and case-insensitive key: 'Skydive Spaá' and 'skydive spaa' match."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(re.sub(r"[\W_]+", " ", stripped.casefold()).split())


def page_size(
    requested: int | None, *, default: int = PAGE_DEFAULT, maximum: int = PAGE_MAX
) -> int:
    if requested is None:
        return default
    return max(1, min(requested, maximum))


@dataclass(frozen=True)
class MergeCheck:
    source_status: VenueStatus
    target_status: VenueStatus
    same_venue: bool


def check_merge(check: MergeCheck) -> None:
    """A merge joins two distinct, unmerged venues into a public or draft target."""
    if check.same_venue:
        raise DirectoryRuleError("merge_into_self")
    if VenueStatus.MERGED in (check.source_status, check.target_status):
        raise DirectoryRuleError("merge_already_merged")
    if (
        check.source_status in PUBLIC_STATUSES
        and check.target_status not in PUBLIC_STATUSES
    ):
        # References to a public venue must keep resolving to a public one.
        raise DirectoryRuleError("merge_target_not_public")


def check_transition(current: VenueStatus, new: VenueStatus) -> None:
    """Status changes other than merging. A merged venue is final."""
    if current is VenueStatus.MERGED or new is VenueStatus.MERGED:
        raise DirectoryRuleError("status_change_invalid")
    if new is VenueStatus.DRAFT and current is not VenueStatus.DRAFT:
        # Unlisting a public venue would break references; close it instead.
        raise DirectoryRuleError("status_change_invalid")
