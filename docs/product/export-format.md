# Personal records export format, version 1

Status: implemented in #155. Source of truth: `backend/app/skydiver/records/format.py` (schema) and `records/policy.py` (rules checked on restore). This page describes the file for people and other tools; it is not a promise of compatibility beyond version 1.

## The file

One UTF-8 JSON object, compact, downloaded from Profile → Your data as `load-organiser-records-YYYY-MM-DD.json` (the UTC date of the export; the name holds no account detail). Exports are free, need only a signed-in session, and are limited to one every five minutes per account.

```json
{
  "format": "load-organiser.personal-records",
  "version": 1,
  "exported_at": "2026-11-03T12:00:00Z",
  "records": { "...": "see below" },
  "references": { "venues": [], "listings": [] }
}
```

Every object rejects unknown keys and every list is bounded, so a valid file can carry nothing but these records.

## Conventions

- **Dates** (`jumped_on`, `before_on`, `done_on`, `from_on`, plan dates…) are ISO calendar dates as entered, never shifted by a time zone.
- **Instants** (`exported_at`, `created_at`, `updated_at`, `archived_at`) are UTC ISO 8601 with `Z`.
- **Exit time** is the local time as entered (`HH:MM:SS`) with its IANA `time_zone`; both or neither.
- **Altitudes** keep the unit (`ft`/`m`) and datum (`unspecified`/`agl`/`msl`) they were entered with. No normalised value is included.
- **Partial dates** for gear (`manufactured`, `acquired`) keep their precision: `YYYY`, `YYYY-MM` or `YYYY-MM-DD`.
- **IDs** only link records inside the file. A restore gives every record a new ID.
- Unknown values are `null`, never zero.

## `records`

| Key | Contents (limit) |
| --- | --- |
| `places` | Private places: name, country, optional link to a public venue (200) |
| `components` | Gear: kind, label, manufacturer, model, serial as entered, partial dates, relation, acquisition, notes, your reserve repack interval (`repack_interval_days`, 1–730, optional) and end-of-life date (`end_of_life_on`, optional), your one jump-count limit (`jump_limit` 1–100,000, `jump_limit_label`, `jump_limit_service_kind`: all three or none, optional), a main or reserve canopy's size (`canopy_size_sqft`, 20–400 square feet, optional; refused on other kinds), archived time (50). Files without these optional keys restore with none set |
| `rigs` | Rig label and archived time (20) |
| `rig_stints` | Which component was in which rig, `from_on`/`until_on` (never overlapping per component) |
| `service_entries` | Kind, done/due dates, performed by, notes (100 per component) |
| `gear_events` | Gear history: kind, detail, time |
| `jumps` | Every jump field, its `links` (5), `component_ids` actually used (10) and `source` (`manual`/`restored`/`imported`) (2,000). `aircraft` (free text, at most 60 characters) and `exit_weight_grams` (the exit weight on that jump, 30,000–250,000 grams) are optional: files without them restore with none |
| `jump_events` | Jump history: `created`, `corrected` (earlier and new facts; notes/links only "changed"; a change of many jumps adds `batch` with its ID, the version it produced and the earlier gear, and its undo adds `undo_of`; a restore drops these two markers, so a restored history can never be undone), `from_export`, and sharing: `post_published`, `post_audience`, `post_unpublished`. Restore copies sharing entries as history only and never republishes a post |
| `baseline` | Prior jump count: `prior_jumps` before `before_on`, `source`; or `null` |
| `baseline_events` | `declared`, `corrected` (from/to), `removed`, `from_export` |
| `saved_listings` | Listing ID and the title as saved (200) |
| `plans` | Title, dates, note, at most one link to a listing, venue or private place (100) |
| `licence` | The licence you stated for currency guidance: `student`, `a`, `b`, `c`, `d`, or `null`. Optional (files without it restore with none). A restore sets it only when the account has none set; it does not make the records non-empty |
| `exit_weight` | Your usual exit weight for wing loading: `grams` (30,000–250,000) and the `unit` you entered it in (`kg` or `lb`), or `null`. Optional, like `licence`: files without it restore with none, a restore sets it only when the account has none set, and it does not make the records non-empty |

## `references`

Snapshots of the public records the file points to: `venues` (`id`, `name`, `country`) and `listings` (`id`, `title`). They are used only when a reference is no longer public at restore time.

## Not included

Password or hash, sessions, email address, roles, follow approvals, publications, other people's records, and the directory itself. Suggestions/reports sent to reviewers are not personal records and are not exported.

## Restore

Profile → Your data → Restore. The raw file is limited to 8 MiB and the normalised content to 4 MiB.

1. **Check** validates the whole file without writing. It shows the counts, what will become private or lose a link, and whether this account can take it.
2. **Restore** needs a confirmed email and the account password. It is limited to three attempts per account per day.
3. **The same file again.** The SHA-256 of the exact file is recorded per account. Restoring that same file again answers "already restored" and writes nothing, even after later edits or deletions. A reformatted copy is a different file.
4. **Empty records only.** The account must hold no places, gear, jumps, prior jump count, saved listings or plans. Otherwise nothing is written and existing records stay as they are. There is no merge.
5. **One transaction.** Everything is written under new IDs. Restored jumps and the baseline are marked `restored`, and history gains a `from_export` entry. The managed records are counted again before commit, so a save that lands at the same moment rolls the whole restore back.
6. **References no longer public:**
   - A dropzone a jump or plan used becomes a private place with the snapshot's name and country.
   - A private place's link to such a dropzone is dropped.
   - A plan's listing link is dropped; the plan stays.
   - A saved listing is not restored, and its title is listed in the check.

Errors:

| Status | Code | Meaning |
| --- | --- | --- |
| 400 | `archive_malformed` | Not JSON, or not an object |
| 400 | `archive_version_unsupported` | Wrong format or version |
| 413 | `archive_too_large` | Over the size limits above |
| 422 | `archive_invalid` | Fails a check. `problem` gives the position and rule, e.g. `jumps[3].deployment_above_exit`, and never the content |
| 422 | `password_confirmation_failed` | The password is wrong or missing |
| 409 | `records_not_empty` | The account already holds records |
| 429 | `too_many_attempts` | Over the export, check or restore limit |
