# Coverage: Iberia (ES, PT, AD, GI)

Researched 2026-11-14 by claude. Development data only; nothing here is checked by the owner yet.

## Method and limits

- **OpenStreetMap / Overpass: not used.** overpass-api.de returned 429 and 502 ("at capacity").
  The kumi.systems, private.coffee and mail.ru mirrors did not answer within 200 s. The shared
  `_osm-sweep.json` in this folder has no candidates. The OSM pass is still open; see "Open" below.
- **Coordinates** come from the OurAirports open dataset
  (<https://davidmegginson.github.io/ourairports-data/airports.csv>), matched by airfield name or
  ICAO code. Three ES records use the operator's own map point instead (Empuriabrava, El Pinar,
  Totana) and give the OurAirports value in `coordinates_source`. Barcelona-Bages uses the
  operator's schema.org point. All points are airfield reference points, not surveyed landing
  areas.
- **Facebook and Instagram** were read only through public search-result views. No page was
  signed in to.
- The Codex MCP server did not connect in this session, so all of this research was done by claude.

## ES: Spain (17 records; counts below updated by the check)

| Status | Count | Records |
|---|---|---|
| active | 11 | Empuriabrava, La Juliana, Lillo, Castellón El Pinar, El Berriel (Gran Canaria), Requena, Totana, Casas de los Pinos, A Fervenza (Mazaricos), Barcelona-Bages, Córdoba |
| uncertain | 3 | Ontur, Trebujena (Skydive Jerez), Chozas de Abajo (Skydive León) |
| closed | 3 | Ocaña (Skydive Madrid moved to Lillo in 2024), Matilla de los Caños (Skydive Valladolid, failed in 2025), Santa Cilia (the club jumps at Lasclaveries, France) |
| missing coordinates | 0 | |

All 5 ES venues from `../dev-listings.json` are merged in. La Juliana, Lillo and El Berriel now
have coordinates. iJump Gran Canaria is recorded at El Berriel airfield, not at its check-in office.

Sources checked:
- RFAE: only regulation PDFs were found, with no public list of centres. The earlier ES.md notes
  say the RFAE calendar showed no parachuting events.
- Operator sites: skydiveempuriabrava.com, skydivespain.com, skydiveatmosfera.com,
  skydivemadrid.es (including the presentation page), skydivelillo.com, skytime.es, ijump.es,
  ijumpskydive.com, skydiveaircruz.com (locations table), skydivetotana.es, skydivelamancha.com,
  paracaidismogalicia.com, saltamos.es, skydivecordoba.com and paracaidismonorte.com. The
  Pirineos site returned 403; the Skydive Jerez and León domains did not resolve.
- Aggregators, used as leads: skydivingsource.com (Spain list, 17 entries), Yumping (Spain list
  and Cádiz/Córdoba pages), Curlie, Manawa, Puraventura blog, extrmsport.
- Press and other: El País 2021, Diario de Valladolid 2026, es.wikipedia (Aeródromo de Requena),
  Tripadvisor and Instagram (public views).
- dropzone.com: its directory URLs now return 404 (the domain serves another site), so it was not
  usable.

Open leads, not recorded because no source places jumps at a specific airfield:
- **Lebrija, "Campo de Vuelo El Copero" (Skydive Lebrija):** named only in a Puraventura blog. No
  operator site was found. OurAirports has "Lebrija UL" (36.896, -6.039), but it is not confirmed
  as the same field.
- **Villamartín, LETF:** Yumping's Cádiz page says jumps are made there. No operator was
  identified.
- **Alhama de Murcia, LELH (Skydive España):** an old skydivingsource entry. It may be a
  predecessor of Skydive Totana; not confirmed.
- **Casarrubios del Monte, LEMT, and Colmenar Viejo:** named in a Puraventura blog. No operator
  was found.
- **"Skydive Pirineus" (Lleida):** named in a Puraventura blog. No operator or airfield was found.
- **Mallorca (Yumping lists "Alcudia"):** no operator site was found. MallorcaFly says it does not
  offer jumps.
- **Aircruz pages for Almería, Granada, Alicante, Castellón and Cuenca:** these look like
  resale/landing pages pointing to the group's own airfields. No separate airfield was found.
- **Excluded:** Norte Sky Dive (Leioa, Bizkaia) jumps at Mimizan, France. Paradise 64 / "Pau" on
  Yumping is in France. Puraventura (Alicante) and skydive.barcelona are resellers. Military-only
  sites, such as Alcantarilla (PAPEA) and Jerez, were not checked for civilian use.

## PT: Portugal (13 records after the check)

| Status | Count | Records |
|---|---|---|
| active | 5 | Portimão, Évora, Proença-a-Nova, Braga, São Jacinto |
| seasonal | 1 | Chaves (visiting operation, added by the check) |
| uncertain | 7 | Tancos, Vila Real, Cerval, Coimbra, Maia, Águeda (Casarão), Figueira dos Cavaleiros |
| closed | 0 | |
| missing coordinates | 0 | |

All 3 PT venues from `../dev-listings.json` (Évora, Portimão, Proença-a-Nova) are merged in, now
with coordinates.

Sources checked:
- FPPq dropzone page <https://www.fppq.pt/saltar/dz.html>: 7 visible dropzones. The Águeda, Maia
  and Figueira dos Cavaleiros entries are present but commented out in the HTML; they are
  recorded as uncertain.
- FPPq clubs page <https://www.fppq.pt/saltar/ace.html>.
- Operator sites: skydivealgarve.com, skydiveseven.pt (including the Skydive Lisboa page),
  skydiveportugal.pt, skydiveporto.com, skydivecerval.pt and skydivedunas.com.
- Other: skydivingsource.com Portugal list (7 entries), Diário de Aveiro (2025-12-04),
  visitportugal and Trip.com (Coimbra), and Instagram public views.

Open:
- FPPq lists several clubs with no airfield: Skydive Big Smile (Setúbal), Motivo Vertical /
  Vertical Extreme (Santo Antão do Tojal), Fly 4 Fun, Get High, SkySport, APQAL (Elvas) and others.
  Where they jump was not found. They probably use the listed dropzones.
- Azores and Madeira: no skydiving operation was found.
- Tancos and Vila Real need dated activity evidence, such as a club Facebook page.

## AD: Andorra (0 records)

No fixed-wing airfield exists (heliports only), and searches found no skydiving operation.
`AD.json` has an empty list and a note.

## GI: Gibraltar (0 records)

The only airfield is Gibraltar Airport (LXGB, RAF), and no civilian skydiving was found.
`GI.json` has an empty list and a note.

## Still to do

1. Re-run the OSM pass when Overpass has capacity. Query `sport=parachuting` and aerodromes whose
   name or operator mentions parachuting, inside the ES and PT country areas. Compare the results
   with the points above.
2. ~~Check the Barcelona-Bages landing point.~~ Resolved by the check (wrong comparison airfield).
3. Find dated 2025–2026 evidence for every "uncertain" record, mainly from Facebook pages.

## Check

Checked 2026-11-14 by a second claude pass (skeptical review). All 29 original records were
looked at; these were re-opened against sources, least certain first: Barcelona-Bages, Santa
Cilia, Trebujena, Chozas de Abajo, Ontur, Córdoba, El Berriel, Casas de los Pinos, Requena,
Braga, Vila Real, Tancos, Cerval, Coimbra, Maia, Águeda, Figueira dos Cavaleiros, plus the
FPPq page (re-read with its HTML comments).

How coordinates were checked:
- Every point was compared with the nearest OurAirports airfield: all are within 0.45 km
  of the stated airfield, in the stated country and town. None falls in the sea or in another town.
- OpenStreetMap: one Overpass query succeeded through the maps.mail.ru mirror (the others timed
  out or returned 504). It returned the `sport=parachuting` points in Iberia and the aerodromes
  around Bages. The OSM points for Saltamos/SkydiveBCN, Skydive Madrid (Lillo), Skydive Valladolid
  (Matilla), Skydive Maia, Skydive Algarve and Skydive Seven (Portimão) and Empuriabrava all lie
  within 0.4 km of the recorded points. A full OSM aerodrome comparison for every record timed out
  and is still open.

Changes made:
- **ES Barcelona-Bages (was `es-pla-de-bages`, now `es-barcelona-bages`):** the point was right,
  the name was wrong. Saltamos is at Aeròdrom Barcelona-Bages (OSM relation 20333619, icao LEMS;
  OurAirports LEMS "Manresa Airfield"), 0.2 km from the record. "Aeròdrom del Pla de Bages"
  (ES-0063, near Sallent) is a different airfield 2.6 km away, which explains the earlier 2.5 km
  "mismatch". Key renamed, `icao` set to LEMS, wrong alias removed. No other file used the old key.
- **ES Santa Cilia: uncertain to closed.** The Yumping page that the researcher cited says the
  Centro de Paracaidismo Pirineos is based in Jaca but jumps at Aérodrome de Lasclaveries, about
  18 km north of Pau, France (43.4274, -0.2888). The Santa Cilia airfield operators list gliding
  and sightseeing flights only. The "season" text had come from the Lasclaveries description and
  was removed. **For FR:** Lasclaveries should be in FR.json (Pau; probably the same field as
  "Paradise 64"); this check did not edit FR.json.
- **PT Chaves: added (`pt-chaves`, seasonal).** Skydive Porto (GoXtreme) sells tandems from Chaves
  aerodrome (LPCH) on Yumping, last updated 2026-09-23, with a verified review of a jump there
  dated 2026-06-06. A Skydive Portugal reel announcing jumps at Chaves on 19-20 September was seen
  only in search results. It is a visiting operation on announced weekends, not a resident
  dropzone, and is not on the FPPq page. Coordinates from OurAirports LPCH.
- **PT Braga: kept active, evidence replaced.** The old evidence misquoted Skydive Porto: its page
  says it jumps mainly at Proença-a-Nova and only occasionally at Braga. New evidence: APM ran a
  landing-accuracy round of the national competition at Braga aerodrome on 31 Oct-1 Nov 2026
  (public posts, search-result view).
- **ES Casas de los Pinos and El Berriel: kept active, stronger evidence.** Operator Instagram
  videos dated 8-9 Nov 2026 (Casas de los Pinos), and a 2026 iJump event booking plus 2026
  reseller listings naming El Berriel (GCLB).
- **ES Chozas de Abajo:** added a February 2026 Tripadvisor fraud complaint. Still uncertain.
- **PT Vila Real:** added a 2026-06-06 customer review saying there are no jumps in Vila Real.
  Still uncertain, and likely inactive.
- **PT Maia:** added the OSM point (agrees) and a search view describing it in the past tense.
  Still uncertain, probably closed.
- **PT Tancos:** noted that military parachuting continues there. Civilian club activity is still
  unconfirmed.
- **ES Ontur:** noted a "SkyDiveOntur" LinkedIn lead with undated posts. Still uncertain.

Checked with no change needed: Córdoba (operator says it has its own facilities at Córdoba
Airport, and the point is the LEBA reference point), Requena (Instagram posts dated 4-8 Nov 2026),
Trebujena (Tripadvisor still says permanently closed; left uncertain because that is
user-reported), Cerval (site live with a 2026 footer only; still uncertain), Coimbra (Trip.com
"temporarily closed"), and Águeda and Figueira dos Cavaleiros (FPPq entries commented out,
confirmed).

Duplicates: none. Each airfield appears once, and multi-operator airfields (La Juliana, El Berriel,
Portimão, Évora, Braga) are already merged.

Rejected in the completeness pass:
- DreamFly (OSM `sport=parachuting` at Sintra, PT) is an indoor wind tunnel.
- "Bassella experiences" (OSM `sport=parachuting`, Lleida, ES) has no confirmed jump operation;
  it is a lead only.
- Yumping "Guipúzcoa" (Centro de Paracaidismo Pau, Berastegui) jumps in Pau, France.
- Mallorca: only a tunnel and paratrike/paragliding operators were found.
- Associação de Paraquedistas do Nordeste (Bragança) is on the FPPq club list, but no airfield
  activity was found; it is a lead only.

Still open after the check:
- the full OSM comparison;
- dated evidence for Ontur, Cerval and Tancos;
- whether Trebujena's closure is confirmed;
- AD.json and GI.json keep a top-level `note` field that the README format does not define.
  It was left in place; the format owner should decide.


## Codex cross-check

Checked independently on 2026-11-14. Existing uncertain records and directory-only evidence were reviewed with operator pages, dated calendars/news and local-language searches. A failed page load or a copyright year was not treated as evidence of recent jumping. No login, contact, booking, Overpass query, commit or push was made.

Coordinate method: opened the [OurAirports airport dataset](https://davidmegginson.github.io/ourairports-data/airports.csv) and compared every existing non-null point with its named airfield, rather than replacing coordinates with the nearest airport indiscriminately. Airport reference points establish the airfield, not the exact parachute target. Off-airfield sites and unresolved points are described below. Counts supersede earlier sections; additions can remain uncertain when the place is confirmed but recent operation is not.

### Spain

- Ontur **uncertain → active**: [Club Aéreo Universal September 2025 bulletin](https://www.clubaereouniversal.com/gallery/2025%209%20SEP%20BOLETI%CC%81N%20MENSUAL%20DEL%20CAU.pdf), page 21, names Ontur as a school/booking location, corroborated by the [operator](https://skydivelamancha.com/). The bulletin's actual August-jump report is about Requena, so that distinction is retained in the record.
- Chozas **uncertain → closed**: [31 May 2026 reporting](https://www.diariodevalladolid.es/valladolid/260531/283127/lyf-aviation-dos-anos-estafas-saltos-anulados-paracaidas-valladolid-leon-dos-accidentes-aterrizaje.html) traces relocation to Valladolid and cessation. This closes the recorded jumping operation, not the airfield.
- Trebujena remains uncertain: [ENAIRE SUP 119/25](https://aip.enaire.es/recursos/descargas/SUP/LE_SUP_A_2025_119_es.html) imposed temporary closure through estimated July 2026. No superseding reopening notice or recent jump operation was established.
- Coordinates: all 17 existing points checked against airport data; none changed. Spanish completeness searches included Villamartín, Alhama and Casarrubios; no additional regular civilian DZ confirmed. Those leads, Lebrija/El Copero and any replacement operation at Trebujena remain open.

### Portugal

- Tancos **uncertain → active**: [O MIRANTE, 9 June 2026](https://omirante.pt/cultura-e-lazer/2026-06-09-boinas-verdes-de-tancos-continuam-a-ensinar-a-voar-e-a-guardar-a-memoria-dos-paraquedistas-909a5e93) describes the club's jumping and newcomers; [Skydive Cerval](https://www.skydivecerval.pt/) explicitly advertises Tancos as the jump zone. Added that operator at Tancos.
- Cerval stays uncertain: website address says Cerval but jumping heading says Tancos. Maia stays uncertain: reporting traces the old operator's move to Spain, without proving that every Maia operation ceased. Vila Real, Coimbra, Águeda and Figueira dos Cavaleiros had no verified 2025+ local jump programme in the Portuguese searches; all retain explicit uncertainty.
- Added **Rio Maior, seasonal**, a recurring precision-landing competition place, based on the [11 August 2026 announcement](https://noticiasdosorraia.sapo.pt/taca-de-portugal-de-paraquedismo-passa-para-novembro-em-rio-maior/). This is an annual sporting venue, not a daily commercial centre. Its exact training-field coordinates remain null; the town or sports-complex office is not a substitute.
- Coordinates: all 13 pre-existing airfield points checked, none changed. Portuguese completeness searches also found São Jacinto/Skydive Dunas and Proença, already present. Remaining gaps: actual current use of the six uncertain airfields and exact Rio Maior landing field. The NAV 2025 amendment PDF timed out; it was not used as decisive evidence.

### Result counts

| Country | Active | Seasonal | Uncertain | Closed | Added | Upgraded | Downgraded | Closed in check | Existing coordinates changed | Null coordinates |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ES | 12 | 0 | 1 | 4 | 0 | 1 | 0 | 1 | 0 | 0 |
| PT | 6 | 2 | 6 | 0 | 1 | 1 | 0 | 0 | 0 | 1 |

Validation: each country file passed `python3 -m json.tool`; unique keys, status values, source presence and paired coordinates checked. Countries with fewer than ten records were checked in full.

## Aggregator sweep

Codex, 2026-11-14. Compared physical places and aliases rather than counting directory brands. Opened Skydiving Source country tables, DropzoneFinder country listings and relevant detail pages, SKYDIVINGDOTCOM country lists, [Flight-1 host directory](https://www.flight-1.com/dropzones), and [Curlie Europe](https://www.curlie.org/en/Recreation/Aviation/Skydiving/Dropzones/Europe) and its relevant country subcategories. The old [dropzone.com Europe URL](https://www.dropzone.com/dropzones/europe/) redirected to an unrelated site; dropzones.eu failed DNS. [USPA locator](https://www.uspa.org/dzlocator) opened but returned no dropzone records in the static response, so its dynamic membership data was not reconciled. Wikipedia's general drop-zone page was blocked in the HTTP client; airport pages were used where available. Directory presence and a current year in a marketplace title were not treated as recent activity evidence. No Overpass queries, sign-ins, messages to operators, or commits.

### ES and PT reconciliation

Opened [Skydiving Source Spain](https://skydivingsource.com/locations/europe/spain/) (17 entries), [Portugal](https://skydivingsource.com/locations/europe/portugal/) (9), [DropzoneFinder Spain](https://dropzonefinder.com/dropzones/spain/) (24), [Portugal](https://dropzonefinder.com/dropzones/portugal/) (18), [SKYDIVINGDOTCOM Spain](https://skydiving.com/dropzone/location/spain/) (16), [Portugal](https://skydiving.com/dropzone/location/portugal/) (11), [Skydive World Portugal](https://www.skydiveworld.com/english/pol_slov.html), and Yumping provider pages for Espinho, Villamartín and Granada.

- ES added **3**, all uncertain: `es-villamartin` (SkyFarm, municipal 2022 opening and undated offer); `es-ventas-de-huelma` (Skydive Granada at Juan Espadafor, historical offer versus reported cessation); `es-alhama-de-murcia` (Campo de Vuelo, federation 2015 activity and 2017 closure notice). All have sourced coordinates. Later reviews labelled Skydive España cannot prove an Alhama reopening because some expressly describe Seville. Villamartín's airfield names La Antigua Estación and Tomás Fernández Espada refer to LETF.
- ES already covered: Empuriabrava, La Juliana/Skydive Spain/Atmósfera/Paraclub Sevilla, Lillo, Ocaña/Freefall University, El Pinar/Skytime/Skydive Castellón, Berriel/Gran Canaria/iJump, Requena, Totana, Ontur, Casas de los Pinos/Aerobalas, Mazaricos/Galsur, Bages/Saltamos/BCN, Córdoba, Santa Cilia/Pirineos, Trebujena/Jerez, Valladolid/Matilla, León/Chozas. [Blue Sky International](https://dropzonefinder.com/dropzones/spain/blue-sky-international-2) explicitly says it owns no dropzone.
- ES unresolved: [Skydive Murcia](https://dropzonefinder.com/dropzones/spain/skydive-murcia) has an old map near Los Alcázares but no named field, so cannot safely merge with Totana or add a San Javier record. [Velocidad Vertical](https://dropzonefinder.com/dropzones/spain/centro-de-paracaidismo-velocidad-vertical) has a Zaragoza-area marker, but the actual jump field remains unverified; a city club address is insufficient. Previous Casarrubios, Colmenar Viejo and Lebrija leads remain unresolved.
- PT added **3**, all uncertain: `pt-espinho` (LPIN; current AIP designation and 2026 booking listing conflict with special-event-only/closure statements), `pt-braganca` (LPBG; historical Galsur school), `pt-ponte-de-sor` (LPSO; municipal 2006 resident-school agreement for Sky Medley). All have sourced coordinates.
- PT already covered: Braga, Portimão/Algarve/Seven, Évora/Portugal/Vertical/Fly4Fun/A.C.E., Maia/Vilar de Luz, Coimbra/FlySkydive, Proença-a-Nova/SkyFunCenter, Figueira dos Cavaleiros/Skydive Europe, Vila Real and Tancos. SKYDIVINGDOTCOM's duplicate Fly4Fun entry is one Évora location; Queda Livre's Lisbon address is an office, not an additional field. Skydive World's Entroncamento label is Sky Medley's address, not its Ponte de Sor operating base.
- PT unresolved: Sky 4 Pombal has no confirmed operating airfield; Blue Emotions/Arruda dos Vinhos, Skysport Oeiras and Projecto Vertigem remain club/office leads without a verified separate jumping place. No extra record inferred from a generic town marker.
- Existing missing coordinate pairs filled: **0**. [DESMOR training-field page](https://desmor.pt/pt/instalacoes/relvados-apoio/campos-de-treino-26) confirms several distinct training pitches but supplies no point for the competition landing field; Rio Maior remains null. A stadium or office coordinate would be misleading.
- Final ES 20 = active 12, seasonal 0, uncertain 4, closed 4; PT 17 = active 6, seasonal 2, uncertain 9, closed 0. Missing coordinates: ES 0; PT 1.
