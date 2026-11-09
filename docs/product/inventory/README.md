# Initial inventory: candidate records (#162)

**Owner decision 2026-11-09: these records are development data only.** They are loaded into
local databases for testing (`scripts/dev.sh seed`, from `dev-listings.json`) and are not
published in production. The loader refuses to run unless `ENVIRONMENT=local`. Facebook pages
may be used as sources.

Owner decision 2026-11-09 (`../beta-decisions.md`): start with Greece, Bulgaria, Spain and
Portugal; events, boogies, camps and courses. The assistant drafted candidate records from
public pages on 2026-11-09; the owner checks each against its source and enters it through
`/review`. **Nothing in these sheets is reviewed or published.**

| Country | Dropzones | Organizers | Listings | Dated listings | Leads |
| --- | --- | --- | --- | --- | --- |
| [Greece](GR.md) | 3 | 4 | 4 | 0 | 4 |
| [Bulgaria](BG.md) | 3 | 5 | 7 | 0 | 10 |
| [Spain](ES.md) | 5 | 5 | 18 | 13 | 13 |
| [Portugal](PT.md) | 3 | 4 | 11 | 0 | 9 |

Counts are candidates found, not coverage: several dropzones are known only from
aggregators and are listed as leads.

## What the research found

- **Dated opportunities exist only in Spain.** In Greece, Bulgaria and Portugal no operator
  page showed a dated event, boogie, camp or course between 2026-11-09 and the end of 2027.
  Their listings are ongoing courses (AFF, static line, packing, canopy) with no dates.
- **Undated courses cannot be published by the current code.** A published listing needs
  start and end dates (`DATED_STATUSES` in `backend/app/skydiver/opportunities/policy.py`),
  and the beta scope is dated listings only (decided 2026-11-09, `../beta-decisions.md`): the
  "continuing offers" in the maintenance routine are the deferred school/coach profiles. The
  dropzones and organizers can be published; these courses stay unpublished until dated.
- **Registration links.** Several Spanish listings register by email only (the event page
  names the address). The editor needs a link; the event page itself is the practical route.
- **Reuse terms.** Most operators that publish terms reserve all rights or forbid reproduction
  (Empuriabrava, Skydive Madrid, the Greek and Bulgarian operators). The Greek sites also ask
  for written consent before linking. Listings record facts with original wording and link to
  the source; whether linking without consent is acceptable is the owner's call.
- **No national federation calendars** were found for Greece, Bulgaria or Portugal; Spain's
  RFAE calendar showed no parachuting events.
- **Possible duplicates/relations to confirm:** Skydive Bulgaria and Skydive Sofia share a
  company number; Skydive Algarve and Skydive Seven may use the same airfield.
- **Greece, from the owner (2026-11-09):** Skydive Athens, Megara, Crete and Mesologi are
  one organizer; Chortero is shared with Hellenic Skydivers (Facebook only; also runs events
  at Thiva/Perneri); Skydive Attica also uses Megara. Recorded in `GR.md`.

## Dev data (`dev-listings.json`)

The sheets as data for `python -m app.skydiver.devdata load`, with the owner's Greek organizer
relations applied. Where a source names no registration link (email only), the source page is
used. Records go through the normal rules: a local load on 2026-11-09 created 14 dropzones,
18 organizers and 40 listings; the 13 with complete dates were published and the 27 undated
ones wait in the review queue (`schedule_required`). 22 tags that are training methods, not
disciplines (AFF, static line, tandem, packing...), are left out.

## Effort

Research by four parallel assistant runs, about 107 page fetches and 57 searches in total.
One dated record (Empuriabrava's calendar) was re-checked independently and matched. The
owner's checking and entry time is not yet recorded; add it here per country when done.
