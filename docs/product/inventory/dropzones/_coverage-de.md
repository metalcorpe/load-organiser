# Coverage: Germany (DE)

Researched 2026-11-14 by claude. File: `DE.json`, 106 records.

## Counts by status

| Status | Count |
|---|---|
| active | 22 |
| seasonal | 65 |
| uncertain | 18 |
| closed | 1 |
| **total** | **106** |

Two records have `null` coordinates (`de-grafenau`, `de-bonn-hangelar`), because no source states
where those clubs jump.

Six `seasonal` records are recurring event or occasional sites, not permanent drop zones: Heringsdorf
(Usedom), Borkum, Norderney, Cham-Janahof, Dingolfing and Bad Wörishofen. FSC Bielefeld's
Haxterberg, Beelen and Höxter sites are also used only on some dates. Leave these out of the map
if it should show only permanent drop zones.

## Sources checked

- **DFV (Deutscher Fallschirmsport Verband).** I read the alphabetical member list at
  `https://www.dfv.aero/Info/Plätze Vereine/alphabetisch` (99 entries, one of them a test entry
  called "lstest") and all 99 club detail pages. They give the address, website, season and
  aircraft. I also read the 96 map markers embedded in the DFV map page. Many markers are only
  town-level positions (for example Hamburg 53.55,10.0 and Berlin 52.5167,13.4), so I did not use
  them as coordinates.
- **OpenStreetMap Overpass.** I queried `sport=parachuting|skydiving` plus aerodromes whose name
  or operator mentions Fallschirm, Skydive or Parachute, and got 39 features. Where they exist, I
  used the parachuting nodes and ways for the landing area. A query for all aerodromes in Germany
  failed because the public Overpass servers were overloaded (HTTP 502). OSM node 11602226198,
  tagged "FSC 1. LLDiv Bruchsal", sits near Hockenheim and looks misplaced, so I did not use it.
- **OurAirports.** `airports.csv` gave the airfield reference points where OSM had no parachuting
  feature. Each record's `coordinates_source` names the OurAirports page.
- **Operator websites.** I fetched about 110 home pages and searched them for 2025–2027 dates.
  These sites did not respond or blocked the scripted fetch: tandemspring.tv,
  fallschirmsport-erfurt.net (the .de site works), skydive-westerwald.de, feg-fallschirm.de,
  fsg-im-dlr.de (404), flugsportverein-durach.de, fsc-bruchsal.de (503),
  Fallschirmsportclub-Braunschweig.de, fsv-eilenburg.de, psv-fallschirmsport.de (parked domain),
  skydive-finsterwald.de, skydive-salamanca.de, skybruecken.de and skydive-zweibruecken.de (403),
  firebird-skydiving.de (401), liftnfly.de, fssc-thueringia.de, fsc-nordost99.de and
  skydive-stendal.de.
- **Aggregators, used as leads only.** These were sky-junkies.de (its map list sorted by state),
  tandemsprung-finden.de/anbieter (the 2026 provider list), fallschirmspringen.info (a JavaScript
  map whose data I could not read), skydivingsource.com, tandemfactory.de and Edi Engl TandemFun's
  list of jump sites.
- **Web search** (Tavily and WebSearch) for each lead, including public Facebook and Instagram
  snippets. I did not sign in anywhere and only used what search results showed.

## Still open

These are clubs with no confirmed jump site. None of them has a record:

- BLUE SKY (Stuttgart, listed by DFV): no website. It is probably connected to Blue Sky
  Adventures at Weckrieden.
- Air Adventures UG (Merdingen, tandemspring.tv): the site did not respond. It may be a tandem
  reseller.
- FEG Lüneburg e.V.: listed by DFV with no address and a website that did not respond.
- ORBITS e.V. (Hamburg), PSV Berlin e.V. and Paraclub Karlsruhe e.V.: DFV gives only postal
  addresses, and none of them has a working website.
- Para-Club Bad Ditzenbach e.V. (sky-junkies.de): DFV gives a postbox only, and the jump site is
  unknown.
- Grounded Skydivers Berlin e.V.: DFV gives an Ilberstedt address. The jump site might be
  Bernburg, but that is unconfirmed.
- In- und Outdoor Skydiving e.V. (ios.aero, Hude): DFV says it flies a Caravan all year, and its
  marker is at 53.1154,8.4700. Which airfield it uses is unconfirmed.
- Berliner Fallschirmsportverband (sky-junkies): no jump site found.
- Skydive Dreams (Langenhagen), Funjump Tandemspringen, Lift'n Fly, Fallschirmsport Airtime and
  SKYDIVE Saar Pfalz: these are tandem resellers or mobile teams. Where their sites were known, I
  recorded those airfields instead.

These records need a check:

- **Eisenach-Kindel**: I marked it closed because a January 2026 newspaper calls Dädalus
  insolvent, but DFV still lists the club.
- **Bautzen**: a neighbouring club says the "Skydivepark Bautzen" has closed. FSC Dresden is still
  listed there, so the status is uncertain.
- **Hüttenbusch and Lüchow-Rehbeck**: DFV still lists both, but Tandem-Skydive now advertises only
  Karlshöfen and Stade.
- **Seedorf**: a 2024 newspaper reported that the club faced closure, and no newer evidence was
  found.
- **Lahr**: Breisgauverein may have moved to Rottweil-Zepfenhan, where "Black Forest Skydive"
  operates.
- **Jena-Schöngleina, Stendal-Borstel, Bienenfarm, Kaufbeuren, Bad Dürkheim and Bremerhaven**:
  these have only aggregator entries or no dated activity.
- **Schwarzheide, Oberpfaffenhofen (DLR), Finsterwalde-Schacksdorf and Lechfeld**: these are
  DFV-listed, but I found no dated activity.

Other leads I did not research:

- Langeoog (Flying Bones event) and Paderborn-Haxterberg tandem days (seen on Instagram).
- Mühlacker (Hangensteiner Hof), Pfullendorf and Giengen/Brenz, where Jump & Fun Factory or
  sky-dive.de jump on some dates.
- Bonn-Hangelar.

Also check:

- Military drop zones other than Altenstadt and Seedorf, if the owner wants them.
- Whether 2026 dates exist for the 31 active or seasonal records whose `status_evidence` starts
  with "DFV list". They rest on the current DFV listing, or on DFV plus a live 2026 site, rather
  than on a dated post.

## Check

Skeptical check on 2026-11-14, by a second agent (claude). It covered 22 records, chosen from the
uncertain ones, the single-source ones, those with no ICAO code and those where an operator's site
looked dead. It also compared every point with OurAirports and checked for duplicates.

Coordinates and duplicates:

- All 103 records with a position lie in Germany. Each one with an ICAO code is within 2.2 km of
  the OurAirports point for that code. The one at 2.2 km is Kassel-Calden, where the OSM node is
  the Aero Fallschirmsport school inside the airport, so it is fine.
- No two records are within 3 km of each other, and all keys are unique, so there are no duplicates.
- **Bremerhaven**: I set the coordinates to null. The point was Luneort airport, which bremerhaven.de
  says closed on 1 March 2016, and sky-junkies places "Jumpzone" in Lower Saxony, not in Bremen. No
  source gives the jump site.
- **Calw**: the club site (fsc-calw.com) says the club jumps from the Bundeswehr training area in
  Calw. I renamed the record, updated the website and added the source. The OSM node (tagged
  sport=parachuting with the club as operator) is between Calw and Althengstett, and I kept it as
  the position. The exact landing area is not stated.

Status changes:

- **Bautzen**: uncertain → closed. Skydive Lausitz's 2026 season note says Skydivepark Bautzen has
  closed and is no longer available for jumping. DFV still lists FSC Dresden there, and the club
  site has an expired certificate.
- **Rheine-Eschendorf**: active → uncertain. fallschirmsport-rheine.de is now a parked domain, and
  the only evidence left is the DFV entry.
- **Braunschweig**: active → uncertain. The club domain does not resolve in DNS, and the only
  evidence is the DFV entry.

Evidence added, with status unchanged:

- **Eisenach-Kindel** (closed) and **Seedorf** (uncertain): both club domains are now parked, which
  supports their status.
- **Bad Lippspringe** (uncertain): the DFV page for FSC Paderborn names no jump site,
  fsc-paderborn.de shows only a hosting placeholder, and OurAirports marks the DZ closed. It could
  be closed, but no dated statement says so.
- **Finsterwalde-Schacksdorf** (uncertain): neither the DFV web link nor the DFV e-mail domain
  resolves.
- **Bonn-Hangelar** (null coordinates): DFV gives FSG Hangelar an office in Soest and a Do 28.
  Skydive Soest flies a Do 28, so the club may jump at Soest-Bad Sassendorf. This lead is noted
  but unconfirmed, and the coordinates stay null.
- **Bad Dürkheim**: added Jump & Fun Factory as a second operator. Its site lists the airfield
  (coordinates match EDRF) but says not every site is offered every season, so the status stays
  uncertain.
- **Burgheim**: confirmed. OSM tags the aerodrome sport=parachuting, and the club site has a live
  tandem ticket shop. I added both as sources.
- **Lahr**: the DFV detail gives a Lahr jump-site address. The club site is behind a bot check, so
  the status stays uncertain.

Checked and left unchanged: Grafenau (the DFV page has only a postal address), Oberpfaffenhofen,
Schlierstadt (OSM confirms Southsidebase, with opening hours March–October), Kassel-Calden,
Neustadt/Aisch (fsc-nea.de now redirects to dropzone-aisch.de), Fürstenzell, Kiel (now at
lsv-kiel.de), Rothenburg, Eggenfelden and Bad Wörishofen. OurAirports also lists a glider field
(DE-0072) in Bad Wörishofen, so which airfield is used remains unconfirmed.

Completeness: I added nothing. Overpass failed again (overpass-api.de and kumi timed out, and
mail.ru returned 504). Searches for Ballenstedt, Strausberg, Pasewalk, Mengen, Ahrenlohe and a
"Jumpzone" in Bremerhaven found no confirmed drop zone. Jump & Fun Factory also lists occasional
sites at Weinheim, Sinsheim, Mühlacker (Hangensteiner Hof), Pfullendorf and Lachen-Speyerdorf, but
with no dated jump days (its 2027 dates are not yet published). They remain leads, not records.

Totals after the check: 106 records. 20 active, 65 seasonal, 19 uncertain, 2 closed, 3 with null
coordinates.

## Codex cross-check

Checked 2026-11-14 by codex. The input had 106 records: 20 active, 65 seasonal, 19 uncertain and 2 closed. The earlier “31 DFV-only” count predates the preceding review: the file received here had 29 active/seasonal records beginning with “DFV list”, plus the 19 uncertain records. All 48 were reviewed. Original researcher metadata is retained; this section records the second-model audit.

### Results

- 0 uncertain records upgraded; 8 active/seasonal records downgraded to uncertain.
- 2 additional closures: Hartenholm and Bruchsal (civilian dropzone operation, not necessarily the whole airfield).
- Eggenfelden changed from active to seasonal because the operator says daily **during the season**, not year-round.
- 1 addition: Langeoog, with recurring 2026 visiting boogies documented by local reports and an operator calendar.
- 1 missing coordinate pair filled: Jumpzone Bremerhaven is at Kührstedt-Bederkesa (EDXZ), so its key/name/location were corrected.
- 10 existing coordinate pairs spot-checked; none was at the wrong airfield.
- Final totals: **107 records: 15 active, 61 seasonal, 27 uncertain, 4 closed; 2 without coordinates**.

### Activity evidence and decisions

Dates in copyright footers and search-engine crawl dates were not treated as jump dates. The [DFV change log](https://www.dfv.aero/Neues/Letzte%2B%C3%84nderungen), opened directly, shows that several still-visible directory records were last edited in 2022–2023. A live directory does not by itself establish a newly verified 2026 season. Public Facebook pages for Passau, Sylt and Kiel exposed titles but no dated posts; no login was attempted. Operator sites, public calendar feeds, local reports, DAeC and DFV were checked, with source URLs recorded in JSON.

| Place | Decision | Evidence / remaining limitation |
|---|---|---|
| Hartenholm airfield | seasonal → closed | Albatros states that jumping at Hartenholm is no longer permitted because it could not obtain usable take-off/landing permission; vouchers are now handled at Hungriger Wolf (operator and municipality pages checked 2026-11-14). |
| Bruchsal drop zone (Eichelberg) | seasonal → closed | Wikipedia states FSC Bruchsal used the Eichelberg military training area only until the end of 2022; a Bundeswehr notice dated 2026-02-08 refers to its former clubhouse. No successor civilian operation found. |
| Schwäbisch Hall-Weckrieden airfield | seasonal → uncertain | Para Club and airport still describe jumping at Weckrieden, but no dated 2025+ jump calendar or activity report was found; the live directory is not proof of a 2026 season. |
| Breitscheid airfield | seasonal → uncertain | Operator homepage says there is currently no jumping at Breitscheid; its calendar/status pages returned no readable dates, so a winter pause cannot be distinguished from a longer interruption. |
| Kempten-Durach airfield | seasonal → uncertain | Schatt explicitly says it currently offers no jumps at Kempten-Durach and redirects to other fields; no 2025+ local club activity was found. |
| Fürstenzell airfield | active → uncertain | Club website describes jumping but supplies no 2025+ activity dates; public Facebook view exposed only the page title and no dated posts. |
| Westerland (Sylt) airport | seasonal → uncertain | Operator describes an April–October season without a year; its booking page still shows cancelled 2020 events, and no dated 2025+ activity was readable publicly. |
| Rosenthal-Plössen airfield | active → uncertain | Operator advertises weekend jumping at Rosenthal-Plössen, but no dated 2025+ jump activity or season calendar was found; a current copyright footer is insufficient. |
| Burgheim airfield | active → uncertain | Club describes regular Friday/weekend jumping and sells tandem vouchers, but no dated 2025+ jump day or season calendar was found. |
| Kiel-Holtenau airport | active → uncertain | LSV Kiel describes jumping but supplies no dated 2025+ activity on the page checked; Kiel-Boogie was blocked and the public Facebook view exposed no dated posts. |
| Thalmässing-Waizenhofen airfield | seasonal → seasonal | Operator publishes a 2026 season calendar with jumping events and training camps. |
| Grefrath-Niershorst airfield | seasonal → seasonal | Operator news dated 2026-03-09 announces season start; August 2026 news reports jumping and advertises Supervan operations on 28–30 August. |
| Rottweil-Zepfenhan airfield | active → active | Jump & Fun Factory training calendar, updated 2025-07-12, lists the 12–16 May 2025 AFF course at Rottweil; its operator description states year-round jumping. |
| Neustadt-Glewe airfield | seasonal → seasonal | Regional sports report dated 2026-09-16 discusses the home club and its 31 October 2026 end-of-season Scramble at Neustadt-Glewe. |
| Elmster Berg (FSC Münster) | seasonal → seasonal | Club events page lists Fallen Leaves on 4–6 September 2026 and the 27–28 September 2025 Speedstar event. |
| Neustadt/Aisch airfield (Eichelberg) | active → active | Current operator site publishes jump prices effective March 2025 and links its jump manifest; dated price publication corroborates the DFV listing, although no dated jump-day calendar was verified. |
| Lachen-Speyerdorf airfield | seasonal → seasonal | Public club calendar feed lists 2026 jump days through 31 October and a jump week beginning 20 July 2026; the feed also contains older years. |
| Günzburg-Donauried airfield | seasonal → seasonal | Club public calendar lists Sprungbetrieb on 11 and 26 April, 29 May, 15–16 August and 2 September 2026, plus a 5 September Scramble. |
| Trier-Föhren airfield | seasonal → seasonal | Club page publishes introductory courses on 15–16 May and 21–22 August 2026 and its anniversary on 29 August 2026. |
| Altenstadt army jump area | seasonal → seasonal | Club page explicitly describes its 2026 facilities and continuing Saturday/selected-Friday jumping from April to October; this corroborates the DFV listing, but a dated individual jump calendar was not readable. |
| Roitzschjora airfield | seasonal → seasonal | Sportstadt Leipzig article dated 2026-07-31 describes Skydive Leipzig operating at Roitzschjora with a Pilatus PC-6. |
| Meißendorf-Brunsiek | seasonal → seasonal | Operator booking page lists an AFF course at Sprungplatz Meißendorf on 29 April–2 May 2027 with remaining places; a published future season date, checked 2026-11-14. |
| Flensburg-Schäferhaus airfield | active → active | Club statement dated 2026-05-23 confirms its parachuting section trains students and makes sport jumps, while clarifying it does not sell or conduct tandem jumps. |
| Eggenfelden airfield | active → seasonal | Operator tandem-booking page is explicitly updated 2026-07-14 and advertises Eggenfelden jumps; homepage says daily operation during the season, replacing the directory claim of year-round daily jumping. No dated available slot was exposed in the public feed. |
| Stadtlohn-Vreden airfield | seasonal → seasonal | DFV national-championship site lists 6–13 September 2025 at Stadtlohn-Vreden with Skyfactory UG; former Skydive Stadtlohn ceased at the end of 2023, but the airfield has a successor. |
| Hildesheim airfield | seasonal → seasonal | Operator events page publishes May 2027 jumping/training events, including 27–29 May Ladies Days; confirms a forthcoming season beyond the undated directory entry. |
| Unterschüpf airfield | seasonal → seasonal | Operator calendar lists the 22–30 August 2026 jump week, 11 July 2026 World Skydiving Day and May 2026 canopy training. |
| Ganderkesee Atlas airfield | active → active | Local report dated 2026-05-11 announces YourSky jumping/tandem open days at Ganderkesee on 16–17 May 2026; corroborates current operator and DFV year-round listing. |
| Itzehoe/Hungriger Wolf airfield | seasonal → seasonal | IAS Itzehoer Airservice publishes a YUU Skydive flight-calendar entry for 23 August 2026; the current YUU operator site also advertises jumping at Hungriger Wolf. |
| Schwarzheide/Schipkau airfield | uncertain → uncertain | Club news dated January 2026 concerns the airfield lease dispute; no dated 2025+ jump operation was found. |
| Lahr airport | uncertain → uncertain | DFV still names Lahr, but the club site was unreadable and no dated 2025+ jumping at Lahr was found; Black Forest activity at Rottweil does not establish Lahr operations. |
| Lechfeld (Graben) | uncertain → uncertain | Club affiliation and activities elsewhere do not establish jumping at Lechfeld; no dated 2025+ civilian jump day at this military site was found. |
| Oberpfaffenhofen (DLR special airport) | uncertain → uncertain | The club parachuting page describes historical starts at Oberpfaffenhofen with landings at Maxhof and more recent visits to other dropzones; no dated 2025+ jumping at EDMO was found. |
| Grafenau area (Flying Bears e.V.) | uncertain → uncertain | DFV gives only a Flying Bears postal address; neither a physical dropzone nor 2025+ local jump activity was established. |
| Seedorf (Zeven) military jump area | uncertain → uncertain | The former operator domain is parked and a 2024 closure threat remains unresolved; no 2025+ regular civilian jumping was found, distinct from military demonstrations. |
| Braunschweig-Wolfsburg airport | uncertain → uncertain | DFV still lists the club and airfield, but the operator domain failed and no dated 2025+ jump activity was found. |
| Bad Lippspringe drop zone | uncertain → uncertain | Closure indicators concern the former civilian skydiving operation; no 2025+ civilian access or jump calendar was found, and military use alone does not establish a public dropzone. |
| Rheine-Eschendorf airfield | uncertain → uncertain | DFV retains the entry but the former operator domain is parked; no dated 2025+ activity or replacement operator was found. |
| Bonn-Hangelar (FSG Hangelar) | uncertain → uncertain | DFV identifies a Hennef postal address and Soest office, not a confirmed Hangelar landing area; no 2025+ local jumping or mappable site was established. |
| Finsterwalde-Schacksdorf | uncertain → uncertain | Both candidate operator domains failed to resolve; the directory entry was not corroborated by any dated 2025+ jump operation. |
| Hüttenbusch airfield | uncertain → uncertain | Tandem-Skydive now names Karlshöfen and Stade on its homepage; no 2025+ operation at Hüttenbusch was found. |
| Lüchow-Rehbeck airfield | uncertain → uncertain | Tandem-Skydive now names Karlshöfen and Stade on its homepage; no 2025+ operation at Lüchow-Rehbeck was found. |
| Jena-Schöngleina airfield | uncertain → uncertain | DAeC still lists the Thüringia school at Jena-Schöngleina, but its operator website was unreadable and no dated 2025+ local jumping was found. |
| Stendal-Borstel airfield | uncertain → uncertain | Airport company report dated 2022-06-15 describes the dissolution of Skydive-Stendal; no 2025+ successor jump operation was confirmed. |
| Bienenfarm airfield | uncertain → uncertain | Historical accounts and the airport description mention occasional parachuting, but no dated 2025+ regular civilian jump operation was found. |
| Bad Dürkheim airfield | uncertain → uncertain | Skyhopping still lists the location, but its calendar yielded no jump dates and Jump & Fun Factory does not yet publish site-specific 2027 dates. |
| Kaufbeuren air base | uncertain → uncertain | DFV lists the parachuting section, but club news concerns other flying activities; no dated 2025+ civilian jump operation was found. |
| Kührstedt-Bederkesa airfield (Jumpzone Bremerhaven) | uncertain → uncertain | The detailed Jumpzone directory entry identifies Kührstedt-Bederkesa, but no dated 2025+ activity or readable current operator calendar was found. |

The stronger new dated evidence includes Günzburg's public Google calendar, Lachen-Speyerdorf's public event feed, 2026 club events at Grefrath/Trier/Sendenhorst/Unterschüpf, the 2025 Rottweil course, the 2025 Stadtlohn championships, and published 2027 dates at Hildesheim and Meißendorf. Lachen-Speyerdorf's feed begins with 2018 entries but also contains 2026 events; its recent dates were filtered and read. Some September 2026 dates are explicitly cancelled, so the retained evidence cites other scheduled days.

Neustadt/Aisch, Altenstadt and Eggenfelden have weaker corroboration than a dated jump event: respectively a jump-price list effective March 2025, a club description explicitly discussing 2026 facilities alongside regular jumping, and a tandem-booking page updated in July 2026. Their current operator statements corroborate the existing DFV entry, but an individual dated jump day was not verified. These remain follow-up leads rather than being presented as completed-jump reports.

Stadtlohn is a useful operator/site distinction: the old business ended in 2023, while Skyfactory hosted the 2025 national championships at the same airfield. The operator was replaced in the existing record, not added as another dropzone. Bruchsal closure evidence is the historical end-of-2022 statement together with a February 2026 Bundeswehr notice describing the former FSC clubhouse. Stendal's 2022 airport report describes dissolution of its club; this does not rule out a successor, so Stendal remains uncertain.

### Coordinates

The following individual OurAirports pages were opened and their coordinates compared with the dataset (airport reference points, not guessed town centres).

| Place | Airport page | Reference latitude, longitude | Result |
|---|---|---|---|
| Hartenholm | [EDHM](https://ourairports.com/airports/EDHM/) | 53.915001, 10.035556 | Matches |
| Weckrieden | [EDTX](https://ourairports.com/airports/EDTX/) | 49.124443, 9.781111 | Matches |
| Breitscheid | [EDGB](https://ourairports.com/airports/EDGB/) | 50.676388, 8.169444 | Existing facility point about 0.44 km away, same airfield |
| Thalmässing | [EDPW](https://ourairports.com/airports/EDPW/) | 49.064167, 11.209167 | Matches |
| Grefrath | [EDLF](https://ourairports.com/airports/EDLF/) | 51.333889, 6.359444 | Existing facility point about 0.11 km away, same airfield |
| Durach | [EDMK](https://ourairports.com/airports/EDMK/) | 47.691944, 10.338056 | Matches |
| Rottweil | [EDSZ](https://ourairports.com/airports/EDSZ/) | 48.186604, 8.722801 | Matches |
| Neustadt-Glewe | [EDAN](https://ourairports.com/airports/EDAN/) | 53.362444, 11.613764 | Matches |
| Fürstenzell | [EDMF](https://ourairports.com/airports/EDMF/) | 48.518055, 13.345833 | Matches |
| Stadtlohn | [EDLS](https://ourairports.com/airports/EDLS/) | 51.995834, 6.840556 | Matches |

The [detailed Jumpzone directory entry](https://www.sky-junkies.de/sprungplatz/fallschirmsport-bremerhaven-jumpzone/) explicitly names Kührstedt-Bederkesa. Its [EDXZ airport page](https://ourairports.com/airports/EDXZ/) supplies 53.568054, 8.789444. This resolves the old Bremerhaven/Luneort ambiguity without inventing a landing point. [EDWL](https://ourairports.com/airports/EDWL/) supplies the new Langeoog point.

**Still null:** Grafenau (Flying Bears has only a postal address; no verified jump field) and Bonn-Hangelar (DFV gives Hennef/Soest addresses without identifying an actual landing site). Assigning Elsenthal, Bonn-Hangelar airport or Soest coordinates would be an unsupported inference. Overpass was not retried.

### Completeness and open leads

German-language searches checked “Fallschirmspringen”, “Sprungbetrieb”, “Sprungplatz”, “Boogie”, operator names and 2025/2026 dates. Langeoog is confirmed by the two dated local reports and Varrelbusch's calendar linked in its new record. Riedenheim/Oberhausen is a club address, not another present dropzone: [Skydive City's operator site](https://www.skydivecity.de/) and [directions on its calendar page](https://www.skydivecity.de/index.php/skydiven/termine) locate current jumping at already-recorded Rothenburg. DAeC's school address alone therefore did not justify a duplicate.

No dated recurring operations were confirmed for the other missing-place leads: Pfullendorf, Mühlacker/Hangensteiner Hof, Giengen/Brenz, Schopfheim/Seven Sky, or Diepholz. [Jump & Fun Factory's booking calendar](https://www.sky-dive.de/termint1.html) says site-specific 2027 dates will appear in February; it does not yet establish those sites. Paderborn-Haxterberg remains an earlier open lead; no confirmed recurring civilian operation was added. The 27 uncertain records remain explicit research gaps, not assumed closures.

Validation: JSON syntax, required fields, unique keys, coordinate pairing and status totals checked after editing; no commit made.

## Aggregator sweep


### Directory coverage and limits

Checked on 2026-11-14 by Codex, starting from external listings rather than the inventory. Opened the country listings on [SkydivingSource](https://skydivingsource.com/locations/europe/) and [Skydiving.com](https://skydiving.com/dropzone/location/), then compared names, physical places, operator aliases and ICAO codes with the JSON. Also opened [Flight-1's international dropzone/course-host directory](https://www.flight-1.com/dropzones), which exposed former operations and boogie sites absent from the first pass. These directories are leads, not evidence that every listed operation is still open.

The [dropzone.com Europe URL](https://www.dropzone.com/dropzones/europe/) redirected to unrelated content, [dropzones.eu](https://dropzones.eu/) did not return usable content, and the [USPA locator](https://www.uspa.org/dzlocator) returned a page shell without a usable international export. Their entries could not be exhaustively reconciled. No Overpass queries were made. Opened airport pages on OurAirports supplied sourced airfield coordinates for new airport records; exact off-airfield landing coordinates were not inferred from town centres or office addresses. No sign-in or contact was used. The sweep does not establish that the inaccessible directories or legacy office-only club entries contain no further sites.

Opened country lists: [SkydivingSource Germany](https://skydivingsource.com/locations/europe/germany/) and [Skydiving.com Germany](https://skydiving.com/dropzone/location/germany/).

- Added `de-muencheberg-eggersdorf` (EDCE), active: the Berliner Fallschirmsportverband operator brochure has May 2025 prices and a year-round weekend/holiday schedule. The airport's resident-clubs page supplies precise coordinates.
- Added `de-wesel-roemerwardt` (EDLX), closed: the Flight-1 My SkyConcept entry is historical; an opened Wesel municipal report explicitly records the operator withdrawing from the field. This does not mean the airport closed.
- Other identifiable directory places matched existing records, including Paderborn-Haxterberg; club/brand entries were not automatically treated as new airfields.
- Existing coordinate retries: reopened DFV Flying Bears/Grafenau and FSG Hangelar pages. They still provide postal/office addresses, not a verified landing site. Grafenau/possible Elsenthal and Hangelar/possible Soest remain unresolved; 0 previously missing pairs filled.
- New total: 109 records — 16 active, 61 seasonal, 27 uncertain, 5 closed; 2 without coordinates.
