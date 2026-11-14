# Dropzone directory and jump attribution

Status: documented product direction from discovery. The listing, provisional-place and merge foundation is implemented by #148 (see [Implemented in #148](#implemented-in-148)); maintenance tools, suggestions/corrections and the manual claim policy are implemented by #151 (see [discovery board](discovery-board.md#implemented-in-151)); claims as a feature, operator participation and jump linking (#153) are not. Skydivers must be able to associate jumps with a dropzone before that operator registers or adopts the application.

## Directory presence versus participation

A dropzone needs a stable directory identity to link related records. This does not require an operator account, endorsement, or operational integration. Treat these as distinct capabilities rather than one universal verification status:

| State / capability | Meaning |
| --- | --- |
| Listed | Public/source-backed name and location; selectable in personal logs and plans |
| Claimed | A representative has demonstrated authority to manage permitted venue information |
| Operationally participating | Authorized staff use selected booking, check-in, or manifest functions |

Provider qualification, listing management authority, operational participation, and verification of individual jumps remain separate. A claimed venue need not adopt every operational feature.

## Personal jump workflow

1. Search by dropzone name, location, or known alias.
2. Select an existing directory entry and log the actual jump, equipment, notes, and optional attachments.
3. If missing, suggest a name/location or keep a provisional location so logging can finish immediately. Do not require an operator invitation to complete a personal entry.
4. Review suggested venues and possible duplicates before publishing a canonical public entry.
5. Link the personal entry to the stable venue ID when resolved, preserving its original attribution and correction history.

A dropzone reference means “the jumper recorded this activity here.” It does not mean the dropzone confirmed the jump. Private logbooks and media do not become public by appearing under a directory location.

## Connected venue page

A venue page can connect sourced public information, related events, independently identified coaches/schools, forecasts, and the current user's own visit/jump history. Label each relationship's source; listing an activity at a venue does not establish endorsement by that venue.

Public visitor counts, user identities, activity feeds, and jump totals are not automatically authorized by having private linked records. Public aggregate statistics, if later proposed, need an explicit privacy and provenance policy and must not be labeled official operator totals.

The [social proposal](social-activity.md) allows recent shared activity on venue pages only for the publisher's chosen audience. This is not a live people-on-site board: activity date, publication date, and future intentions remain distinct. Following never reveals the full private DZ-linked history.

## Later operator claim

An authorized representative can request management of an existing entry through a defined authority-review process. Reuse the venue identity rather than creating a disconnected duplicate. A directory claim grants scoped management permissions, not unrestricted access to linked personal records.

Historical entries retain their original self-reported/imported/confirmed sources. Claiming the venue does not retroactively verify them. Any later review of a specific jump requires permission and a separate attributable confirmation. Operational workspaces remain isolated from other operators.

## Identity and corrections

Retain aliases, source references, and change history. Distinguish a venue's rename, an operator change, a relocation, and a duplicate directory entry; these are not automatically equivalent. Support closed/historical venues so past jumps remain meaningful.

Duplicate merges must preserve activity references, saved plans, event links, and attribution without losing records or granting new permissions. Do not merge distinct locations solely because their names match. Provide a correction/dispute route for inaccurate location data or competing management claims.

## Acceptance examples

- A user logs a jump at an unclaimed dropzone without the operator registering.
- A missing venue can remain provisional while the rest of the jump is saved.
- A later claim retains the same location identity and creates no new access to private logs.
- Merging duplicate entries preserves every linked jump without increasing a user's jump count.
- An operator can publish an event after a claim without adopting manifest software or confirming historical jumps.
- An older jump still identifies the historical venue when it closes or changes operators.

Open details: initial directory sources and reuse permissions, minimum location fields, moderation, authority-review evidence, merge/relocation rules, and any public statistics policy.

## Implemented in #148

| Area | Behaviour |
| --- | --- |
| Venue identity | Random UUID that never changes. Name, ISO 3166-1 country, optional locality and coordinates, `source_url` + `checked_on` (required unless draft), optional source note |
| Status | `draft` (reviewer-only, not public) → `listed` ⇄ `closed` (historical, still public and selectable). A public venue cannot return to draft; it is closed instead. `merged` is set only by a merge |
| Rename / relocation | Same venue; the previous name becomes a searchable `former` alias. Location changes are recorded as `relocated`, separately from renames. Every change is an event with the reviewer's account |
| Duplicates | Only an explicit reviewer merge. The source becomes `merged` → target; its name and aliases become `merged` aliases of the target. Old IDs keep resolving (the web redirects `/dz/{old}` with 301). Stored private references are not rewritten. Equal names are never merged automatically; a public venue cannot merge into a draft |
| Search | Name, alias and former names; case-, accent- and punctuation-insensitive; optional country; keyset pages of 20 (max 50). Public results are listed and closed venues only |
| Provisional places | Owner-only name + country, saved immediately (confirmed email required, like all private writes); optional link to a public venue; at most 200 per person (design default). Never public, never a suggestion, never visible on venue pages |
| Authority | Maintenance requires the server-granted `reviewer` role (`python -m app.skydiver.access.grant reviewer <email>`). Listings have no operator, claim, endorsement or verification fields, and public venue responses contain no counts or linked private records |

## Map view

Requested by the owner 2026-11-14: `/dz?view=map` shows the same search as the list on a map. No paid
service and no new infrastructure.

| Area | Behaviour |
| --- | --- |
| Data | `GET /api/skydiver/v1/venue-points` (same `q`/`country` filters and public statuses as `/venues`, merged and draft venues excluded, venues without coordinates left out): id, name, locality, country, lat, lon, closed. Pages of up to 1,000; the web shows the first page and says when there are more |
| Map | Leaflet and Leaflet.markercluster (npm), OpenStreetMap standard tiles with the "© OpenStreetMap contributors" attribution. Closed dropzones have their own marker and say "Closed" in the popup; popups link to `/dz/{id}` |
| Privacy | Nothing third-party loads before the visitor presses "Show map"; the choice is kept in `sessionStorage` for that tab. Tiles then send the visitor's IP address and the site's origin (`Referrer-Policy: strict-origin` on tiles only, which the tile usage policy requires) to `tile.openstreetmap.org`, the only image host the CSP allows besides the site. The privacy page says so |
| Without JavaScript | The Map view says the map needs JavaScript and links to the list, which stays complete |
| Accessibility | The list is the equivalent and the map says so. The map region is labelled and focusable (arrow keys pan, +/- zoom); markers and clusters are named buttons; Enter on a marker opens its popup and moves focus to its link, and closing returns focus to the marker |
| Detail page | Coordinates as text and a plain "Open in OpenStreetMap" link; no map is embedded |

The tile servers are run by volunteers under a [usage policy](https://operations.osmfoundation.org/policies/tiles/) meant for moderate use. If the map ever needs more than that, the policy asks for another tile provider or self-hosting; that would be a new decision.

No venue data is shipped. Listings must come from reviewed sources with reuse permission (#151/#162); the beta directory starts empty.

Related: [connected product model](product-model.md), [feature catalog](feature-catalog.md), and [discovery board](discovery-board.md).
