# Coverage: Italy and the northern Adriatic (IT, MT, SM, SI, HR)

Researched 2026-11-14 by claude. Development data only; see `README.md`.

Coordinates were taken from OpenStreetMap airfield geometry (Overpass, `aeroway=aerodrome|airstrip`
and `sport=parachuting|skydiving` in the five countries). Where OSM had no matching airfield, they
came from the OurAirports dataset (`davidmegginson.github.io/ourairports-data/airports.csv`). That was
needed for three records: IT Caltagirone/Massarotti, SI Šentvid pri Stični and HR Poreč-Škagacer.
No coordinates were guessed. One record has `null` coordinates (IT Cecina).

## Italy (IT): 37 records. 32 active, 5 uncertain

Sources checked:
- ENAC "Elenco scuole di paracadutismo 2026" (xlsx linked from enac.gov.it) lists 33 authorised schools.
  This is the primary list and the status evidence for every `active` IT record.
- OSM Overpass found 15 `sport=parachuting/skydiving` objects and about 785 aerodromes in the five countries.
- OurAirports CSV, keyword search ("skydive", operator names).
- Directories, used as leads only: skydivingsource.com (23 Italian DZs), flight-1.com, freedome.it,
  yumping.com, dropzonesandtunnels.com.
- Operator sites: Primolancio, Aero Club Albatros, Sunflyers (Roma, Puglia, Napoli), Skydive Iseo,
  Skydive Milano, Crazy Fly, Skydive Venice, Skydive Sunrise, Maremma Fly, Skydive Calabria, Skydive Garz,
  Ferrara and others.
- Local news: UmbriaOn (Terni).

How ENAC schools map to dropzones:
- The 32 non-military ENAC schools give 32 `active` records, one per school's airfield. Novi Ligure has
  two operators: Paraclub (I-061) and Albatros (I-046). Albatros also has its own Acqui Terme record.
- Monte Compatri (Aviosuperficie Fly Roma) has four operators.
- Excluded: **I-019 Carabinieri, Livorno**. It is a military school and there is no sign civilians can use it.
- The Sunflyers school (I-056, registered at Catania) is recorded at Caltagirone/Massarotti. Its other
  sites, Melendugno (Puglia) and Lavello (Basilicata), are recorded as `uncertain`.

Records not on the ENAC list, all `uncertain`:
- Costa Volpino (Skydive Iseo / Skydive Milano events)
- Terni (TheZoo closed 2023; ASD Terni restarted Nov 2023; nothing found for 2025 or later)
- Melendugno and Lavello (Sunflyers)
- Cecina (Skydive Toscana; aggregator listing only; no airfield tied to it, so coordinates are `null`)

Still open:
- Caltagirone: the coordinates come from OurAirports "Aviosuperficie Massarotti". The link between that
  airstrip and Sunflyers' "Contrada Caudarella" address rests on a directory entry. Check it on the ground
  or in the ENAC aviosuperfici register.
- Acqui Terme vs Novi Ligure: Albatros's January 2026 terms name Novi Ligure as the venue. Acqui Terme may
  no longer see jumps.
- Melendugno: directories say "Melpignano", while the operator says Melendugno. The match to the OSM
  airstrip is by municipality only.
- Not followed up:
  - Palermo-Boccadifalco "Sicilia Boogie" (Skybrothers Palermo; an old event)
  - Rimini groups (reported to jump at Fano)
  - Military drop zones (Folgore at Altopascio, US 173rd "Juliet DZ" at Pordenone; excluded as military)
- Facebook and Instagram were not checked post by post. Status relies on the ENAC 2026 list.

## San Marino (SM): 0 records

Checked web searches (Italian and English) and OSM/OurAirports for Torraccia airfield (LIKD).
No parachuting operator was found. An old Avionews item mentions parachute launches among planned
airfield activities, without operator or date. Still open: the Aeroclub San Marino site was not opened.

## Malta (MT): 0 records

Checked web and Tavily searches ("skydive Malta", "parachuting club Malta", Ta' Qali, Luqa) and
OSM/OurAirports for MT. Only aggregator pages with no named operator turned up. No dropzone was found.
Still open: Malta may see occasional display jumps (military or air show); none were confirmed.

## Slovenia (SI): 8 records. 1 active, 7 uncertain

Sources checked:
- OSM: one parachuting pitch, at Lesce.
- OurAirports.
- Portorož airport tandem page.
- Prostipad location pages (a mirror domain; the main prostipad.com did not respond).
- Skydive Croatia location page.
- slovenia.info (via search).
- Ptuj municipality notice.
- Svet24/Vestnik news (Rakičan).
- flight-1.com (Skydive Maribor).
- Letalska zveza Slovenije (LZS): only board minutes turned up. A list of clubs was not found.

Active: Portorož (Prostipad 2025 plan; the airport says all year by arrangement).

Uncertain:
- Šentvid pri Stični
- Maribor (LCM parachuting section)
- Lesce: conflicting. A reseller says tandems land there; Prostipad says it has been closed to tandems since 2015.
- Bovec
- Postojna
- Ptuj: tandems at the open day on 6 Sep 2025 only.
- Murska Sobota/Rakičan: Red Bull team training in 2025; not shown to be public.

Still open: LZS parachuting club list; Facebook pages of LCM and Prostipad for 2026 dates; Slovenj Gradec
(named by slovenia.info; not recorded, no operator found).

## Croatia (HR): 11 records. 2 active, 4 seasonal, 5 uncertain

Sources checked:
- Hrvatski zrakoplovni savez member list (caf.hr), with about 10 parachute clubs.
- Skydive Croatia site, with dated 2026 season news.
- FLYClub CRO / Skydive Poreč, with a 2026 boogie calendar.
- padobranstvo.com: 20 May 2025 tandem-locations article and 2025 competition calendar.
- ADV Adventure Driven Vacations (Zadar and Otočac).
- Aeroklub Sinj news.
- Skydive Vrsar promo page.
- Krila Kvarnera club site.
- OSM and OurAirports.

Records by status:
- Active: Zagreb-Lučko and Poreč-Škagacer.
- Seasonal: Varaždin, Mali Lošinj (boogies), Sinj, Zadar (take-off at LDZD; beach landing at Rtina,
  position not published).
- Uncertain: Čakovec, Vrsar, Otočac, Grobnik (Krila Kvarnera), Osijek-Čepin.

Still open:
- Clubs with no jump site located:
  - AirIK (youth club; no own DZ)
  - Homo Volans, Maksimir, Croatia (Zagreb; probably Lučko)
  - Paraštrumf
  - Aeroklub Slobodan Pad (mobile tandems "all over Croatia")
- Grobnik and Osijek: the club-to-airfield link is assumed from each club's home town. This is stated in the records.
- No Facebook checks were made for Vrsar or Čakovec.
- "Hrvatski zrakoplovni savez" parachuting commission reports (2022 PDF seen in search) were not opened.

## Check

Skeptical check, 2026-11-14 (claude). I tried to prove records wrong, starting with the weakest:
uncertain status, a single source, or coordinates not from OSM.

### What was checked

**Coordinates (all 57 records).** For every record whose `coordinates_source` is an OSM element, the
geometry was fetched from the OSM API (`api.openstreetmap.org/api/0.6`). Overpass was not reachable.
- Every stored point falls inside its element's bounding box, within 0.6 km of the centroid.
- Every stored point is at the named airfield, and every ICAO code matches the OSM tag.
- No point is in the sea, in the wrong town or in the wrong country.

The three OurAirports-sourced points were moved to OSM nodes that Nominatim found:

| Record | OSM node | Distance moved |
|---|---|---|
| IT Caltagirone/Massarotti | node 11115877986 | about 0.1 km |
| SI Šentvid pri Stični | node 1040115393 | about 0.03 km |
| HR Poreč-Škagacer | node 12288191925 | about 0.27 km |

**Duplicates.** None found. Albatros appears under both Acqui Terme and Novi Ligure, but these are
two different airfields. The two Fly Zone operators (Loreto and Fermo) are also at different airfields.

**ENAC 2026 list.** I re-downloaded the xlsx. Its localities match the 32 active IT records.

### Corrections

IT:
- `it-acqui-terme`: active → **uncertain**.
  - AcquiNews (3 Jan 2026) reports that the lease was not renewed. Parachuting moves to Novi Ligure
    from June 2026.
  - Albatros's own page now names Novi Ligure for parachuting.
  - Most likely closed for skydiving, but no post-June evidence either way, so it stays uncertain.
- `it-terni`: uncertain → **active**.
  - The airstrip's 2026 *Carta dei servizi* (Terni Reti, March 2026) names ASD "VoliaMO" as a
    parachuting school based there.
  - The Comune di Terni (31 Aug 2026) announced tandem jumps at the Festival del Cielo on 5 Sep 2026.
  - It is not a separate ENAC school.
- `it-cecina`: null coordinates → **OSM node 3147491515** ("Porta della Maremma", LIQG).
  - ENAC FACTOR 06/2019 ties ASD Skydive Kalifornia to this airstrip (jump-flight accident, 2016).
  - Status stays uncertain: no 2025+ activity found.
- `it-caltagirone-massarotti`: the operator's own page "Aviosuperficie Massarotti – Caltagirone"
  confirms the link. Coordinates now come from OSM.
- `it-melendugno`: the operator's Contrada Giammarino (SP148) is about 0.7 km from the airstrip,
  which supports the match. Still uncertain: the newest visible Instagram post is from 2023.

SI:
- `si-bovec`: uncertain → **seasonal**.
  - Added operator Skydive Bovec (Rupa 17, at the airfield edge).
  - Evidence: a 2025 season-calendar news item dated 7 Mar 2025, and a "Season 2026" Facebook post
    with dates from 7 May. The post was seen in search results only.
- `si-sentvid-pri-sticni`: coordinates now come from OSM. The main prostipad.si site responds now.
  Its tandem page says the 2026 season has ended and the next starts in April 2027. It lists
  Portorož, Šentvid, Postojna, Bovec and Lesce. Šentvid and Postojna stay uncertain: they are
  by-arrangement locations with no dated jump.
- `si-lesce`: still uncertain. Prostipad's own Lesce page (main domain) still says it has been closed
  to tandems since 2015, even though the tandem page lists Lesce.
- **Added `si-metlika`** (Vzletišče Prilozje – Metlika, OSM node 1042066789): seasonal.
  - Croatian Aeroklub Tandem (tandem.hr) lists seven 2026 tandem weekends, April–June.
  - The airfield is matched as the only aerodrome at Metlika.

HR:
- `hr-vrsar`: uncertain → **seasonal**.
  - Slobodan Pad lists a tandem event at Aerodrom Vrsar on 13–14 Jun 2026 (Cessna 182 9A-DTD).
  - Skydive Adria uses the same aircraft at Vrsar.
- `hr-porec-skagacer`: coordinates now come from OSM.
- `hr-cakovec`: still uncertain. Added Skydive Croatia and Slobodan Pad pages, which both name the
  Pribislavec airfield but give no dated 2025+ jump.

### Revised counts

| Country | Records | Active | Seasonal | Uncertain | Null coordinates |
|---|---|---|---|---|---|
| IT | 37 | 32 | 0 | 5 | 0 |
| SI | 9 | 1 | 2 | 6 | 0 |
| HR | 11 | 2 | 5 | 4 | 0 |
| MT | 0 | | | | |
| SM | 0 | | | | |

### Still doubtful

- IT Acqui Terme: probably closed since June 2026.
- IT Terni: no regular jump days seen.
- IT Cecina: last dated jump was in 2016.
- IT Melendugno and Lavello: no 2025+ evidence.
- IT Costa Volpino: the operator is live, but no dated post was seen.
- SI Lesce: the operator's own pages conflict.
- SI Postojna, Šentvid, Maribor, Ptuj and Rakičan: no dated regular jumps.
- HR Grobnik, Osijek, Otočac and Čakovec: no dated 2025+ jumps.
- Not followed up:
  - Tandem Experti "Medulin" (gallery caption only; no airfield named)
  - Padobranski klub Croatia (no jump site on its page)
- MT: a deal.com.mt "Fly Zone" tandem offer appears to be for jumps in Italy. No Maltese dropzone
  was found.


## Codex cross-check

Date: 2026-11-14 (environment date). Scope: Italy only; the earlier SI/HR/MT/SM findings are unchanged. Read the README and prior coverage before reviewing all five uncertain records and the ENAC-list-based active records. Independently opened and parsed the [ENAC 2026 workbook](https://www.enac.gov.it/app/uploads/2024/09/ELENCO-SCUOLE-PARACADUTISMO-2026.xlsx), operator sites, calendars and local-language searches. No sign-in, terms acceptance, contact, Overpass requests or commits.

### Changes and counts

- Upgraded to active/seasonal: **0**; downgraded to uncertain: **0**; closed: **1**; added: **0**; existing coordinate pairs corrected: **0**.
- **Acqui Terme: uncertain → closed.** [AcquiNews, 24 June 2026](https://acquinews.ilpiccolo.net/2026/06/24/acqui-una-croce-bianca-sulla-pista-aviosuperficie-chiusa-resta-la-speranza/) reports the airstrip's closure and quotes its operator confirming that jumps and aircraft have moved to Novi Ligure. [Albatros's March 2026 announcement](https://aeroclub-albatros.it/category/news-eventi/) independently confirms the move. The existing Novi Ligure record already consolidates Albatros and Paraclub.
- Added stronger dated activity evidence to Belluno, Cumiana, Arezzo, Nettuno and Fano from the [AeCI sporting calendar](https://www.webaeci.it/cgi-bin/agp.bat?service=casp_list); Serdiana from the operator-linked public calendar; Siracusa and Paestum from operator event calendars; Fermo from its November 2026 canopy course; Orbetello from a dated 2025 customer account; Molinella from October 2026 reporting; Scarlino from a July 2026 tandem report. These records retain active status.

| Country | Active | Seasonal | Uncertain | Closed | Total | Missing coordinates |
|---|---:|---:|---:|---:|---:|---:|
| IT | 32 | 0 | 4 | 1 | 37 | 0 |

### Directory-based activity review

The ENAC list is an aviation-authority authorization list, not a generic club directory. Its 2026 school/locality entries were independently verified and retained as qualifying evidence under the README's current-list rule unless a specific contradiction was established. An authorization is not proof of daily operation; copyright years and undated booking forms were not converted into dated jump reports.

For Verona, Vercelli, Cremona, Reggio Emilia, Thiene, Loreto, Ferrara, San Stino, Udine, Caltagirone, Sibari, Garzigliana, Alessandria, Monte Compatri and the remaining undated operator pages, the cross-check did not establish a separate field-specific dated schedule beyond the authority evidence. Lucca and San Vincenzo also retain the checked 2026 authority evidence; search-only articles/offers were not added as opened activity sources. No newly confirmed closure was established at those fields. Casale's current operator still advertises booking and a weekly opening pattern; January 2026 enforcement news is a lead to clarify rather than proof of permanent dropzone closure, so the record retains the 2026 authority basis. The opened operator and authority URLs are recorded in IT.json.

### Uncertain records and gaps

- `it-costa-volpino`: Operator pages remain live but undated; no 2025–2026 site-specific operating calendar or jump report was established.
- `it-melendugno`: Operator offers remain undated, while an AIRAC digest reports removal of the Melendugno parachuting area effective 20 February 2025; continued regular jumping is unconfirmed.
- `it-lavello`: The operator event page was reopened but yielded no dated 2025–2026 Lavello jumping; copyright dates do not establish activity.
- `it-cecina`: Historical ENAC accident evidence identifies the site, but no reliable 2025–2026 activity or definitive operator closure notice was established.

Melendugno's [secondary AIRAC digest](https://aeronauticalinformation.it/index.php/2024/10/02/aeroporti-di-belluno-e-lecce-lepore/) says its parachuting area was deleted effective 20 February 2025. This strengthens the uncertainty but does not independently prove the operator permanently closed. Cecina has conflicting reseller offers and closure comments; no authoritative recent outcome was established. Sunflyers' event pages for Lavello and Caltagirone yielded no dated events in the retrieved text. Primolancio's calendar returned HTTP 403; the homepage was readable. Public operator pages were preferred over social search snippets; no login-gated social content was used.

Completeness searches covered Italian-language 2025/2026 parachuting, calendars, schools and the earlier Palermo/Sicilia Boogie lead. Generated-2026 printouts of old event articles were not treated as 2026 events. No missing regular civilian site was confirmed; Palermo's actual continuing field/operator combination remains open.

### Coordinate audit

Ten existing points were compared against individually opened OurAirports pages: LIPN Verona, LIDB Belluno, LILM Casale, LILI Vercelli, LILR Cremona, LIDR Ravenna, LIDE Reggio Emilia, LIQL Lucca, LIQB Arezzo and LIDH Thiene. All correspond to the stated airport, with differences of about 0.03–0.19 km from the airport reference points. Original OSM geometry points were retained; all ten audit-source URLs were added to the records. There were no missing IT coordinates and no coordinate corrections.

Validation: IT.json passed `python3 -m json.tool` and structural checks for source presence, unique keys, allowed status values and paired coordinates. No commit was made.
