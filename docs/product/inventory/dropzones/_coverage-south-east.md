# Coverage: South-eastern Europe (GR, BG, RO, CY, TR)

Researched 2026-11-14 by claude. Development data only; see `README.md`.

Coordinates come from OpenStreetMap: one Overpass sweep (`sport=parachuting`, plus aerodromes whose name or
operator mentions parachuting) and a full `aeroway=aerodrome|airstrip` pull for the five countries. Nominatim
was used for Kingsfield after Overpass became overloaded. Two operators publish their own point (Skydive Athens,
Skydive Messolonghi; Skydive Bulgaria's map link), and those points are used where they agree with OSM. Two
records use the OurAirports CSV (`davidmegginson.github.io/ourairports-data/airports.csv`): RO Baia Mare (LRMM)
and RO Sibiu "Hermann Oberth". Four records have `null` coordinates because the airfield could not be
identified: RO Oradea, TR Erzincan, TR Etimesgut and TR Manavgat/Side. No coordinates were guessed.

Codex was not used: its MCP server failed to connect in this session.

Totals: 33 records. 20 active, 1 seasonal, 12 uncertain, 0 closed.

## Greece (GR): 6 records. 3 active, 3 uncertain

All five GR candidates from `../dev-listings.json` are merged in. Each record's `note` gives the old
dev-listings key. Chortero now has OSM coordinates. Megara's rounded point was replaced with the OSM node.

Sources checked:
- Operator sites: skydive-athens.gr, skydivemegara.gr (skydivegreece.gr redirects there),
  skydive-thessaloniki.gr, skydivemessolonghi.gr.
- Resellers and guides, used as leads: Manawa, Greeka, unlimited-adrenaline.gr (403), discover-greece-tours.
- Facebook (Skydive Thessaloniki): only the page title is visible without login, and no posts.
- Searches in Greek and English, including island searches (Crete, Rhodes, Kos, Corfu) and Larissa/Volos.
  No island dropzone was found. One guide says Greece has none.
- No list from a federation or aero club was found online. Neither an "Ελληνική Ομοσπονδία Αλεξιπτωτισμού"
  nor an aero club list of parachuting clubs turned up.

Status notes:
- **Active** (Kopaida, Megara, Chortero): the evidence is each operator's own current site, which gives a
  year-round schedule, a stated permanent base, or a current booking schedule. No dated 2025/2026 post was
  seen, so this is weaker evidence than a federation list.
- **Uncertain**:
  - Messolonghi: the site is live but shows no schedule.
  - Thiva/Perneri: only resellers mention it.
  - Polykastro/Nea Kavala: Hellenic Skydivers' old northern base, about one weekend a month. OurAirports
    marks the airfield closed.

Open:
- Check Instagram/Facebook for Skydive Messolonghi and Skydive Thessaloniki activity in 2025–2026.
- Find out whether Skydive Greece still flies at Perneri or Polykastro at all.
- "Ελληνική Λέσχη Ελεύθερης Πτώσης" (Hellenic Freefall Club) ran a school at Kopaida (accident report 2016,
  aaiasb.eu). Its current status is unknown.

## Bulgaria (BG): 4 records. 2 active, 2 uncertain

All three BG candidates from dev-listings are merged in, all now with coordinates.

Sources checked:
- Operator sites: skydivebulgaria.com, sko4i.bg, skyshumen.com.
- Capital.bg (2023) on Ihtiman.
- Resellers: makaroon.bg, adrenalin.bg, giftcometrue.
- Wikipedia: Primorsko Airfield.
- Searches in Bulgarian for "парашутен скок тандем летище", the federation and clubs. No federation member
  list was found online.

Status notes:
- Ihtiman is active: the operator publishes working hours (Wednesday–Sunday).
- Sapareva Banya is active: the operator page plus a reseller's "all year" listing.
- Shumen/Gradishte is uncertain: only the operator page, with no schedule.
- Primorsko is uncertain: only an undated travel guide mentions it, and no operator was found.

Open:
- Thaispa.bg (an SEO blog) claims tandems at Krumovo/Plovdiv. This is unconfirmed and was not recorded.
- Sko4i's office is in Lyaskovets (near Gorna Oryahovitsa). No jumps there were found.
- The Bulgarian Aeroclub (Ruse) does demo jumps at gliding events. No regular DZ was found.

## Romania (RO): 17 records. 13 active, 1 seasonal, 3 uncertain

Sources checked:
- Aeroclubul României (aeroclubulromaniei.ro): its list of 16 territorial aeroclubs, each club's course menu,
  and the "Aerodrom > Informatii" pages (name, ICAO, runway).
- aerodromclinceni.ro, tnt-brothers.ro, skydivetransilvania.ro, gojump.ro.
- learn-atc.com directory.
- News:
  - Pro TV (2025-04-07): about 800 parachuting trainees.
  - Cotidianul: Luncani marathon on 2025-08-15.
  - Puterea.ro: Tuzla, 2025-07-12.
- OSM operator tags (Luncani: Skydive Transilvania; Sânmihaiu German: Timisoara Skydiving Club; Dezmir: Cluj
  aeroclub).

Status notes:
- **Active**:
  - Clinceni and Luncani have dated or current evidence.
  - Eleven territorial aeroclubs (Arad, Baia Mare, Brașov, Cluj, Craiova, Deva, Iași, Pitești, Ploiești, Sibiu,
    Suceava) are marked active because the national aero club's current site lists a "Parasutism" course for
    each, and the national 2025 trainee report backs this. Caransebeș lists no parachuting and is excluded.
    This is a weaker, list-based status. No per-airfield dated jump was found for these.
- **Seasonal**: Tuzla (TNT Brothers' coastal base, with a jump incident on 2025-07-12).
- **Uncertain**:
  - Sânmihaiu German (GoJump): no dated activity, and a directory also names Șiria.
  - Târgu Mureș: the club site could not be opened.
  - Oradea: only a Facebook link, and the airfield is unknown.

Coordinate caveats:
- Iași uses OSM Iași-Sud (LRIS), based on an OSM operator tag. The club's own aerodrome page returned 404.
- Suceava uses Salcea airport (LRSV), based on the club address.
- Brașov uses Ghimbav. The club also runs Sânpetru (LRSP).

Open:
- Brăila/Ianca (LRIC) is a territorial club, but no parachuting is listed. Not recorded.
- Măgura/Cisnădie (LRCD) is tagged "skydiving" in OurAirports keywords. A search summary says tandems are flown
  there. Unconfirmed. Not recorded.
- Șiria / Charlie Bravo (LRCB, Arad County) is a possible GoJump site.
- Satu Mare: the Baia Mare club covers it. A 2025 local article mentions free courses with parachute jumps in
  the county, but the article could not be read.
- The CAA has a tandem directive (caa.ro), but no register of tandem operators was found.

## Cyprus (CY): 1 record. 1 active

Sources checked:
- British Skydiving "find a drop zone": Kingsfield, Xylotymbou.
- UK Charity Commission entry, seen in search results only (403): "Cyprus Combined Services Parachute Centre
  CIO", working name Skydive Cyprus, registered 2025-09-26.
- Ulysses Trust "Dragon Falling 2025": Army reservists' parachuting expedition in Cyprus, 12–21 Sept 2025. The
  site is not named.
- OSM via Nominatim and OurAirports (LCRE).

Notes:
- Kingsfield is in the Dhekelia UK Sovereign Base Area and is filed under CY.
- It is a military/combined-services centre. Whether civilians can jump there is unconfirmed:
  skydivecyprus.org had a TLS error, and the MOD AIP PDF did not download.
- No civilian DZ was found in the Republic of Cyprus. The Cyprus Parachute Association appears in 2026 news
  only for indoor skydiving.
- Northern Cyprus: only military demo jumps were found (Teknofest 2025, a record flag jump). No DZ.

## Türkiye (TR): 5 records. 1 active, 4 uncertain

Sources checked:
- THK-related news: Memurlar.net 2024-06-17 (parachute course sites Karain, Efes-Selçuk, Etimesgut Türkkuşu,
  Erzincan, June–September, static line from about 400 m) and TGRT/Haber7 2026 (THK Selçuk Efes school).
- Anadolu University notice (2026-10-21) listing THK centres.
- Yeni Asır 2026-10-21 (Skydive Efes).
- GoTürkiye adventure page.
- Resellers: Headout, Vigo Tours, Expedia, GowithGuide.
- OSM and OurAirports.
- Searches in Turkish for "uçaktan tandem paraşüt", Fethiye, İstanbul (Ormanlı, Şile, Hezarfen), Kayseri and
  Kapadokya.
- thk.org.tr could not be opened (expired certificate).

Status notes:
- Selçuk-Efes is active: two separate 2026 news items.
- Karain, Erzincan and Etimesgut are uncertain: they are THK course sites per a 2024 article, with no 2025+ jump
  evidence. Etimesgut and Erzincan have null coordinates because the landing site is unconfirmed.
- Manavgat/Side is uncertain, with null coordinates: resellers sell Alanya, Side, Antalya and Kemer tandems
  from "an airfield near the Manavgat River". Candidates are OurAirports TR-0159 "Manavgat Sport Aeroclub" and
  the OSM Ulualan forestry strip.

Open:
- **Fethiye**: the brief hinted at a private Fethiye DZ, but every search, in Turkish and English, found only
  paragliding from Babadağ to Ölüdeniz beach. Daily Sabah (2016) mentions skydivers at the Ölüdeniz air games,
  which is a festival, not a DZ. Not recorded. It needs a check of Instagram/Facebook for a "Skydive Fethiye"
  operator.
- İstanbul: GoTürkiye names Ormanlı (Çatalca) and Şile for "skydiving", but these appear to be paragliding
  sites. No DZ was found at Hezarfen (LTBW). Not recorded.
- THK İnönü (Eskişehir) is a THK aviation centre, mainly gliding. No parachuting was found.
- Kayseri is called "a prominent skydiving spot" by one travel blog. No evidence found.
- Kuşadası and Ephesus reseller products are treated as the Selçuk-Efes DZ.

## Check

Checked 2026-11-14 by a second claude pass (skeptical review). All 33 original records were looked at. Coordinates
were compared with the OurAirports CSV for every record (Overpass could not be reached during the check). Sources
were reopened for the least certain records.

Totals after the check: 35 records. 19 active, 2 seasonal, 14 uncertain, 0 closed. 4 have null coordinates.

Coordinates: every point lies at its named airfield and inside its country, within about 400 m of the OurAirports
entry. The exceptions are records with no OurAirports entry, and Kopaida and Sapareva Banya, which are within
300–350 m. No point is in the sea or in another town. No duplicate airfields were found.

Changes:
- **RO, from the national aero club's 2026 course notice** (ar.ro/articol/cursuri-gratuite-2026, posted
  2025-12-30). The notice lists the clubs that take parachuting students and the centres where school jumps
  happen:
  - **Iași-Sud, Sibiu and Cluj/Dezmir** go from active to **uncertain**. The notice says these clubs' school
    jumps take place at Suceava, Deva and Târgu Mureș.
  - **Pitești-Geamăna** goes from active to **uncertain**. Pitești is not in the 2026 parachuting list.
  - **Târgu Mureș** goes from uncertain to **active**. It is listed, and it is the jump centre for Cluj. Its
    club-site source wrongly said "'Parasutism' in its course menu" although the site never opened. That is
    corrected.
  - **Ianca (LRIC)** is **added** as active, on the same list-based standard as Arad and the others. Its
    coordinates come from OurAirports (LR79). It was not cross-checked in OSM.
  - Arad, Baia Mare, Brașov, Craiova, Deva, Ploiești and Suceava: the evidence is now the dated 2026 notice
    instead of the undated course menus. They stay active.
  - Oradea is not in the 2026 list and stays uncertain.
  - Clinceni stays active (aerodrome site, TNT Brothers). A note records that the București club's school
    jumps were moved to Ploiești in 2026.
  - Brașov: the airfield is still unconfirmed. The club gives addresses at both Sânpetru and Ghimbav, and its
    2025–2026 events are at Sânpetru. Ghimbav is now also Brașov-Ghimbav International (LRBV). A note says the
    point may be the wrong one of the two airfields.
- **RO Sânmihaiu German** goes from uncertain to **seasonal**. GoJump's own aerodrome page names **LRSG** at
  Sânmihaiu German and publishes hours of most weekends, April–October. The operator's reference point
  replaces the directory point; it is the same place, about 30 m away. The Șiria doubt is dropped.
- **GR Megara**: a second operator, **Skydive Attica**, is added. It says it is based at Pachi-Megara and posted
  a tandem video from Megara on 2025-12-16, seen in search results only.
- **TR Manavgat/Side** goes from uncertain with null coordinates to **active with coordinates**. The operator is
  **Manavgat Skydive** (manavgatskydive.com): "2026 open for booking", jumps from 10,000 ft. Its map link points
  to the "Manavgat Model Uçak Pisti" (36.748796, 31.479853), about 270 m from OurAirports TR-0159 "Manavgat
  Sport Aeroclub". A skydive.tr Instagram reel of 2025-12-28 shows tandems at Manavgat; it was seen in search
  results only. Whether skydive.tr is the same operator is unconfirmed.
- **TR Selçuk-Efes**: the Skydive Efes website (skydiveefes.com) and Instagram (parasutokuluefes) are added. Both
  were seen in search results only, because the site's TLS certificate has expired. The site title is "Skydive
  Efes - Türk Hava Kurumu", which suggests Skydive Efes is the THK school's public name.
- **TR Skydive Cappadocia** is **added** as uncertain with null coordinates. The operator site (footer 2025)
  calls it "Türkiye's first private dropzone", shows a general aviation operating licence and offers jumps all
  year. Its only address is an office in Ürgüp. No airfield or dated jump was found.

Checked and left unchanged:
- GR: Kopaida, Chortero, Thiva/Perneri (OurAirports GR-0010 agrees), Messolonghi (the operator site still has no
  schedule) and Polykastro (OurAirports says closed).
- BG: all four. Sapareva Banya stays active: the operator site is current, and resellers still sell jumps there
  in November 2026, though no dated jump was found. Sko4i's other sites (Draganovtsi, Erden, Ihtiman) are
  commented out on its site.
- CY: Kingsfield.
- TR: Karain, Erzincan and Etimesgut. A Bulgarian, a Greek and a Turkish search found no other DZ.

Still doubtful:
- Status that rests only on a current operator site and no dated post: GR Kopaida and Chortero, BG Sapareva Banya.
- Location: RO Brașov (Ghimbav or Sânpetru), and RO Ianca (coordinates from OurAirports only).
- Operators: TR skydive.tr, and whether Skydive Efes is the same operation as the THK school.
- Kingsfield: whether civilians can jump there.
