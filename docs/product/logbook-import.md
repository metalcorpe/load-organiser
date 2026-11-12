# Logbook import from a spreadsheet

Status: implemented on branch `feat/logbook-import` after the owner decision of 2026-11-12 ([beta decisions](beta-decisions.md)). Source of truth: `backend/app/skydiver/imports/` (`policy.py` reads the file and checks rows, `service.py` resolves places and writes) and the page `web/src/routes/(private)/records/import/`.

## What it does

A signed-in jumper chooses a CSV file on Records → Import from a spreadsheet (also linked from an empty Logbook). The service:

1. **Checks** the file and shows what an import would save: the columns it found, how many rows can be imported, the private places it would create, the first 10 rows as they would be saved and the skipped rows with the reason. Nothing is written.
2. **Imports** it after the jumper chooses the same file again and confirms. Everything is written in one transaction, or nothing is.
3. **Undoes** an import on request: every jump it added is deleted, even ones edited since, together with the private places it created that no jump or visit plan uses any more.

Imported jumps are private and self-reported like any other entry. They show as "imported by you, not verified" and keep a `created` history entry marked as imported. An export lists them with source `imported`; restoring that export marks them `restored`, as for every restored jump.

Paper logbooks, FlySight, GPX, FIT and other device files are out of scope.

## The file

- At most 1 MiB and 2,000 data rows (the logbook limit), at most 100 columns.
- UTF-8 with or without a byte-order mark, UTF-16 with a byte-order mark, otherwise read as Windows-1252. The page says when Windows-1252 was used.
- Comma, semicolon or tab separated: the separator used most in the heading line, outside double quotes, wins (ties: comma, then semicolon, then tab).
- The first non-empty row holds the headings. Blank rows are ignored but still counted, so row numbers match the file: row 1 is the first row under the headings.

### Columns

Columns are found by heading, ignoring case and accents, with a few words per language. The jumper can change each choice and check again.

| Field | Headings recognised (examples) |
| --- | --- |
| Date (needed) | Date, Jump date, Fecha, Data, Ημερομηνία |
| Dropzone or place (needed) | Dropzone, DZ, Location, Place, Lugar, Local, Τοποθεσία |
| Jump number | Jump #, #, No, Number, Número, Nº, Αριθμός |
| Type | Type, Discipline, Tipo, Modalidade, Τύπος |
| Exit altitude | Altitude, Exit altitude, Altitud, Altura, Ύψος |
| Freefall seconds | Freefall, Delay, Caída libre, Queda livre, Ελεύθερη πτώση |
| Notes | Notes, Comments, Remarks, Observaciones, Σχόλια |

A trailing unit word in a heading ("Altitude (ft)") is ignored. Other columns are not read.

### Options

- **Date order**: day/month/year (default), month/day/year or year-month-day. `2024-03-12` and any date starting with a four-digit year are always read year first. Two-digit years up to this year are 20xx, later ones 19xx. A time after the date is ignored. Month names are not read.
- **Altitude unit**: feet (default) or metres. The datum is stored as not stated. A value with the other unit written after it is a problem, never converted.
- **Country** for places that are not listed. Needed only when the file has such places; without it the check answers which names need one.

## Row rules

| Value | Rule | Problem code |
| --- | --- | --- |
| Date | Needed, a real date, not after today anywhere (UTC+14), not before 1919 | `jump_date_required`, `jump_date_invalid`, `jump_date_in_future` |
| Place | Needed, at most 120 characters | `location_required`, `place_too_long` |
| Number | Optional whole number 1–1,000,000; `#`, `1,204` and `88.0` are accepted | `jump_number_invalid` |
| Exit altitude | Optional, as for a jump entered by hand (up to 45,000 ft or 13,700 m) | `altitude_invalid` |
| Freefall | Optional, 0–600 seconds; `45`, `45 s` and `1:05` are accepted | `freefall_invalid` |
| Notes | Optional, at most 2,000 characters | `notes_too_long` |

**Type** is read from the words written: belly, RW, FS, formation → belly; freefly, FF, head down, sit → freefly; angle, tracking → angle; wingsuit, WS → wingsuit; canopy, swoop, CP → canopy piloting; CRW, canopy formation → CRW; accuracy → accuracy; hop, hop and pop → hop and pop; tandem → tandem; AFF, training, coach, student → training. Anything else, or nothing, is "not specified".

**Place**, in this order:

1. the exact name or alias (ignoring case and extra spaces) of one listed or closed dropzone in the directory. If several dropzones share the name, the chosen country picks one; otherwise the row is skipped as `place_ambiguous`;
2. the name of one of the jumper's private places (the oldest if several);
3. otherwise a new private place in the chosen country. Rows naming the same new place share it.

**Duplicates** follow the logbook's own duplicate warning. A row whose number is already in the logbook, or a row without a number whose date, place, type, exit altitude, freefall and notes equal an existing jump without a number, is skipped as `likely_duplicate`. A number used twice in the file skips the later row as `repeated_in_file`. Two rows without a number are never treated as duplicates of each other.

Skipped rows are never imported; the jumper fixes the file and checks again if they are wanted.

## Whole-file refusals

Nothing is written when: the file is too large or unreadable, has no headings, too many rows or columns, no date or place column, two fields on one column (`mapping_invalid`), new places but no country (`country_required`), nothing left to import (`nothing_to_import`), the import would pass 2,000 jumps (`jump_limit_reached`) or 200 private places (`place_limit_reached`), or the file and choices differ from the ones checked (`import_changed`).

## Repeats, concurrency and undo

- The fingerprint is the SHA-256 of the exact file bytes plus the date order, unit, country and the columns used. The same fingerprint again answers "already imported" with the original counts and writes nothing. After an undo the same file can be imported again.
- The import row claims the person's next import number and the fingerprint, both unique per person, so two simultaneous imports of the same file write it once.
- The jump and place limits are counted behind the same per-person gate (a row lock on the person, `access.sql.lock_owner`) that adding a private place by hand already used; logging a jump by hand now takes it too. An import and a hand-made jump or place at the same time therefore cannot both pass a limit.
- Undo takes the same per-person gate first, so it never deletes a place an import is reusing, and an import never counts as a duplicate a jump that an undo is deleting. It sets its time only where it is still empty, so a second undo answers `already_undone` and changes nothing. Another person's import answers exactly like a missing one.
- Checks are limited to 60 an hour per account. Import requests are limited to 30 an hour, counted before the file is read, and completed imports to 10 a day: a refused import (nothing to import, a limit, a missing country) does not use the daily quota. An import needs a confirmed email; a check needs only a session.

## Tested and untested

Tested (`backend/tests/test_skydiver_import_policy.py`, `backend/app/tests/skydiver/test_imports.py`, `web/tests/import.e2e.ts`): reading and column detection, row rules, check without writing, import, repeat, duplicates, country requirement, the jump limit, undo and double undo, other people and anonymous callers, an export with imported jumps restored into another account, two imports at once, and an import racing a hand-made jump or place near the limits.

Untested or known limits:

- Real spreadsheets exported by specific logbook apps or Excel versions have not been tried; the synonym list is a first guess.
- An import running at the same time as a restore into empty records is not covered by a test; restore's own recount is the only guard there.
- The import row and its undo time are not in the erasure ledger. After a database restore from backup, an undo made later is replayed as jump and place deletions, but the import still lists as not undone.
- Big files (2,000 rows) were tested for the limit only, not for response time on the production host.
- The file has to be chosen again for each step (no JavaScript upload state is kept), which is clumsy on phones; not validated with users.
- The daily import quota is checked before and counted after an import, so two imports sent at the same moment as the tenth can both complete (at most a few over the 10). The hourly limit on import requests still applies.
- Sending the import form twice (a double click) imports once; the second answer says the file was already imported and was not imported a second time. The button is not disabled while the first request runs.
