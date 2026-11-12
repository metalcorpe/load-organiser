"""The owner's jumps as a spreadsheet (CSV) as plain values. No framework or SQL.

UTF-8 with a byte-order mark (so Excel reads the accents), comma-separated, CRLF
line ends and RFC 4180 quoting: a value with a comma, a double quote or a line
break is quoted, and its double quotes doubled. A text cell that a spreadsheet
would read as a formula (starting with = + - @, a tab or a carriage return) gets a
leading apostrophe, and so does one already starting with an apostrophe; the
logbook import removes exactly that one apostrophe again.

The headings are ones the logbook import recognises, so the file imports back into
an empty account as the same jumps. Gear used is written as text (the labels, then
any other equipment, cut to 200 characters with an ellipsis) and comes back as
"other equipment", not as gear links. Repeated jump numbers do not come back: the
import keeps the first row with a number and skips the later ones. Exit
time, time zone, altitude datum and links are not columns; the full export (JSON)
keeps everything.
"""

import csv
import io
from dataclasses import dataclass
from datetime import date

HEADINGS = (
    "Date",
    "Jump number",
    "Place",
    "Country",
    "Type",
    "Aircraft",
    "Exit altitude",
    "Altitude unit",
    "Deployment altitude",
    "Freefall seconds",
    "Notes",
    "Gear",
)

# Words the import reads back as the same type (imports/policy.py jump_type).
TYPE_TEXT = {
    "unspecified": "",
    "belly": "Belly",
    "freefly": "Freefly",
    "angle": "Angle",
    "wingsuit": "Wingsuit",
    "canopy": "Canopy",
    "crw": "CRW",
    "accuracy": "Accuracy",
    "hop_and_pop": "Hop and pop",
    "tandem": "Tandem",
    "training": "Training",
    "other": "Other",
}

BOM = "\ufeff"
# The import keeps gear text as "other equipment", at most 200 characters: a longer
# Gear cell is cut to fit with an ellipsis, so the file still imports.
GEAR_MAX = 200
_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


@dataclass(frozen=True)
class Row:
    jumped_on: date
    jump_number: int | None
    place: str  # as named now; empty for a dropzone no longer listed
    country: str | None
    jump_type: str
    aircraft: str | None
    exit_altitude: int | None
    altitude_unit: str | None
    deployment_altitude: int | None
    freefall_seconds: int | None
    notes: str | None
    gear: list[str]  # component labels, then other equipment


def guard(value: str) -> str:
    """Text a spreadsheet would run as a formula starts with an apostrophe instead
    (and so does text already starting with one, so the import restores it exactly)."""
    # Leading spaces do not stop a spreadsheet from reading a formula.
    start = value.lstrip(" ")
    return f"'{value}" if start.startswith((*_FORMULA_START, "'")) else value


def gear_text(parts: list[str]) -> str:
    """Labels and other equipment in one cell, cut to GEAR_MAX with an ellipsis."""
    text = "; ".join(parts)
    if len(text) <= GEAR_MAX:
        return text
    return text[: GEAR_MAX - 1].rstrip() + "\u2026"


def _text(value: str | None) -> str:
    return guard(value) if value else ""


def _number(value: int | None) -> str:
    return "" if value is None else str(value)


def render(rows: list[Row]) -> bytes:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(HEADINGS)
    for r in rows:
        writer.writerow(
            [
                r.jumped_on.isoformat(),
                _number(r.jump_number),
                _text(r.place),
                r.country or "",
                TYPE_TEXT.get(r.jump_type, ""),
                _text(r.aircraft),
                _number(r.exit_altitude),
                r.altitude_unit or "",
                _number(r.deployment_altitude),
                _number(r.freefall_seconds),
                _text(r.notes),
                _text(gear_text(r.gear)),
            ]
        )
    return (BOM + out.getvalue()).encode("utf-8")
