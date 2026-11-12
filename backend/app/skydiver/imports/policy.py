"""Logbook import from a spreadsheet (CSV) as plain values. No framework or SQL.

Reading: at most 1 MiB; UTF-8 with or without a byte-order mark, UTF-16 with a
byte-order mark, otherwise Windows-1252. The delimiter (comma, semicolon or tab)
is sniffed. The first non-empty row holds the column headings; at most 2,000
data rows follow. Columns are recognised by their heading (a few English, Greek,
Spanish and Portuguese words) and the caller may override each one.

Rows: each data row becomes a draft jump checked with the logbook's own rules, or
a problem `{row, code}` (1-based data row, blank rows counted but ignored). Place
names are kept as text here; the service resolves them to a listed dropzone, an
existing private place or a new private place. Nothing here invents a value the
file does not give: a missing altitude, freefall time or number stays empty.
"""

import csv
import hashlib
import io
import json
import re
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum

from app.skydiver.directory import policy as directory
from app.skydiver.directory.policy import DirectoryRuleError as RuleError
from app.skydiver.logbook import policy as logbook
from app.skydiver.logbook.policy import AltitudeUnit, JumpType

RAW_MAX_BYTES = 1024 * 1024
MAX_ROWS = logbook.MAX_JUMPS
MAX_COLUMNS = 100
HEADING_MAX = 80
PROBLEMS_SHOWN = 50
SAMPLE_ROWS = 10

FIELDS = ("date", "number", "place", "type", "altitude", "freefall", "notes")


class ImportRefused(Exception):
    """The whole file or request cannot be used; `code` is the API detail."""

    def __init__(self, code: str, *, names: list[str] | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.names = names or []


class DateOrder(StrEnum):
    DMY = "dmy"
    MDY = "mdy"
    YMD = "ymd"


@dataclass(frozen=True)
class Options:
    date_order: DateOrder = DateOrder.DMY
    unit: AltitudeUnit = AltitudeUnit.FT
    country: str | None = None  # for places that are not listed
    # Per field: a column index, None for "not in this file"; absent means detect.
    mapping: dict[str, int | None] = field(default_factory=dict)


@dataclass(frozen=True)
class Table:
    headings: list[str]
    rows: list[list[str]]  # data rows in file order; blank rows are []
    encoding: str  # utf-8 | utf-16 | windows-1252
    delimiter: str


@dataclass(frozen=True)
class Draft:
    row: int
    jumped_on: date
    jump_number: int | None
    place: str
    jump_type: JumpType
    exit_altitude: int | None
    altitude_unit: AltitudeUnit | None
    freefall_seconds: int | None
    notes: str | None


@dataclass(frozen=True)
class Problem:
    row: int
    code: str


# -- reading ----------------------------------------------------------------------


def decode(raw: bytes) -> tuple[str, str]:
    """The text and the encoding it was read with."""
    if len(raw) > RAW_MAX_BYTES:
        raise ImportRefused("file_too_large")
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return raw.decode("utf-16"), "utf-16"
        except UnicodeDecodeError:
            raise ImportRefused("file_unreadable") from None
    try:
        return raw.decode("utf-8-sig"), "utf-8"
    except UnicodeDecodeError:
        pass
    try:
        return raw.decode("cp1252"), "windows-1252"
    except UnicodeDecodeError:
        raise ImportRefused("file_unreadable") from None


_DELIMITERS = ",;\t"


def _delimiter(text: str) -> str:
    sample = text[:65536]
    first = next((line for line in sample.splitlines() if line.strip()), "")
    try:
        sniffed = csv.Sniffer().sniff(sample, delimiters=_DELIMITERS).delimiter
    except csv.Error:
        sniffed = ""
    if sniffed in _DELIMITERS and sniffed and sniffed in first:
        return sniffed
    # The heading row decides when sniffing is unsure (one row, quoted notes...).
    counts = {d: first.count(d) for d in _DELIMITERS}
    best = max(counts, key=lambda d: counts[d])
    return best if counts[best] else ","


def read_table(raw: bytes) -> Table:
    text, encoding = decode(raw)
    if "\x00" in text:
        raise ImportRefused("file_unreadable")
    delimiter = _delimiter(text)
    try:
        rows = list(csv.reader(io.StringIO(text, newline=""), delimiter=delimiter))
    except csv.Error:
        raise ImportRefused("file_unreadable") from None
    cleaned = [[cell.strip() for cell in row] for row in rows]
    start = next((i for i, r in enumerate(cleaned) if any(r)), None)
    if start is None:
        raise ImportRefused("header_required")
    headings = cleaned[start]
    if len(headings) > MAX_COLUMNS:
        raise ImportRefused("too_many_columns")
    data = [r if any(r) else [] for r in cleaned[start + 1 :]]
    while data and not data[-1]:
        data.pop()
    if sum(1 for r in data if r) > MAX_ROWS:
        raise ImportRefused("too_many_rows")
    return Table(
        headings=[" ".join(h.split())[:HEADING_MAX] for h in headings],
        rows=data,
        encoding=encoding,
        delimiter=delimiter,
    )


# -- columns ----------------------------------------------------------------------

_SYNONYMS: dict[str, tuple[str, ...]] = {
    "date": (
        "date", "jump date", "day", "datum", "fecha", "fecha del salto", "data",
        "data do salto", "dia", "ημερομηνια", "ημερομηνια αλματος",
    ),
    "number": (
        "jump number", "jump no", "jump nr", "jump num", "jump", "number", "no",
        "nr", "num", "n", "numero", "numero de salto", "numero do salto",
        "salto", "salto no", "no salto", "αριθμος", "αριθμος αλματος", "α α", "αλμα",
    ),
    "place": (
        "dropzone", "drop zone", "dz", "location", "place", "airfield", "airport",
        "venue", "site", "lugar", "sitio", "zona de salto", "centro", "local",
        "aerodromo", "τοποθεσια", "τοπος", "αεροδρομιο",
    ),
    "type": (
        "type", "jump type", "discipline", "kind", "category", "activity", "tipo",
        "tipo de salto", "disciplina", "modalidad", "modalidade", "τυπος",
        "τυπος αλματος", "ειδος",
    ),
    "altitude": (
        "exit altitude", "altitude", "exit alt", "alt", "exit height", "height",
        "exit", "altitud", "altitud de salida", "altura", "altura de salida",
        "altitude de saida", "altura de saida", "υψος", "υψος εξοδου",
    ),
    "freefall": (
        "freefall", "free fall", "freefall time", "free fall time", "delay",
        "freefall delay", "freefall seconds", "ff time", "caida libre",
        "tiempo de caida libre", "queda livre", "tempo de queda livre",
        "ελευθερη πτωση", "χρονος ελευθερης πτωσης",
    ),
    "notes": (
        "notes", "note", "comments", "comment", "remarks", "description", "notas",
        "nota", "comentarios", "comentario", "observaciones", "observacoes",
        "σχολια", "σημειωσεις", "παρατηρησεις",
    ),
}  # fmt: skip
# Compared in the same normalised form as headings (Greek final sigma included).
_KEYS = {
    name: frozenset(directory.search_key(w) for w in words)
    for name, words in _SYNONYMS.items()
}
_UNIT_WORDS = {"ft", "feet", "m", "meters", "metres", "s", "sec", "secs", "seconds"}


def heading_key(heading: str) -> str:
    """'Altitude (ft)' -> 'altitude ft'; 'Ημερομηνία' -> 'ημερομηνια'."""
    return directory.search_key(heading)


def _field_of(heading: str) -> str | None:
    if heading.strip() == "#":
        return "number"
    key = heading_key(heading)
    words = key.split()
    candidates = [key]
    if len(words) > 1 and words[-1] in _UNIT_WORDS:
        candidates.append(" ".join(words[:-1]))
    for candidate in candidates:
        for name in FIELDS:
            if candidate in _KEYS[name]:
                return name
    return None


def detect(headings: list[str]) -> dict[str, int | None]:
    """The first column whose heading names each field; None when none does."""
    found: dict[str, int | None] = dict.fromkeys(FIELDS)
    for index, heading in enumerate(headings):
        name = _field_of(heading)
        if name is not None and found[name] is None:
            found[name] = index
    return found


def mapping(headings: list[str], overrides: dict[str, int | None]) -> dict[str, int | None]:  # fmt: skip
    """Detected columns with the caller's overrides; every column used at most once."""
    if any(name not in FIELDS for name in overrides):
        raise ImportRefused("mapping_invalid")
    chosen = detect(headings)
    for name, index in overrides.items():
        if index is not None and not 0 <= index < len(headings):
            raise ImportRefused("mapping_invalid")
        chosen[name] = index
    used = [i for i in chosen.values() if i is not None]
    if len(used) != len(set(used)):
        # A detected column the caller moved elsewhere gives way to the override.
        for name in FIELDS:
            index = chosen[name]
            if name not in overrides and index is not None and used.count(index) > 1:
                chosen[name] = None
                used.remove(index)
        if len(used) != len(set(used)):
            raise ImportRefused("mapping_invalid")
    if chosen["date"] is None:
        raise ImportRefused("date_column_required")
    if chosen["place"] is None:
        raise ImportRefused("place_column_required")
    return chosen


def fingerprint(raw: bytes, options: Options, columns: dict[str, int | None]) -> str:
    """SHA-256 over the exact bytes and the canonical options and columns used."""
    canonical = json.dumps(
        {
            "date_order": options.date_order.value,
            "unit": options.unit.value,
            "country": options.country,
            "columns": {name: columns.get(name) for name in FIELDS},
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(raw)
    digest.update(b"\x00" + canonical.encode())
    return digest.hexdigest()


# -- values -----------------------------------------------------------------------

_ISO = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})$")
_PARTS = re.compile(r"^(\d{1,4})[./\-](\d{1,2})[./\-](\d{1,4})$")


def parse_date(text: str, order: DateOrder, today: date) -> date:
    """A calendar date in the chosen order; ISO yyyy-mm-dd is always accepted.

    A time after the date (spreadsheets often add 00:00) is ignored. Two-digit
    years up to this year's are 20xx, later ones 19xx.
    """
    value = text.strip()
    if not value:
        raise RuleError("jump_date_required")
    value = re.split(r"[\sT]", value, maxsplit=1)[0]
    iso = _ISO.match(value)
    if iso:
        y, m, d = (int(g) for g in iso.groups())
    else:
        parts = _PARTS.match(value)
        if not parts:
            raise RuleError("jump_date_invalid")
        a, b, c = parts.groups()
        if order is DateOrder.YMD or len(a) == 4:
            ys, ms, ds = a, b, c
        elif order is DateOrder.MDY:
            ms, ds, ys = a, b, c
        else:
            ds, ms, ys = a, b, c
        if len(ys) not in (2, 4) or len(ds) > 2:
            raise RuleError("jump_date_invalid")
        y, m, d = int(ys), int(ms), int(ds)
        if len(ys) == 2:
            y += 2000 if y <= today.year % 100 else 1900
    try:
        parsed = date(y, m, d)
    except ValueError:
        raise RuleError("jump_date_invalid") from None
    return logbook.jump_date(parsed, today)


_GROUPED = re.compile(r"^\d{1,3}([,.' ]\d{3})+$")
_WHOLE = re.compile(r"^(\d+)(?:[.,]0+)?$")


def _whole(text: str, code: str) -> int:
    value = text.replace(" ", " ").strip()
    if _GROUPED.match(value):
        value = re.sub(r"[,.' ]", "", value)
    found = _WHOLE.match(value)
    if not found or len(found.group(1)) > 9:
        raise RuleError(code)
    return int(found.group(1))


def parse_number(text: str) -> int | None:
    value = text.strip().lstrip("#").strip()
    if not value:
        return None
    return logbook.jump_number(_whole(value, "jump_number_invalid"))


_UNIT_SUFFIX = re.compile(
    r"^(.*?)\s*(ft|feet|foot|'|m|meters|metres|meter|metre)\.?$", re.I
)


def parse_altitude(text: str, unit: AltitudeUnit) -> int | None:
    value = text.strip()
    if not value:
        return None
    suffix = _UNIT_SUFFIX.match(value)
    if suffix:
        given = AltitudeUnit.M if suffix.group(2).lower().startswith("m") else AltitudeUnit.FT  # fmt: skip
        if given is not unit:
            raise RuleError("altitude_invalid")
        value = suffix.group(1)
    height = _whole(value, "altitude_invalid")
    return logbook.altitudes(height, None, unit, None).exit


_CLOCK = re.compile(r"^(\d{1,2}):(\d{2})$")
_SECONDS = re.compile(r"^(.*?)\s*(s|sec|secs|seconds|seg|segundos|δ)\.?$", re.I)


def parse_freefall(text: str) -> int | None:
    value = text.strip()
    if not value:
        return None
    clock = _CLOCK.match(value)
    if clock:
        minutes, seconds = int(clock.group(1)), int(clock.group(2))
        if seconds >= 60:
            raise RuleError("freefall_invalid")
        return logbook.freefall_seconds(minutes * 60 + seconds)
    suffix = _SECONDS.match(value)
    if suffix:
        value = suffix.group(1)
    return logbook.freefall_seconds(_whole(value, "freefall_invalid"))


# Checked in this order: the first that matches wins ("canopy formation" is CRW,
# "canopy accuracy" is accuracy, "tandem training" is tandem).
_PHRASES: tuple[tuple[str, JumpType], ...] = (
    ("canopy formation", JumpType.CRW),
    ("canopy relative", JumpType.CRW),
    ("hop and pop", JumpType.HOP_AND_POP),
    ("hop n pop", JumpType.HOP_AND_POP),
    ("head down", JumpType.FREEFLY),
)
_WORDS: tuple[tuple[frozenset[str], JumpType], ...] = (
    (frozenset({"crw"}), JumpType.CRW),
    (frozenset({"wingsuit", "ws"}), JumpType.WINGSUIT),
    (frozenset({"tandem"}), JumpType.TANDEM),
    (frozenset({"hop", "hnp"}), JumpType.HOP_AND_POP),
    (frozenset({"aff", "training", "coach", "coached", "student"}), JumpType.TRAINING),
    (frozenset({"accuracy"}), JumpType.ACCURACY),
    (frozenset({"canopy", "swoop", "swooping", "cp"}), JumpType.CANOPY),
    (frozenset({"angle", "tracking", "track"}), JumpType.ANGLE),
    (
        frozenset({"freefly", "ff", "headdown", "hd", "sit", "sitfly", "freeflying"}),
        JumpType.FREEFLY,
    ),
    (frozenset({"belly", "rw", "fs", "formation", "flat"}), JumpType.BELLY),
)  # fmt: skip


def jump_type(text: str) -> JumpType:
    """A jump type from the words a jumper wrote; anything unknown is unspecified."""
    key = directory.search_key(text)
    if not key:
        return JumpType.UNSPECIFIED
    for phrase, kind in _PHRASES:
        if phrase in key:
            return kind
    words = set(key.split())
    for names, kind in _WORDS:
        if words & names:
            return kind
    return JumpType.UNSPECIFIED


def place_name(text: str) -> str:
    try:
        return directory.clean_text(text, field="place", maximum=directory.NAME_MAX)
    except RuleError as error:
        code = "location_required" if error.code == "place_required" else error.code
        raise RuleError(code) from None


def place_key(name: str) -> str:
    """Exact, case-insensitive comparison key for a place or dropzone name."""
    return " ".join(name.split()).casefold()


# -- rows -------------------------------------------------------------------------


def drafts(
    table: Table, columns: dict[str, int | None], options: Options, today: date
) -> tuple[list[Draft], list[Problem]]:
    """Every non-blank data row as a draft jump or as a problem with its rule code."""
    ok: list[Draft] = []
    problems: list[Problem] = []

    def cell(row: list[str], name: str) -> str:
        index = columns.get(name)
        return row[index] if index is not None and index < len(row) else ""

    for position, row in enumerate(table.rows, start=1):
        if not row:
            continue
        try:
            jumped_on = parse_date(cell(row, "date"), options.date_order, today)
            place = place_name(cell(row, "place"))
            number = parse_number(cell(row, "number"))
            altitude = parse_altitude(cell(row, "altitude"), options.unit)
            freefall = parse_freefall(cell(row, "freefall"))
            notes = logbook.notes(cell(row, "notes"))
        except RuleError as error:
            problems.append(Problem(position, error.code))
            continue
        ok.append(
            Draft(
                row=position,
                jumped_on=jumped_on,
                jump_number=number,
                place=place,
                jump_type=jump_type(cell(row, "type")),
                exit_altitude=altitude,
                altitude_unit=options.unit if altitude is not None else None,
                freefall_seconds=freefall,
                notes=notes,
            )
        )
    return ok, problems
