# Coverage: Benelux and the Alps (NL, BE, LU, CH, AT, LI)

Researcher: claude, 2026-11-14. Development data only. These records have not been reviewed.

## Method and limits (all six countries)

- **OpenStreetMap:** a single Overpass query for `sport=parachuting|skydiving`, plus aerodromes whose name or
  operator mentions parachuting, across all six countries. It succeeded once, on the maps.mail.ru mirror. Every
  later Overpass call returned 429 or 504 on overpass-api.de, kumi, mail.ru and private.coffee. I then used the
  OSM API 0.6 `map` call for small bounding boxes (Fromberg, Radfeld, Thalgau) and Nominatim for a few addresses.
  The OSM sweep file from another agent (`_osm-sweep.json`) has no candidates for these countries: every query in
  it timed out.
- **Coordinates:** aerodrome positions come from the OurAirports open data CSV
  (davidmegginson.github.io/ourairports-data/airports.csv) when no OSM parachuting object was found.
  OurAirports gives the aerodrome reference point, not the landing area. Records cite whichever source was used.
- **Directories:** skydivelocations.com could not be read (TLS errors) and dropzone.com was not opened.
  Aggregator and reseller pages were used only as leads.
- **Facebook and Instagram:** seen only through search-result snippets. I did not sign in and opened no pages there.
  Wherever a record relies on a snippet, it says so.
- **Codex:** the codex MCP server failed to connect in this session, so this research had no Codex input.

## Netherlands (NL.json): 8 records

Sources checked: KNVvL parachuting pages (knvvl.nl/parachutespringen, "je eerste sprong"), which link to
parachute.nl/paracentra (the KNVvL section's list of 8 centres with their own dropzone); each operator site; OSM;
OurAirports.

| Status | Count |
|---|---|
| active | 7 |
| seasonal | 1 (Hoogeveen) |

Open:
- Skydive Rotterdam lands at Rhoon, but no source gives that landing area's position, so its coordinates are null.
  The aircraft departs from EHRD.
- KNVvL also lists Airmoves, Airboss, the KMA cadet club and Parachute Group Holland. These train abroad or serve
  closed groups and have no Dutch dropzone of their own, so they have no records.
- Tunnels (Roosendaal, City Skydive Utrecht) are excluded.
- One KNVvL information sheet mentions about 20 published para drop areas, not all permanently active. Some may be
  demo or military areas; the AIP list was not checked.

## Belgium (BE.json): 7 records

Sources checked: Skydive Flanders (pcv.be: Moorsele, Schaffen, Zwartberg); Skydive Spa; Skydive Cerfontaine;
Paraclub Namur; Skydive Antwerp (Hoevenen); an RTBF article on Walloon dropzones; a manawa.com article (leads);
OSM; OurAirports. I found no public list of member centres from the federations (FBP, the Walloon federation,
or the Vlaamse Vereniging voor Parachutisme). parachutisme.be (Skydive asbl) is a school that jumps at Spa and
Cerfontaine, so it has no record of its own.

| Status | Count |
|---|---|
| active | 5 |
| seasonal | 1 (Namur-Temploux) |
| uncertain | 1 (Hoevenen: live site, but no dated evidence) |

Open:
- Skydive2fly at Cerfontaine: a 2024 headline says it returned. I have not confirmed that it is still running
  alongside Skydive Cerfontaine.
- Saint-Ghislain (EBSG): a Facebook video title reads "Skydive St-Ghislain - Cerfontaine". It may be a former
  dropzone. Not checked.
- The three Skydive Flanders dropzones rely on the operator's current list (footer 2026). No dated jump post was
  opened.
- The Belgian Defence parachute school at Schaffen is part of the Schaffen record and has no separate record.

## Luxembourg (LU.json): 1 record

Sources checked: Skydive Luxembourg (skydive.lu); OurAirports; the OSM query (no LU hits). There is 1 active
dropzone: Noertrange (ELNT). I found no second dropzone.

## Liechtenstein (LI.json): 0 records

Liechtenstein has no airfield. The OSM query returned nothing, and no operator was found. LI.json is written with
an empty list. Jumpers from Liechtenstein use Swiss or Austrian dropzones; Hohenems (AT) is the nearest.

## Switzerland (CH.json): 21 records

Sources checked: Swiss Skydive's "Schulen/Clubs" page, which lists 13 certified schools and 18 clubs; the site of
each school or club that resolved; Romandie Parachutisme "Nos terrains"; Flying-Devil's centres; Skydive
Ostschweiz (Sitterdorf and Kägiswil pages); FG Titlis's history; EngadinSky; Skydive Interlaken; Alp Skydive;
OSM; OurAirports.

| Status | Count |
|---|---|
| active | 11 |
| seasonal | 5 (Yverdon, Sion, Raron, Kägiswil, Samedan event) |
| uncertain | 5 (Triengen, Buttwil, Epagny-Gruyère, Château-d'Oex, Le Châble/Verbier) |

Three records have null coordinates: Interlaken (helicopter base not stated), Château-d'Oex and Le Châble.

Open:
- **Triengen and Buttwil:** PSC Triengen and FG Freiamt merged into DROPZONE 47 at Grenchen, and both club
  domains now serve the Grenchen site. The two airfields are probably no longer regular dropzones, but neither is
  confirmed closed. FG Freiamt's link to Buttwil is from general knowledge and needs confirming.
- **Clubs not placed at a site:** Swiss Skydive lists Gravity Skydiving (certified school), VIVA, Swiss POPS,
  Paraclub Jolly Roger's, Para-Club Genève and Eagles Para-Club Sigriswil. Their home dropzones were not
  determined. Sigriswil may jump at Reichenbach, and Genève may jump in France; both are guesses and not recorded.
- **Colombier (NE):** Romandie Parachutisme's menu has a "Tandem – Colombier (NE)" item. The site and its
  coordinates were not checked.
- **Skydive Interlaken:** its Interlaken base or landing field is not stated. Gsteigwiler heliport (LSXG) is a
  candidate, not confirmed.
- **Military:** Locarno is shared with the Swiss Army's parachute reconnaissance training; no separate record.
- **Indoor:** Windwerk (OSM) is excluded as a tunnel.

## Austria (AT.json): 20 records

Sources checked: Österreichischer Aero-Club (only section contact sheets found; there is no public list of
dropzones); club and operator sites (Para Club Wiener Neustadt, Jumpclub Krems, Union Linz/Wels, freifall.at
Punitz, Alpenfreifall, UPCS Hohenems, 1. OEFC Graz, HSV Freistadt, Fallschirmzentrum Kärnten, HSV Red Bull
Salzburg, the IPPC/Pink Skyvan site); tandem reseller pages as leads (fallschirmsprung-tandem.at); OSM (Krems,
Skydive Tirol strip); OurAirports.

| Status | Count |
|---|---|
| active | 3 (Punitz, Zell am See, Hohenems) |
| seasonal | 9 |
| uncertain | 8 |

The uncertain records are Wiener Neustadt West and Wels (live sites, no dated entry), and six roaming jump sites
of Fallschirmzentrum Kärnten: Ferlach, Nötsch, Lienz-Nikolsdorf, Wolfsberg, Hirt and Wörthersee (Krumpendorf).

Open:
- **Wiener Neustadt:** I mapped the Para Club's "Flugfeldgürtel 5" address to Wiener Neustadt West (LOXN).
  This needs confirming against LOAN.
- **Gmunden:** the operator says "Gmunden". I mapped it to Gmunden-Laakirchen (LOLU), which needs confirming.
- **Fromberg:** the boogie venue is located only by its address (Fromberg 42). The runway is not in OSM.
- **Radfeld:** the OSM "Skydive Tirol" strip is matched to fallschirmspringen-tirol.at's "Radfeld" by position.
  skydive-tirol.at now redirects to a German club.
- **Wörthersee (Krumpendorf):** placed at the operator's street address. Neither the landing area nor the
  departure airfield is known.
- **St. Johann in Tirol:** based only on search snippets of bestfallschirm.com and Instagram. The site was not
  opened in full.
- **Leads with no record:**
  - Thalgau (Salzburg), the HSV Red Bull venue for the Parachute World Cup accuracy event, 2010–2026. This is an
    event venue, and its landing area was not located; OSM has two windsocks near 47.81, 13.25.
  - Trieben (LOGI): named by a tandem aggregator only.
  - Spitzerberg (LOAS): no parachuting evidence found.
  - Fallschirmzentrum Kärnten's Lavamünd/Libeliče and Bovec sites are in Slovenia, so they belong to the SI
    researcher.
  - A 2023 Aero-Club Kärnten folder names clubs at Klagenfurt, Feldkirchen, Friesach and Nötsch (search snippet
    only).
  - The Bundesheer (army) parachute units, including Wals/Salzburg, were not researched.
- Ternberg (OSM "Landeplatz Ternberg") is a paraglider landing field, so it is excluded.

## Check

Skeptical check by claude, 2026-11-14. I re-checked 35 of the 57 records, starting with the least certain. For each one I
opened the sources again, compared the ICAO coordinates with OurAirports (every ICAO record matches its OurAirports row;
OSM-based points are within 0.5 km), and looked for evidence dated 2025 or later. No point falls outside its country or
stated town. There are no duplicate keys or ICAO codes. The counts above this section are the researcher's; the totals
after this check are listed at the end of this section.

### Corrections

- **AT Wiener Neustadt West:** the Para Club's directions page says "Wir befinden uns auf dem WEST-Platz", so LOXN is
  confirmed. The club lists AFF courses for the 2026 season, so the status changes from uncertain to **seasonal**.
- **AT Wels:** Union Linz held a wingsuit competition at Flugplatz Wels on 15 August 2026 and the Upper Austria 4-way
  championship on 19 September 2026. The status changes from uncertain to **seasonal**.
- **AT Freistadt:** the status evidence said the 45th Para-Cross 2026 was held at Flugplatz Freistadt. SPORTUNION
  WINNER 02/2026 says it was held in Bad Leonfelden. The evidence now rests on the club's own posts dated 2025 and 2026,
  and the record says where the Para-Cross took place.
- **AT Gmunden:** confirmed as Gmunden-Laakirchen (LOLU). A Fliegerclub Traunsee post (the airfield's club) says
  Alpenfreifall jumps there. The "Confirm" note is removed.
- **AT Radfeld:** the operator's address (Wies 1, Radfeld) is about 130 m from the OSM Skydive Tirol strip, which
  confirms the match. Tirol Mountain Boogie dates in October 2026 are now the status evidence.
- **AT St. Johann in Tirol:** I opened the operator site in full. It gives Flugplatz St. Johann, Reitham 2 (about 130 m
  from LOIJ) and says the next season runs April–October 2027. The snippet-only note is removed.
- **AT Krems and Hohenems:** dated evidence added. Krems: Instagram posts from April and September 2026. Hohenems:
  the Austrian national championships were held there on 21–22 August 2026.
- **AT Graz:** the OEFC page lists 2026 course dates but also says no more courses take place in 2026. The record
  stays seasonal, with a note about this conflict.
- **BE Hoevenen:** the Skydive Antwerp booking calendar lists tandem slots every weekend of November 2026. The status
  changes from uncertain to **active**.
- **BE Moorsele, Schaffen, Zwartberg:** the evidence was only a 2026 site footer. It is now the Skydive Flanders booking
  page ("2026 is volledig volzet", with bookings per dropzone) and the ODBN 2026 nationals at Schaffen. The operator
  website changes from pcv.be, which redirects, to skydiveflanders.be.
- **BE Cerfontaine:** dated 2026 evidence added (booking calendar, Instagram). The note now links the operator to
  Skydive Saint-Ghislain.
- **NL Rhoon:** the coordinates are no longer null. buijtenland-van-rhoon.nl says the landing site has been at the corner
  of Lageweg and Poelweg since 2020, and the point is that road junction from OSM. The record is marked approximate
  (100–200 m). A 13 December 2025 event page is added as evidence.
- **NL Hilversum:** the club roster shows jumping on 7 November 2026, added as evidence.
- **CH Château-d'Oex:** this record was removed and merged. It was the EPCO school's office, not a dropzone. EPCO's
  2027 jump agenda, posted on 27 October 2026, puts its jump days at Gruyères, Colombier, Bex and elsewhere. EPCO is now
  an operator at **CH La Gruyère (Epagny)**, which changes from uncertain to **seasonal**.
- **CH Buttwil:** the SES dropzone page and localcities.ch confirm that FG Freiamt jumped at Flugplatz Buttwil, so the
  "general knowledge" note is replaced. The status stays uncertain because of the merger into DROPZONE 47.
- **CH Interlaken:** the coordinates are no longer null. The operator's about-us page says its Interlaken office and
  dropzone are together at Mittelweg 11, Wilderswil, and the point is that address from OSM. It is marked as an address,
  not a surveyed landing area.
- **CH Lauterbrunnen:** the operator confirms its dropzone is at the Air Glaciers Lauterbrunnen heliport.
- **CH Sion and Yverdon:** the seasons as stated are now recorded: Sion October–February, Yverdon March–September.

### Added

- **AT Wiener Neustadt East (LOAN):** Heeres Fallschirm Sport Verein / Eastside Skydive, with weekend jumps at the civil
  airfield. Status **uncertain**: there is no dated jump post, only an image named "Tandem-Aktion-2025".
- **AT Niederöblarn (LOGO):** Fallschirmzentrum Niederöblarn, helicopter tandems at Flugplatz 83. The 2026 season has
  ended and 2027 dates will follow, so the status is **seasonal**.
- **CH Colombier (NE), Neuchâtel airfield (LSGN):** used by Romandie Parachutisme and EPCO, with four EPCO dates in
  2027. Status **seasonal**.
- **BE Saint-Ghislain (EBSG):** Skydive Saint-Ghislain opened there in October 2022. According to RTBF (17 October
  2023), its jumps moved back to Cerfontaine and France. Status **uncertain**: there is no 2025+ evidence of jumps there.

### Still doubtful

- AT: the six roaming sites of Fallschirmzentrum Kärnten have no dated jump days. The only Facebook dates visible
  (Nötsch in September, Hirt on 15–16 October) carry no year. The Wörthersee point is still the operator's street address.
- AT: Wiener Neustadt East has no dated 2025+ evidence. For Graz, it is unclear whether the 2026 courses ran.
- CH: Triengen and Buttwil (after the merger), and Le Châble/Verbier, which has no dated evidence and no position.
  Skydive Interlaken's Grindelwald dropzone has no position, so it has no record.
- CH: Gravity Skydiving, VIVA, Swiss POPS, Jolly Roger's, Para-Club Genève and Eagles Sigriswil are still not placed
  at any dropzone.
- BE: Skydive2fly is probably the same group as Saint-Ghislain/Cerfontaine; not confirmed.
- LI: still no dropzone. Balzers heliport (LSXB) exists, but I found no parachuting there.

### Totals after the check

| Country | Records | active | seasonal | uncertain | null coordinates |
|---|---|---|---|---|---|
| NL | 8 | 7 | 1 | 0 | 0 |
| BE | 8 | 6 | 1 | 1 | 0 |
| LU | 1 | 1 | 0 | 0 | 0 |
| CH | 21 | 11 | 7 | 3 | 1 (Le Châble) |
| AT | 22 | 3 | 12 | 7 | 0 |
| LI | 0 | 0 | 0 | 0 | 0 |

All six JSON files were validated with `python3 -m json.tool` after the edits.

## Codex cross-check

Checked independently on 2026-11-14. Existing uncertain records and directory-only evidence were reviewed with operator pages, dated calendars/news and local-language searches. A failed page load or a copyright year was not treated as evidence of recent jumping. No login, contact, booking, Overpass query, commit or push was made.

Coordinate method: opened the [OurAirports airport dataset](https://davidmegginson.github.io/ourairports-data/airports.csv) and compared every existing non-null point with its named airfield, rather than replacing coordinates with the nearest airport indiscriminately. Airport reference points establish the airfield, not the exact parachute target. Off-airfield sites and unresolved points are described below. Counts supersede earlier sections; additions can remain uncertain when the place is confirmed but recent operation is not.

### Austria

- **Four upgrades to seasonal**: Wiener Neustadt Ost, Ferlach, Nötsch and Wörthersee. The [ÖAeC register dated 3 February 2026](https://www.aeroclub.at/uploads/download/OeAeC_FAA_ato_FAL_001_i021_fallschirmspringerschulen.pdf) identifies LOAN explicitly, and the Eastside operator confirms weekend jumping. The [Kärnten 2026 calendar](https://www.fallschirmspringen-kaernten.at/de/termine.html) supplies site-specific dates for the other three.
- Lienz, Wolfsberg and Hirt remain uncertain: still in the operator directions, absent from its 2026 calendar. Added **Trieben, uncertain**: explicit training location in the 2026 register, but no recent Trieben date on the [Pink schedule](https://pink.at/schedule.htm).
- Coordinates: all 22 original points compared with airport data. Twenty are airfield points, while Wörthersee and Fromberg required separate checks. **Wörthersee coordinates removed** because they pointed to the meeting-address building, not a confirmed landing area. **Fromberg corrected** from Steinberghalle to the Waldviertel Boogie map destination linked in the operator's November 2026 schedule; this is a venue pin, not a surveyed target. New Trieben uses opened OurAirports LOGI.
- German completeness searches and the new school register raised Klagenfurt and Linz. [Union Linz](https://www.unionlinz.com/) explicitly jumps at Wels, already present. [KFSC calendar](https://kfsc.at/termine.html), including its public JavaScript, identifies Wörthersee/Nötsch/Glainach/Feldkirchen dates; Klagenfurt's office/training-register address does not justify another landing-place record. Thalgau's competition landing site and whether Klagenfurt Airport itself has separate regular jumps remain leads.

### Switzerland

- Strengthened four active records: Kappelen and Beromünster with [SPHAIR 2026 course reports](https://sphair.ch/de/mediahub/sphair-para), Locarno with the operator's [2026 calendar PDF](https://www.paracentro.ch/images/PCL-PDF/prezzi_web_kl.pdf), and Sitterdorf with its [13 May 2026 ticket update](https://www.skydive-ostschweiz.ch/dropzone). Fehraltorf's operator schedule confirms jumping, but dated embedded calendar entries could not be read; federation evidence remains its dated basis.
- Triengen and Buttwil remain uncertain: redirects/merger evidence do not establish whether all jumping at the old airfields ended. Verbier remains uncertain and unlocated: its [tourism listing](https://www.verbier.ch/decouvrir/explore-activites/chute-libre-avec-alpskydive-le-chable-fr-2993420/) shows 2026 opening but a 2024 last-updated stamp, and gives only the address.
- Added **Bressaucourt, uncertain**: [Swissboogie calendar](https://swissboogie.ch/de/pages/fallschirmsprungkalender) names this jump site and [Jura Tourisme](https://www.j3l.ch/fr/P33534/a-faire/sport-loisirs/fun-aventure/saut-en-parachute) offers it; dated embedded events were not readable. Coordinates from OurAirports LSZQ.
- Coordinates: all 20 original non-null points compared; 19 match airfields/heliports, with Wilderswil retained as the separately documented off-airfield Interlaken landing place. No existing point changed. German/French/Italian searches found no further confirmed additions. Open: Verbier landing area, Grindelwald place, Bressaucourt dates, and old Triengen/Buttwil operations.

### Belgium

- Saint-Ghislain remains uncertain: no 2025+ resumption confirmed. The opened [Walloon federation](https://fwcp.be/) lists Spa, Cerfontaine and Namur; absence is not proof of closure.
- All eight coordinate points checked against airport data, no corrections. French/Dutch completeness searches and the federation list produced no confirmed missing regular DZ. Existing other records already have 2025/2026 activity beyond directory membership. Saint-Ghislain reopening remains the gap.

### Netherlands

- Added **Westbroek, active**, and **Baarn, uncertain** as separate landing places of Skydive Hilversum, not duplicate operators at Hilversum airport. The [operator page](https://www.skydivehilversum.nl/en/im-a-skydiver/) and [airport guide](https://www.ehhv.nl/for-pilots/para-jumping-dropzones) explicitly distinguish all three. [Safety Board report](https://onderzoeksraad.nl/onderzoek/bijna-botsing-met-parachutist-diamond-aircraft-industries-inc-da20-a1-dropzone-westbroek/) establishes jumping at Westbroek in March 2025; no dated Baarn jump was confirmed.
- Coordinates: seven existing airport points checked against OurAirports; Rhoon's off-airfield approximate junction point reviewed against [operator directions](https://skydiverotterdam.com/routebeschrijving), with its prior 100–200 m caveat retained. Both added locations use explicit destination coordinates in the opened operator page's map links. Thus ten place coordinates reviewed; Rhoon's precise target is still unresolved, not falsely moved to Rotterdam airport.
- Dutch completeness searches exposed these extra landing areas despite the eight-centre federation count. Echten (Hoogeveen alternative landing area) remains a lead without a confirmed recent place-specific schedule. LVNL AIP pages failed or returned 403/oversized PDF; their search-result coordinates were not used. Baarn's recent activity remains uncertain.

### Result counts

| Country | Active | Seasonal | Uncertain | Closed | Added | Upgraded | Downgraded | Closed in check | Existing coordinates changed | Null coordinates |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| AT | 3 | 16 | 4 | 0 | 1 | 4 | 0 | 0 | 2 | 1 |
| CH | 11 | 7 | 4 | 0 | 1 | 0 | 0 | 0 | 0 | 1 |
| BE | 6 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| NL | 8 | 1 | 1 | 0 | 2 | 0 | 0 | 0 | 0 | 0 |

Validation: each country file passed `python3 -m json.tool`; unique keys, status values, source presence and paired coordinates checked. Countries with fewer than ten records were checked in full.
