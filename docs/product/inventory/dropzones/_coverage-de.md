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
