# European dropzone inventory (research, development data)

Started 2026-11-14 at the owner's request: collect every active skydiving dropzone in Europe,
with coordinates so the app can show them on a map. Like the rest of `../`, this is
**development data only** until the owner reviews it. Nothing here is published by itself.

One file per country: `<CC>.json` (ISO 3166-1 alpha-2, upper case), in the format below.
`_coverage.md` in this folder records, per country, which sources were checked and what is
still open.

## What counts as a dropzone

A place where skydiving jumps (sport, tandem or student) are made regularly from an aircraft,
run by a club, school or company: a "drop zone", "centre école", "Sprungplatz",
"centro de paracaidismo", "zona di lancio" and so on. It is an airfield or landing area, not
an office.

Include:
- seasonal and weekend-only dropzones;
- military or club dropzones that civilians can use.

Exclude:
- indoor wind tunnels;
- BASE sites;
- paragliding sites;
- tandem resellers with no aircraft of their own at that place. Record the place they fly
  from instead.

Not covered (owner decision 2026-11-14): Russia, Belarus, and places in occupied
territory.

When a place may be closed, record it with `"status": "closed"` or `"uncertain"` and say why.
Do not leave it out silently.

## Record format

```json
{
  "country": "FR",
  "researched_on": "2026-11-14",
  "researcher": "claude | codex",
  "dropzones": [
    {
      "key": "fr-la-ferte-gaucher",
      "name": "Aérodrome de La Ferté-Gaucher",
      "aliases": ["Paris Skydive", "LFFG"],
      "country": "FR",
      "locality": "La Ferté-Gaucher, Seine-et-Marne",
      "latitude": 48.7547,
      "longitude": 3.2767,
      "coordinates_source": "https://… (where the coordinates came from: OSM, AIP/airport page, operator page)",
      "icao": "LFFG",
      "operators": [
        {"name": "Paris Skydive", "website": "https://…", "facebook": "https://www.facebook.com/…"}
      ],
      "aircraft": "Pilatus PC-6 (as stated by the source, optional)",
      "season": "all year | April–October | weekends … (as stated, optional)",
      "status": "active | seasonal | uncertain | closed",
      "status_evidence": "Facebook post 2026-10-30 shows jumps; or federation list 2026",
      "sources": [
        {"url": "https://…", "checked_on": "2026-11-14", "what": "federation list of centres"}
      ],
      "note": "optional, short, factual"
    }
  ]
}
```

Rules:
- `key`: `<cc>-<slugified place>`, lower case, ASCII, unique. Use the place, not the operator.
  Two operators at one airfield are one dropzone with two `operators`.
- `latitude` / `longitude`: decimal degrees, WGS84, 4–6 decimals, the landing area or
  airfield. Never guess. If no source gives the position, put `null` and say so in `note`.
  Check that the point falls in the stated country and town.
- `status` needs `status_evidence`. Evidence counts if it is recent, from 2025 or later: a
  dated post, a published season calendar, or a federation list for the current year.
- Every record needs at least one source URL that you actually opened. Prefer, in order:
  - national federation or aero-club lists (e.g. BPA, FFP, DFV, KNVvL, the national aero club);
  - official operator sites;
  - OpenStreetMap, the national AIP or airport pages for coordinates;
  - Facebook or Instagram pages for activity;
  - aggregators (dropzone.com, dropzones.eu, Wikipedia lists) as leads to confirm.
- Facts only, in your own words. Do not copy descriptions, photos or logos. Names, places,
  coordinates, websites, aircraft and seasons are facts.
- Do not sign in anywhere, accept terms, or contact anyone. Public pages only. If Facebook
  shows a login wall, use what is visible, or search results, and say so.
- Prefer OpenStreetMap data (e.g. Overpass `aeroway=aerodrome`, `sport=parachuting`) or official
  pages for coordinates. Keep request rates low. Send no personal data or email address in
  request headers.
- Write valid JSON (UTF-8). Validate with `python3 -m json.tool <file>` before finishing.
