"""Logbook import from a spreadsheet: reading and row rules as plain values (no database)."""

from datetime import date

import pytest

from app.skydiver.directory.policy import DirectoryRuleError
from app.skydiver.imports import policy
from app.skydiver.imports.policy import DateOrder, ImportRefused, Options
from app.skydiver.logbook.policy import AltitudeUnit, JumpType

TODAY = date(2026, 11, 12)


def _refused(raw: bytes) -> str:
    with pytest.raises(ImportRefused) as raised:
        policy.read_table(raw)
    return raised.value.code


def _rule(call: object) -> str:
    with pytest.raises(DirectoryRuleError) as raised:
        call()  # type: ignore[operator]
    return raised.value.code


# -- reading ----------------------------------------------------------------------


@pytest.mark.parametrize("delimiter", [",", ";", "\t"])
def test_comma_semicolon_and_tab_files_read_the_same(delimiter: str) -> None:
    lines = [["Date", "Dropzone", "Notes"], ["12/03/2024", "Empuriabrava", "a, b; c"]]
    text = "\n".join(
        delimiter.join(f'"{c}"' if any(d in c for d in ",;\t") else c for c in row)
        for row in lines
    )
    table = policy.read_table(text.encode())
    assert table.delimiter == delimiter
    assert table.headings == ["Date", "Dropzone", "Notes"]
    assert table.rows == [["12/03/2024", "Empuriabrava", "a, b; c"]]


def test_a_byte_order_mark_is_not_part_of_the_first_heading() -> None:
    table = policy.read_table("﻿Date,Place\n2024-03-12,Farm\n".encode())
    assert table.encoding == "utf-8"
    assert table.headings == ["Date", "Place"]


def test_utf16_with_a_byte_order_mark_is_read() -> None:
    table = policy.read_table("Date\tPlace\n2024-03-12\tΜέγαρα\n".encode("utf-16"))
    assert table.encoding == "utf-16"
    assert table.rows == [["2024-03-12", "Μέγαρα"]]


def test_a_file_that_is_not_utf8_is_read_as_windows_1252() -> None:
    table = policy.read_table("Fecha;Lugar\n01/02/2020;Ñandú\n".encode("cp1252"))
    assert table.encoding == "windows-1252"
    assert table.rows == [["01/02/2020", "Ñandú"]]


def test_blank_rows_are_kept_in_position_and_trailing_ones_dropped() -> None:
    table = policy.read_table(b"\n\nDate,Place\n2024-03-12,A\n,\n2024-03-13,B\n\n\n")
    assert table.rows == [["2024-03-12", "A"], [], ["2024-03-13", "B"]]


def test_limits_and_unreadable_files_refuse_the_whole_file() -> None:
    assert _refused(b"") == "header_required"
    assert _refused(b" , \n") == "header_required"
    assert _refused(b"Date\n" + b"x" * policy.RAW_MAX_BYTES) == "file_too_large"
    assert _refused(b"Date,Place\n\x00\n") == "file_unreadable"
    assert _refused(",".join(["h"] * 101).encode()) == "too_many_columns"
    rows = b"\n".join([b"Date,Place"] + [b"2024-01-01,A"] * (policy.MAX_ROWS + 1))
    assert _refused(rows) == "too_many_rows"
    exact = b"\n".join([b"Date,Place"] + [b"2024-01-01,A"] * policy.MAX_ROWS)
    assert len(policy.read_table(exact).rows) == policy.MAX_ROWS


# -- columns ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("headings", "expected"),
    [
        (
            ["Date", "Jump #", "DZ", "Type", "Altitude (ft)", "Freefall", "Comments"],
            {"date": 0, "number": 1, "place": 2, "type": 3, "altitude": 4, "freefall": 5, "notes": 6},
        ),
        (
            ["#", "Jump date", "Drop zone", "Discipline", "Exit altitude", "Delay", "Remarks"],
            {"date": 1, "number": 0, "place": 2, "type": 3, "altitude": 4, "freefall": 5, "notes": 6},
        ),
        (
            ["Fecha", "Número", "Lugar", "Tipo", "Altitud", "Caída libre", "Observaciones"],
            {"date": 0, "number": 1, "place": 2, "type": 3, "altitude": 4, "freefall": 5, "notes": 6},
        ),
        (
            ["Data", "Nº", "Local", "Modalidade", "Altura", "Queda livre", "Observações"],
            {"date": 0, "number": 1, "place": 2, "type": 3, "altitude": 4, "freefall": 5, "notes": 6},
        ),
        (
            ["Ημερομηνία", "Αριθμός", "Τοποθεσία", "Τύπος", "Ύψος", "Ελεύθερη πτώση", "Σχόλια"],
            {"date": 0, "number": 1, "place": 2, "type": 3, "altitude": 4, "freefall": 5, "notes": 6},
        ),
        (
            ["Date", "Location", "Something else"],
            {"date": 0, "number": None, "place": 1, "type": None, "altitude": None, "freefall": None, "notes": None},
        ),
    ],
)  # fmt: skip
def test_columns_are_detected_by_heading_synonyms(
    headings: list[str], expected: dict[str, int | None]
) -> None:
    assert policy.mapping(headings, {}) == expected


def test_overrides_replace_or_remove_detected_columns() -> None:
    headings = ["Date", "Place", "Notes", "Comments"]
    assert policy.mapping(headings, {"notes": 3})["notes"] == 3
    assert policy.mapping(headings, {"notes": None})["notes"] is None
    # A column moved to another field leaves the field that detected it.
    moved = policy.mapping(headings, {"type": 2})
    assert (moved["type"], moved["notes"]) == (2, None)


@pytest.mark.parametrize(
    ("headings", "overrides", "code"),
    [
        (["Place"], {}, "date_column_required"),
        (["Date"], {}, "place_column_required"),
        (["Date", "Place"], {"date": None}, "date_column_required"),
        (["Date", "Place"], {"notes": 5}, "mapping_invalid"),
        (["Date", "Place"], {"date": 1, "place": 1}, "mapping_invalid"),
        (["Date", "Place"], {"colour": 1}, "mapping_invalid"),
    ],
)
def test_impossible_column_choices_are_refused(
    headings: list[str], overrides: dict[str, int | None], code: str
) -> None:
    with pytest.raises(ImportRefused) as raised:
        policy.mapping(headings, overrides)
    assert raised.value.code == code


def test_the_fingerprint_covers_bytes_options_and_columns() -> None:
    raw = b"Date,Place\n2024-03-12,A\n"
    columns = policy.mapping(["Date", "Place"], {})
    base = policy.fingerprint(raw, Options(), columns)
    assert base == policy.fingerprint(raw, Options(), dict(columns))
    assert base != policy.fingerprint(raw + b"\n", Options(), columns)
    assert base != policy.fingerprint(raw, Options(unit=AltitudeUnit.M), columns)
    assert base != policy.fingerprint(raw, Options(country="PT"), columns)
    assert base != policy.fingerprint(raw, Options(), columns | {"notes": 1})


# -- values -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "order", "expected"),
    [
        ("12/03/2024", DateOrder.DMY, date(2024, 3, 12)),
        ("12.03.2024", DateOrder.DMY, date(2024, 3, 12)),
        ("12-3-24", DateOrder.DMY, date(2024, 3, 12)),
        ("03/12/2024", DateOrder.MDY, date(2024, 3, 12)),
        ("2024/03/12", DateOrder.YMD, date(2024, 3, 12)),
        ("2024/03/12", DateOrder.DMY, date(2024, 3, 12)),  # year first is clear
        ("2024-03-12", DateOrder.MDY, date(2024, 3, 12)),  # ISO always
        ("2024-03-12 00:00:00", DateOrder.DMY, date(2024, 3, 12)),
        ("2024-03-12T10:00", DateOrder.DMY, date(2024, 3, 12)),
        ("01/01/99", DateOrder.DMY, date(1999, 1, 1)),
        ("01/01/26", DateOrder.DMY, date(2026, 1, 1)),
    ],
)
def test_dates_follow_the_chosen_order(text: str, order: DateOrder, expected: date) -> None:  # fmt: skip
    assert policy.parse_date(text, order, TODAY) == expected


@pytest.mark.parametrize(
    ("text", "order", "code"),
    [
        ("", DateOrder.DMY, "jump_date_required"),
        ("31/02/2024", DateOrder.DMY, "jump_date_invalid"),
        ("12/31/2024", DateOrder.DMY, "jump_date_invalid"),
        ("12 March 2024", DateOrder.DMY, "jump_date_invalid"),
        ("13/11/2026", DateOrder.DMY, "jump_date_in_future"),
        ("01/01/1900", DateOrder.DMY, "jump_date_invalid"),
    ],
)
def test_dates_that_are_not_real_or_in_the_future_are_problems(
    text: str, order: DateOrder, code: str
) -> None:
    assert _rule(lambda: policy.parse_date(text, order, TODAY)) == code


def test_numbers_altitudes_and_freefall_accept_common_spreadsheet_forms() -> None:
    assert policy.parse_number("") is None
    assert policy.parse_number("#1,204") == 1204
    assert policy.parse_number("88.0") == 88
    assert _rule(lambda: policy.parse_number("0")) == "jump_number_invalid"
    assert _rule(lambda: policy.parse_number("12a")) == "jump_number_invalid"
    assert policy.parse_altitude("13,500", AltitudeUnit.FT) == 13500
    assert policy.parse_altitude("13 500 ft", AltitudeUnit.FT) == 13500
    assert policy.parse_altitude("4000m", AltitudeUnit.M) == 4000
    assert policy.parse_altitude(" ", AltitudeUnit.FT) is None
    assert _rule(lambda: policy.parse_altitude("4000m", AltitudeUnit.FT)) == "altitude_invalid"  # fmt: skip
    assert _rule(lambda: policy.parse_altitude("50000", AltitudeUnit.FT)) == "altitude_invalid"  # fmt: skip
    assert policy.parse_freefall("60") == 60
    assert policy.parse_freefall("45 s") == 45
    assert policy.parse_freefall("1:05") == 65
    assert policy.parse_freefall("") is None
    assert _rule(lambda: policy.parse_freefall("1:75")) == "freefall_invalid"
    assert _rule(lambda: policy.parse_freefall("601")) == "freefall_invalid"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Belly", JumpType.BELLY), ("RW", JumpType.BELLY), ("FS 4-way", JumpType.BELLY),
        ("formation", JumpType.BELLY), ("Freefly", JumpType.FREEFLY), ("FF", JumpType.FREEFLY),
        ("head down", JumpType.FREEFLY), ("sit", JumpType.FREEFLY), ("Angle", JumpType.ANGLE),
        ("tracking", JumpType.ANGLE), ("Wingsuit", JumpType.WINGSUIT), ("WS", JumpType.WINGSUIT),
        ("canopy", JumpType.CANOPY), ("Swoop", JumpType.CANOPY), ("CP", JumpType.CANOPY),
        ("CRW", JumpType.CRW), ("canopy formation", JumpType.CRW),
        ("Accuracy", JumpType.ACCURACY), ("canopy accuracy", JumpType.ACCURACY),
        ("hop", JumpType.HOP_AND_POP), ("Hop and pop", JumpType.HOP_AND_POP),
        ("hop_and_pop", JumpType.HOP_AND_POP), ("Tandem", JumpType.TANDEM),
        ("AFF level 3", JumpType.TRAINING), ("coach jump", JumpType.TRAINING),
        ("student", JumpType.TRAINING), ("", JumpType.UNSPECIFIED),
        ("demo", JumpType.UNSPECIFIED), ("other", JumpType.UNSPECIFIED),
    ],
)  # fmt: skip
def test_jump_types_come_from_the_words_written(text: str, expected: JumpType) -> None:
    assert policy.jump_type(text) == expected


# -- rows -------------------------------------------------------------------------


def test_rows_become_drafts_or_problems_by_data_row() -> None:
    raw = (
        "Date,No,DZ,Type,Alt,Freefall,Notes\n"
        "12/03/2024,101,  Skydive  Spain ,FS,13500,60,first\n"
        "\n"
        "31/02/2024,102,Farm,,,,\n"
        "13/03/2024,103,,,,,\n"
        "14/03/2024,,Farm,,,,\n"
        f"15/03/2024,,Farm,,,,{'n' * 2001}\n"
    ).encode()
    table = policy.read_table(raw)
    columns = policy.mapping(table.headings, {})
    drafts, problems = policy.drafts(table, columns, Options(), TODAY)
    assert [(p.row, p.code) for p in problems] == [
        (3, "jump_date_invalid"),
        (4, "location_required"),
        (6, "notes_too_long"),
    ]
    first, second = drafts
    assert (first.row, first.place, first.jump_number) == (1, "Skydive Spain", 101)
    assert (first.exit_altitude, first.altitude_unit) == (13500, AltitudeUnit.FT)
    assert (first.freefall_seconds, first.notes) == (60, "first")
    # Nothing is invented: no altitude means no unit; no type means unspecified.
    assert (second.row, second.jump_number, second.exit_altitude) == (5, None, None)
    assert (second.altitude_unit, second.jump_type) == (None, JumpType.UNSPECIFIED)


def test_short_rows_read_missing_cells_as_empty() -> None:
    table = policy.read_table(b"Date,Place,Notes\n2024-03-12,Farm\n")
    drafts, problems = policy.drafts(
        table, policy.mapping(table.headings, {}), Options(), TODAY
    )
    assert problems == [] and drafts[0].notes is None


def test_place_keys_compare_exactly_but_ignore_case_and_spacing() -> None:
    assert policy.place_key("Skydive  Spain") == policy.place_key("SKYDIVE SPAIN")
    assert policy.place_key("Skydive Spain") != policy.place_key("Skydive Spáin")
