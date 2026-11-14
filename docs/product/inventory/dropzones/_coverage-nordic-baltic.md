# Nordic and Baltic dropzone research coverage

Researcher: codex. Research date: 2026-11-14 (environment date). Development inventory only; unresolved leads are explicit below.

## Initial-pass counts

| Country | Active | Seasonal | Uncertain | Closed | Total | Without coordinates |
|---|---:|---:|---:|---:|---:|---:|
| NO | 5 | 3 | 12 | 0 | 20 | 5 |
| SE | 1 | 2 | 17 | 1 | 21 | 7 |
| FI | 12 | 0 | 3 | 0 | 15 | 2 |
| DK | 5 | 2 | 11 | 1 | 19 | 4 |
| IS | 0 | 1 | 1 | 0 | 2 | 0 |
| EE | 1 | 1 | 2 | 0 | 4 | 1 |
| LV | 0 | 2 | 1 | 0 | 3 | 2 |
| LT | 6 | 0 | 3 | 0 | 9 | 1 |
| **Total** | **30** | **11** | **50** | **2** | **93** | **22** |

The sections through LT below preserve the initial-pass findings. The **Follow-up** section supersedes their status counts, coordinate gaps and resolved leads.

## Method and limitations

Federation lists were reconciled with physical operating fields, operator sites, local-language searches and country directory lists. Dropzone.com was attempted but did not yield usable country inventories; DropzoneFinder was used for leads, not its generic promotional claims or estimated national totals. Public social links/search snippets were considered where available; no login-gated activity was treated as verified. No accounts, messages, terms acceptance or contact requests were used.

One successful Overpass scan covered all eight countries using country areas and `nwr["sport"="parachuting"]`, with `out center tags`. Broader aerodrome/club-name queries timed out or returned server errors; they do not establish absence of sites. OSM object links in the JSON refer to objects actually returned by that scan. Shop/rigger-only points were excluded. OSM polygon centres and airport-side club premises are distinguished from exact touchdown locations in notes. Wikipedia and OurAirports facility pages supplied further coordinates, using only successfully opened pages; OurAirports TLS validation failed locally and those public pages were fetched with certificate verification disabled. No coordinate was inferred from a town centroid or a search snippet.

Undated live websites and undated federation lists do not alone establish recent operation under the README rule, so many plausible operating fields remain uncertain. Active does not imply year-round jumping. Seasonal means a dated recurring season/event is supported. Closed refers to the parachuting operation, not necessarily the airfield. Official permits support the Lithuanian active entries; actual daily schedules remain unverified.

All eight JSON files passed `python3 -m json.tool`. Additional structural checks covered required identifiers, unique ASCII keys, country matching, allowed statuses, paired null coordinates, coordinate ranges and source presence. Completeness is not independently guaranteed; the country-specific open leads below are the remaining research gaps.

## NO

Sources checked: [NLF club directory](https://klubber.nlf.no/klubber/Fallskjerm), [DropzoneFinder Norway](https://dropzonefinder.com/dropzones/norway), operator sites listed in NO.json, [2026 national championships](https://www.nmfallskjerm.no/), OSM parachuting objects, Wikipedia airport pages and OurAirports airport facility pages.

The NLF list includes organizations without a distinct operating field. Bergen's Stend and Titlestad landing fields were first separate records; on 2026-11-14 they were merged into `no-stend` (one club, two seasonal landing areas 1.8 km apart). Flesland is their departure airport. Stavanger's Sviland landing area is represented instead of Sola. Troms has Bardufoss and Elvenes bases plus an annual Leknes lead. Duplicate Føniks, Tønsberg and Troms directory entries were merged.

Open leads: [Gudvangen / Skydive Home](https://skydivehome.com) advertises 2026 helicopter experiences across Norway, but a regular fixed landing area was not established; do not map its office. Tandemhopp Fallskjermsenter's fixed site is unresolved and its website failed certificate validation. Lofoten & Vesterålens club's federation address does not establish a separate dropzone. Krigsskolen and Veteranenes need evidence of a separate civilian-access field; Voss educational/club entities may share Bømoen. Old NTNU Værnes and Røros sites are retained as uncertain; its unnamed Trondheim city field remains unresolved. Historical club-name search leads Andøya, Fjordane/Førde, Lista, Rana, Sparbu and Trondarnes need field-level evidence before adding records. Kjevik's operator website was unreachable. Several existing operators had undated pages, so uncertainty does not mean proven inactivity.

Records without coordinates: `no-stend`, `no-titlestad`, `no-kjevik`, `no-bjorli`, `no-sviland`.

Record-level opened URLs, check dates and evidence are retained in `NO.json`; the sources above are the main reconciliation sources.

## SE

Sources checked: [SFF club list](https://sff.se/borja-hoppa-fallskarm/fallskarmsklubbar-i-sverige/), [SFF homepage](https://sff.se/), [DropzoneFinder Sweden](https://dropzonefinder.com/dropzones/sweden), linked operator websites, [Cirrus course calendar](https://www.hoppafallskarm.se/kurs/), [Öland tourism Borglanda page](https://www.oland.se/fallskarmshoppning-over-borgholm), [SVT closure report](https://www.svt.se/nyheter/lokalt/orebro/fallskarmsklubben-i-orebro-avvecklas-efter-flygolyckan), OSM and airport pages.

The SFF page says 17 active clubs but exposes 14 club links; that discrepancy was not silently converted into a completeness claim. Its undated list establishes operators and locations, not 2026 field activity. Cirrus's published next-season calendar supports Vårgårda and seasonal Näsinge. Smålands' Feringe base, its Halmstad cooperation and its Borglanda visiting week are distinct locations. Repeated Aros and Örebro directory entries were merged.

Open leads: obtain dated site-specific evidence for the undated SFF entries. Kiruna, Luleå/Kallax, Karlsborg and Skavsta remain historical directory leads; military access and exact landing areas at Karlsborg need confirmation. Örebro's club dissolution is documented in May 2025. Borglanda's tourist page gives July dates but no year, so its recurring operation is retained as uncertain. Mohed and Gotland operator pages could not be fully read. The 2025 SFF rules PDF surfaced in search but was not parsed; it may resolve authorized landing areas and historical sites.

Records without coordinates: `se-optand`, `se-mohed`, `se-skarstad`, `se-feringe`, `se-eslov`, `se-nasinge`, `se-borglanda`.

Record-level opened URLs, check dates and evidence are retained in `SE.json`; the sources above are the main reconciliation sources.

## FI

Sources checked: [Finnish Aeronautical Association club directory](https://ilmailuliitto.fi/ilmailuliitto/ilmailukerhot/?filter_ilmailulaji=laskuvarjourheilu), [2021–2025 club jump totals](https://laskuvarjotoimikunta.ilmailuliitto.fi/wp-content/uploads/sites/5/2026/02/Hypyt-kerhoittain-2021-2025.pdf), [8 February 2026 presentation with 2025 club/locality table](https://laskuvarjotoimikunta.ilmailuliitto.fi/wp-content/uploads/sites/5/2026/02/esitelma_25_netti.pdf), [DropzoneFinder Finland](https://dropzonefinder.com/dropzones/finland), operator sites, [Visit Kemi](https://visitkemi.fi/kohde/skydivekemi/), OSM and airport pages.

Twelve place-level bases match nonzero 2025 club activity in the federation table. Oulu's earlier club names collapse into Oulu Skydive Center. Historical Utti and Skydive Finland listings concern one airfield. The Turku operator identifies Turku airport; Oripää was not substituted on the strength of unrelated air-sport activity. Tampere's FAQ names both Jämi and Pirkkala, but the dated federation table identifies Jämi only.

Open leads: Tandemtehdas has 2025 jumps under locality Helsinki, but a physical operating field was not established; its business location is not a dropzone. Suomen Urheiluilmailijat / Räyskälä, Senior Skydivers and Pohjois-Suomen Urheiluilmailijat need actual regular-field evidence rather than membership/aircraft ownership alone. Skyxperience's Malmi listing and Arctic Circle/Rovaniemi remain uncertain historical leads; a formal Malmi closure source and the Arctic Circle club's actual airfield should be checked. Older Skyxperience Turku is an alias lead at the existing Turku field, not an additional airport. Kemi's own site was unavailable; the federation and local tourism source support its entry.

Records without coordinates: `fi-malmi`, `fi-rovaniemi`.

Record-level opened URLs, check dates and evidence are retained in `FI.json`; the sources above are the main reconciliation sources.

## DK

Sources checked: [DFU club list](https://dfu.dk/klubber/kluboversigt), [DFU booking portal club page](https://skydive.dk/om-os/klubber?page=1), [DropzoneFinder Denmark](https://dropzonefinder.com/dropzones/denmark), operator sites, [ØFK 2026 events](https://oefk.dk/kalender/liste/?eventDisplay=past&tribe-bar-date=2026-08-16), [Skydive Copenhagen](https://skydivecopenhagen.dk/om-os/), [Stauning operator closure statement](https://www.skydivestauning.dk/), OSM and airport pages. DFU's 2026 map image was fetched but not visually inspected; it was not treated as field-by-field confirmation.

Aversi and Nordsjælland share Aversi from 2026 according to DFU's booking portal. Herning club and Dropzone Denmark share one field. Skydive 2000 is the former Kolding club name. SkydiveX is an older Ejstrupholm listing. Samsø is a recurring ØFK spring operation; the calendar gives the school venue, not an exact landing polygon.

Open leads: most DFU entries lack a dated field-specific calendar in the material reviewed. Sydsjællands is listed at Haslev, but whether it shares Aversi was not established; no speculative extra field was created. Farum, POPS and JGKI lack a distinct confirmed civilian operating location. Roskilde and old Sundbylille remain uncertain historical places. Stauning's operator explicitly says the club closed on 31 December 2024; continued operation by a replacement was not established. Bornholm's current jumping availability needs confirmation. Some operator pages failed TLS or access checks. Samsø departure airfield and landing location remain unresolved.

Records without coordinates: `dk-aversi`, `dk-ejstrupholm`, `dk-samso-besser`, `dk-sundbylille`.

Record-level opened URLs, check dates and evidence are retained in `DK.json`; the sources above are the main reconciliation sources.

## IS

Sources checked: [Iceland Skydive event page](https://icelandskydive.com/tandem-event), [DropzoneFinder Iceland](https://dropzonefinder.com/dropzones/iceland), [Sandskeið airport page](https://en.wikipedia.org/wiki/Sandskei%C3%B0), [Hella facility page](https://ourairports.com/airports/BIHL/), local-language searches for fallhlífastökk and [Reykjavík air rescue service](https://www.fbsr.is/).

Hella has a published recurring three-day event in August 2026. Sandskeið remains an undated directory lead. The rescue service's 2026 jumping report concerns training in Florida and does not establish another Icelandic dropzone.

Open leads: no complete dated national dropzone list was obtained. Confirm FFF/Reykjavík club continuity, whether Sandskeið still hosts regular sport jumps, and whether Hella has additional operations outside the published annual event. The two records are a documented inventory with these gaps, not a certified exhaustive national register.

Records without coordinates: none.

Record-level opened URLs, check dates and evidence are retained in `IS.json`; the sources above are the main reconciliation sources.

## EE

Sources checked: [Estonian Air Sports Federation members](https://www.lennusport.org/liikmed/), [DropzoneFinder Estonia](https://dropzonefinder.com/dropzones/estonia), [Eesti Langevarjuklubi](https://skydive.ee/) and its [contact page](https://skydive.ee/kontakt/), [Eesti Lennuklubi](https://airsport.ee/), [Narva/Olgina operator](https://avianarva.ee/), [Nurmsi sports register](https://www.spordiregister.ee/et/ehitis/1924/nurmsi_lennuvali), Wikipedia airport pages and the shared OSM scan. EANS AIP ENR 5.5 pages were attempted but not successfully retrieved for coordinate extraction.

Rapla/Kuusiku is a single place with multiple operators. Kihnu is a recurring camp documented in June 2026. Tallinn business addresses were excluded. Nurmsi has a 2026 register update mentioning parachuting, but civilian regularity is not confirmed.

Open leads: Dropzone Eesti is a federation member whose website could not be read; whether it shares Rapla or operates elsewhere is unresolved. Narva's operator page is undated. Nurmsi's current civilian club access and exact position need confirmation. Military-only activity is not counted as an active civilian dropzone.

Records without coordinates: `ee-nurmsi`.

Record-level opened URLs, check dates and evidence are retained in `EE.json`; the sources above are the main reconciliation sources.

## LV

Sources checked: [Latvian parachuting federation](https://lif.lv/), [Skydive Latvia sport page](https://skydive.lv/en/pages/sports_and_funjumpers) and [contact coordinates](https://skydive.lv/en/pages/contact), [Daugavpils operator](https://dropzone.lv/) and [location map](https://dropzone.lv/contacts), [DropzoneFinder Latvia](https://dropzonefinder.com/dropzones/latvia), local-language searches for other airfields and the shared OSM scan.

The two established operators have dated 2026 federation/operator events. Daugavpils is the Grīva operation, not the separate international airport. The embedded map's camera centre was not used as an exact position. Jelgava is labelled closed by the directory, but without a dated independent closure source it remains uncertain.

Open leads: obtain Grīva and Jelgava coordinates from an AIP, OSM feature or unambiguous operator map marker. Cēsis searches did not establish a regular parachute operator. No complete official national operating-field register was located; additional temporary/club fields remain possible.

Records without coordinates: `lv-griva`, `lv-jelgava`.

Record-level opened URLs, check dates and evidence are retained in `LV.json`; the sources above are the main reconciliation sources.

## LT

Sources checked: [LPSF member permits](https://lpsf.lt/nariai-ir-nariu-leidimai/), [2026 Lithuanian AIP ENR 5.5](https://www.ans.lt/a1/aip/03_11Jun2026/2026-06-11-000000/html/eAIP/EY-ENR-5.5-lt-LT.html?amdt=show), [DropzoneFinder Lithuania](https://dropzonefinder.com/dropzones/lithuania), operator sites, [Ignalina listing](https://dropzonefinder.com/dropzones/lithuania/dz-ignalina), [Mažeikiai regional encyclopedia](https://mke.lt/Ma%C5%BEeiki%C5%B3_aviacijos_sporto_klubas), and the Vilnius activity page cited in LT.json.

Six clubs hold federation permits valid to February 2027. Their physical sites are cross-checked against the AIP; AIP coordinates describe parachuting-area reference points. Permit status is evidence of authorized operation, not a claim that jumps occur every day. Šeduva and Zarasai are retained as uncertain because an AIP area alone does not prove a regular civilian service.

Open leads: Šiauliai's older Šeduva listing conflicts with current search evidence naming Barysiai; the operator contact page returned 403/502, so verify the relocation and whether Šeduva still operates. Ignalina's operator continuity and exact airfield remain unresolved. Mažeikiai's operator domain was unavailable. AIP areas Aleksotas, Šiauliai military, Gaižiūnai and Pajuostis were not promoted to active civilian dropzones without access/operator evidence. Magic 4 and Pirmas šuolis have no issued federation permit in the opened list and no separately established field; they remain organization-level leads.

Records without coordinates: `lt-ignalina`.

Record-level opened URLs, check dates and evidence are retained in `LT.json`; the sources above are the main reconciliation sources.


## Follow-up

Follow-up date: 2026-11-14; researcher: codex. Reviewed all 50 initially uncertain records using 2025–2026 calendars, federation reports and local-language searches. Thirty received supported status changes; Ejstrupholm changed from active to uncertain because the operator now gives a temporary Viborg address. No records were deleted. Twenty of the 22 missing coordinate pairs were filled from opened airport/AIP pages or an operator-linked map. No Overpass requests were made in this follow-up; no sign-in, terms acceptance, contact or personal request-header data was used.

### Revised counts

| Country | Active | Seasonal | Uncertain | Closed | Total | Without coordinates |
|---|---:|---:|---:|---:|---:|---:|
| NO | 11 | 5 | 4 | 0 | 20 | 1 |
| SE | 10 | 6 | 4 | 1 | 21 | 0 |
| FI | 12 | 0 | 2 | 1 | 15 | 0 |
| DK | 12 | 2 | 4 | 1 | 19 | 1 |
| IS | 0 | 1 | 1 | 0 | 2 | 0 |
| EE | 1 | 1 | 2 | 0 | 4 | 0 |
| LV | 0 | 2 | 1 | 0 | 3 | 0 |
| LT | 6 | 0 | 3 | 0 | 9 | 0 |
| **Total** | **52** | **17** | **21** | **3** | **93** | **2** |

### Follow-up sources and decisions

- **NO:** NLF/Fritt Fall's dated December 2025 Bergen and Stavanger club reports confirmed Stend, Titlestad and Sviland; the July 2026 Bømoen article confirms operations continue despite a land dispute. Molde's April 2026 course, Viken's 2026 courses, Tromsø's 2026 calendar and Tønsberg's 2026 prices resolve Årø, Rakkestad, Langnes and Jarlsberg. The 2025 NLF meeting membership material supports Kjevik's club existence, but not field activity. Tromsø is recorded as a visiting operator at existing Elvenes, rather than another dropzone. [Bergen's directions](https://www.bfsk.no/v3/index.php?catid=37&id=502&option=com_content&view=article) link a public map whose KML has named landing-area points for Stend and Titlestad; these are not map camera centres. Kjevik and Bjorli use opened OurAirports references.
- **SE:** Opened and extracted the [2025 SFF annual report, published February 2026](https://sff.se/wp-content/uploads/2026/02/2025-Verksamhetsberattelse-SFF.pdf), reconciling operating-inspection abbreviations against SFF's club list and field pages. It supports Bankås, Mohed, Romme, Everöd, Eslöv and Skärstad; its dated championships support Gryttjom and Johannisberg. Umeå publishes a 2026 course and operating season. Smålands' public calendar confirms 2026 Feringe jumping and its July Borglanda week. Östersund's [public calendar](https://calendar.google.com/calendar/ical/ofsknet%40gmail.com/public/basic.ics) schedules jumping on 18–22 June 2025. The [Visby event announcement](https://happeningnext.com/event/let%E2%80%99s-rauk-boogie-experience-magic-gotland-eid3a0dcnwsb4) gives 29 June–5 July 2026 with sport, student and tandem jumping; Aros and the tandem provider are visiting operators on the single Visby record. This last source is a public secondary event listing, not direct proof that every scheduled jump occurred. Opened OurAirports pages filled all seven coordinate gaps. SFF report references to Skövde and Vårgårda need further field-level reconciliation before adding another place.
- **FI:** Rechecked the dated federation table and operator-location evidence. [Helsinki's September 2025 decision](https://paatokset.hel.fi/fi/asia/hel-2025-007869/4524ded0-bf76-4902-ac02-fcc32ea5c38f) confirms Malmi's revoked airport permit and redevelopment; marked closed. The opened Malmi airport encyclopedia page provides coordinates. Finavia's Rovaniemi noise plan explicitly associates occasional parachuting with Rovaniemi airport; its 2022 date does not establish 2025–2026 regularity. An opened EFRO airport page supplies the coordinates. Pirkkala remains distinct from the dated Jämi evidence.
- **DK:** Opened and extracted [DFU's 2026 representative-meeting material](https://www.dfu.dk/sites/default/files/dfu_rep_mode_2026_samlet.pdf), including its 9 January 2026 club roll, and cross-checked operating locations against DFU/operator pages. This supports Maribo, Sindal, Aars, Skive, Beldringe and Vamdrup; Rønne's small membership alone does not resolve its failed operator site or actual airport activity. Faxe's published 2026 PDF calendar and Tirstrup's public 2025–2026 calendar give field-specific activity. [ØFK directions](https://oefk.dk/find-vej/) give a temporary Viborg address while its contact page retains Ejstrupholm: ØFK is added to the existing Viborg operators, and historical Ejstrupholm stays uncertain. OurAirports labels the latter airfield closed; its coordinates describe the historical airfield, not a verified current touchdown location. Aversi coordinates come from its airport page; Sundbylille comes from [AIP ENR 5.5](https://aim.naviair.dk/media/files/iui0dmciy25/EK_ENR_5_5_en.pdf), at whole-minute precision. Aversi/NFK and Herning/Dropzone Denmark remain consolidated shared fields. Samsø/Besser remains separate from Samsø airport: a search surfaced a Dropzone Denmark July 2026 airport pop-up, but that does not locate ØFK's school-associated landing field and does not establish regularity for another record.
- **IS:** Repeated 2025–2026 Sandskeið/club searches did not establish regular activity at this historical site; current airport or airspace documentation does not itself prove civilian jumping. Hella's already dated 2026 event remains seasonal. No coordinate gaps.
- **EE:** Rechecked Nurmsi register and Narva operator leads and 2025–2026 local-language/AIP searches. Nurmsi's updated register does not establish regular civilian access, while Narva's parachuting page remains undated. Nurmsi coordinates now come from opened OurAirports EENI. Military/drone activity was not substituted for civilian sport activity.
- **LV:** Repeated Jelgava 2025–2026 searches did not resolve whether the historical operation is closed. Opened Grīva LV-0002 and Jelgava airport pages provide both missing coordinate pairs. Grīva is not Daugavpils international airport.
- **LT:** Rechecked Šeduva, Zarasai and Ignalina with 2025–2026 searches and official airfield/airspace leads. An authorized parachuting area does not establish regular civilian club service; the Šeduva/Barysiai relocation question remains unresolved, and the operator website was inaccessible. Opened OurAirports EYIG establishes Ignalina's coordinate pair. Existing current federation permits remain the basis for the six active records.

### Remaining uncertain records

Each remaining uncertain record has a one-line reason in `status_evidence`:

- `no-kjevik`: The 2025 NLF membership record confirms the club, but no 2025–2026 Kjevik jumping calendar or booking evidence was established.
- `no-leknes`: The operator mentions an annual Lofoten boogie, but no 2025–2026 event explicitly at Leknes was established.
- `no-vaernes`: Historical directory location; the current operator identifies Oppdal, with no 2025–2026 regular jumping at Værnes established.
- `no-roros`: Historical directory location; the current operator identifies Oppdal, with no 2025–2026 regular jumping at Røros established.
- `se-kiruna`: Historical directory lead absent from the current SFF club page; no 2025–2026 regular civilian jumping was established.
- `se-lulea-kallax`: Historical directory lead absent from the current SFF club page; no 2025–2026 regular civilian jumping was established.
- `se-karlsborg`: Historical directory lead absent from the current SFF club page; no 2025–2026 regular civilian jumping was established.
- `se-skavsta`: Historical directory lead absent from the current SFF club page; no 2025–2026 regular civilian jumping was established.
- `fi-pirkkala`: Operator information names Pirkkala, but dated 2025 federation evidence concerns Jämi and no 2025–2026 Pirkkala schedule was established.
- `fi-rovaniemi`: Finavia confirms occasional parachuting in 2022, but no 2025–2026 evidence of regular civilian operation was established.
- `dk-ronne`: The January 2026 DFU roll includes the Rønne club, but its website failed and recent jumping at Bornholm airport remains unverified.
- `dk-ejstrupholm`: ØFK directions now give temporary operations at Viborg while its contact page retains Ejstrupholm; the airport directory marks Ejstrupholm closed and ongoing jumping here is unverified.
- `dk-roskilde`: The AIP permits parachuting here, but no 2025–2026 operator or regular jumping schedule was established.
- `dk-sundbylille`: NFK shares Aversi from 2026; the historical Sundbylille site remains in an older AIP, without evidence of continued regular jumping.
- `is-sandskeid`: Historical directory listing; no 2025–2026 calendar, booking page or dated public activity at Sandskeið was established.
- `ee-nurmsi`: Airfield and parachuting references remain, but no 2025–2026 evidence established regular civilian-access club jumping.
- `ee-olgina`: The aviation operator describes parachuting, but no dated 2025–2026 calendar or activity evidence was established.
- `lv-jelgava`: Historical directory evidence suggests closure, but no dated 2025–2026 operator activity or definitive closure statement was established.
- `lt-seduva`: An AIP parachuting designation remains, but no 2025–2026 regular sport operation was established and the listed operator website was inaccessible.
- `lt-zarasai`: An AIP parachuting designation remains, but no 2025–2026 regular civilian operator or jumping calendar was established.
- `lt-ignalina`: The historical operator listing and airfield location are established, but no 2025–2026 regular jumping activity was verified.

### Remaining coordinate gaps and validation

- `no-sviland`: the operator identifies a landing portion of farmland at Søredalen 29 and publishes an image, but no opened source established a coordinate for that landing field. Sola departure-airport or Sviland village coordinates would be misleading, so both coordinates remain null.
- `dk-samso-besser`: ØFK's recurring event gives Samsø Efterskole, Besser Kirkevej 30, as its venue; neither the precise landing field nor its departure airfield was established. School/address or unrelated Samsø-airport coordinates were not substituted, so both coordinates remain null.

All eight JSON files validated with `python3 -m json.tool`; required fields, unique place keys, coordinate pairing, status values and source presence also passed. All coordinate sources used were opened. The two remaining coordinate gaps and 21 uncertain statuses are research limitations, not claims of inactivity. No commit was made.

## Aggregator sweep — Codex, 2026-11-14

Started from [Skydiving Source Europe](https://skydivingsource.com/dropzones/europe/) and its country tables, then independently read the [Skydiving.com international directory](https://skydiving.com/find-a-skydiving-center/) country tables and compared names, addresses and airfields with the inventory. [Skyderby places](https://skyderby.io/places) supplied another cross-check; its BASE exits were excluded. Directory names alone were not treated as evidence of current activity. Dropzone.com `/dropzones/europe/` returned 404, and dropzones.eu did not resolve; these sources were unavailable, not empty. USPA's public Mirosławice entry, DropzoneFinder, operator calendars and local-language follow-ups were used for specific leads. No sign-in, contact, form submission or Overpass queries were used.

New coordinate pairs came from the opened [OurAirports airport dataset](https://davidmegginson.github.io/ourairports-data/airports.csv), except Kyiv-South's opened airport article. These are airfield reference points, not purportedly precise parachute landing targets. An undated offer stays uncertain even when its website is reachable. This is a directory reconciliation with documented gaps, not a guarantee of exhaustive current operation.

- NO: Bergen, Bodø, Grenland, HaGL/Hamar, Kjevik, Nimbus, NTNU/Oppdal, Oslo/Østre Æra, Voss, Stavanger, Tønsberg, Troms and Tromsø resolve to existing places; Lesja resolves to Bjorli. No new airfield established.
- SE: Aros, Cirrus, Dala, Halmstad, Linköping/Motala, Nyköping, Örebro, Östersund, Gotland, Skåne, Stockholm, Sundsvall, SYD, Småland, Söderhamn and Umeå match existing places. City labels are not extra dropzones.
- FI: Hämeenlinna is the club mailing locality, with Vesivehmaa already recorded; SkyXperience's former Malmi base is already recorded. Other directory airfields match the inventory. [Operator history](https://skydivehame.fi/pages/historia) and [Malmi company list](https://www.malmiairport.fi/toiminta/yrityksia/) were found as additional leads; neither establishes a missing current place.
- DK: Århus, Aversi, Herning, Odense, DFC/Faxe, Kolding, West Jump/Skive, Rødby/Maribo, Lindtorp, Aars, Nordsjælland, Stauning, Viborg, Ejstrupholm and Varde already match. IS Hella, EE Rapla/Nurmsi, LV Limbazi/Grīva and LT Pociūnai/Klaipėda/Sasnava/Šerkšnėnai/Šeduva/Kyviškės also match.
- Coordinate retries: the opened [Stavanger landing-field directions](https://www.sfsk.no/hoppfelt) identify a portion of farmland at Søredalen 29 but do not supply a usable coordinate. The reopened [ØFK 2026 calendar](https://oefk.dk/kalender/liste/?eventDisplay=past&tribe-bar-date=2026-08-16) identifies Samsø Efterskole as the event venue, without locating the actual landing field. Both pairs remain null; neither Sola nor the school centroid was substituted.

| Country | Added | Keys added | Existing coordinate pairs filled | Active / seasonal / uncertain / closed |
|---|---:|---|---:|---|
| NO | 0 | — | 0 | 11 / 5 / 4 / 0 |
| SE | 0 | — | 0 | 10 / 6 / 4 / 1 |
| FI | 0 | — | 0 | 12 / 0 / 2 / 1 |
| DK | 0 | — | 0 | 12 / 2 / 4 / 1 |
| IS | 0 | — | 0 | 0 / 1 / 1 / 0 |
| EE | 0 | — | 0 | 1 / 1 / 2 / 0 |
| LV | 0 | — | 0 | 0 / 2 / 1 / 0 |
| LT | 0 | — | 0 | 6 / 0 / 3 / 0 |

All listed country JSON files passed `python3 -m json.tool`; new keys are unique and coordinate pairs are present for every addition. No commit was made.
