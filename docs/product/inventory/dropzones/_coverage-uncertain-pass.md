# Uncertain-record pass (2026-11-14)

Development data only. The owner asked whether every record is a real dropzone ("never heard of Nea Kavala"). All 178 records then marked `uncertain` were re-researched:

1. **Research (Codex, 9 Orca workers, one per country group).** Each record got a verdict from public sources opened that day, searching in the local language: active, seasonal, closed, not_a_dropzone, or still uncertain. Raw verdicts: `_uncertain-pass/<group>.json`.
2. **Adversarial check (Claude, one subagent per group).** Every verdict other than "uncertain", and every correction, was re-opened and challenged, and the checker searched independently. Absence of evidence was not accepted as closure, and resellers alone were not accepted as activity. Checks: `_uncertain-pass/<group>.check.json`.
3. **Applied.** The checker's final verdict wins where it disagreed with Codex. Codex verdicts left "uncertain" were not checked and change nothing beyond a dated re-check sentence in `status_evidence`. Corrections were applied only where the checker did not reject them. Applied list: `_uncertain-pass/_applied.json`.

**Result:** 16 promoted, 19 closed, 3 removed as not dropzones, 139 still uncertain, plus the decisions below. Codex and the checker disagreed on 16 records.

## Promoted

- at-trieben (Trieben Airfield): seasonal
- ch-bressaucourt (Bressaucourt Airfield): seasonal
- bg-erden (Erden Airfield): seasonal
- ro-sibiu (Sibiu "Hermann Oberth" Aeroclub Airfield): seasonal
- ba-bihac-golubic (Sportski aerodrom Golubić (Bihać)): seasonal
- si-lesce (Letališče Lesce-Bled): seasonal
- si-murska-sobota (Letališče Murska Sobota (Rakičan)): seasonal
- si-ptuj (Športno letališče Ptuj (Moškanjci)): seasonal
- si-sentvid-pri-sticni (Šentvid pri Stični airfield): seasonal
- pl-zamosc (Lotnisko Zamość-Mokre): seasonal
- de-bad-duerkheim (Bad Dürkheim airfield): seasonal
- de-burgheim (Burgheim airfield): seasonal
- fr-le-castellet (Aéroport du Castellet): seasonal
- fr-reims-prunay (Aérodrome de Reims-Prunay): seasonal
- pt-braganca (Aeródromo Municipal de Bragança): seasonal
- fi-pirkkala (Tampere-Pirkkala airport): active

## Closed

- gr-polykastro-nea-kavala (Nea Kavala Polykastro Airfield): closed
- ro-oradea (Oradea (Aeroclubul Teritorial "Smaranda Brăescu")): closed
- ua-chayka-kyiv (Aerodrom Chayka): closed
- ua-tsuniv-lviv (Aerodrom Tsuniv): closed
- de-breitscheid (Breitscheid airfield): closed
- de-finsterwalde-schacksdorf (Finsterwalde-Schacksdorf): closed
- de-schwaebisch-hall-weckrieden (Schwäbisch Hall-Weckrieden airfield): closed
- fr-annemasse (Aérodrome d’Annemasse): closed
- fr-le-blanc (Aérodrome du Blanc): closed
- pt-maia (Aeródromo de Vilar de Luz (Maia)): closed
- lv-jelgava (Jelgava former dropzone): closed
- se-skavsta (Skavsta airport historical dropzone): closed
- dk-ejstrupholm (Ejstrupholm dropzone): closed
- dk-sundbylille (Sundbylille historical dropzone): closed
- gb-chiltern-park (Chiltern Park Aerodrome): closed
- gb-lewknor (Lewknor former parachute landing area): closed
- gb-old-buckenham (Old Buckenham Airfield): closed
- gb-redlands (Redlands Airfield): closed
- gb-teesside (Teesside International Airport parachute site): closed

## Removed (not a dropzone)

- hu-tokol (Tököli repülőtér): The operator's site (2026 copyright) calls Tököl its company base and a future tandem location, and says jumps currently happen only at Nyíregyháza and Hajdúszoboszló. The Tököl airport rules (Ver 1.1, approved 23 Apr 2026) are stronger proof that no jumping happens there: the LHSDZLHTL drop zone airspace is 'designated but inactive', and the active-drop-zone procedures are marked N/A. Caveat: undated Fly Jump social bios list Tököl as a jump location, and the drop zone airspace is published, so the place should be rechecked if that airspace becomes active.
- fr-lapalisse-perigny (Aérodrome de Lapalisse-Périgny): CAE Aviation's live page describes its Lapalisse centre as dedicated to military parachutists, with 'Accès réservé aux armées et organisations d'état uniquement'. The page was last modified in September 2022, so 'high' confidence is generous. Still, no civilian offer dated 2025 or later was found: the civilian tandem listings are undated legacy directory entries, and Lapalisse is not on the FFP structure list.
- gb-south-cerney (South Cerney Airfield): Added on the coordinator's follow-up. South Cerney is the Army's Duke of Gloucester Barracks, and RAF Brize Norton publishes it as the 'South Cerney Drop Zone' for scheduled military local training sorties (November 2026 schedule). The resident team, the RLC Silver Stars, is an Army display team for Regular and Reserve RLC personnel. A stakeholder response in a CAA airspace-change consultation says resident parachuting no longer takes place and any activity is rare and NOTAM-covered. British Skydiving lists no club here, though it does list military clubs that take civilians elsewhere (APA Netheravon, RAFSPA Weston-on-the-Green). The only civilian jumping found is a 2008 Red Devils / Click and Jump tandem day, so I treat it as a military-only drop zone. The main risk is that this partly rests on absence: I found no explicit 'military only' statement, only no civilian route.

## Coordinator decisions

- at-lienz-nikolsdorf: checker seasonal -> uncertain. Airgasmo's 2026 schedule lists two Lienz weekends (27-28 Jun, 12-13 Sep 2026), but nothing shows either took place; kept uncertain, like ba-visoko (a schedule or offer alone is not proof of jumps).
- nl-baarn: merged into nl-hilversum as its fallback landing area (alias and note).
- de-untermuenkheim-brachbach: new uncertain lead (Blue Sky Adventures, EDTY take-off); removed from Weckrieden's operators.

## Where the checker changed Codex's verdict

- at-lienz-nikolsdorf: Codex uncertain -> checked seasonal. Airgasmo's 'Lienz' is this airfield: the 'Flugplatz Lienz' pin on its own dropzone map (46.80032, 12.87523) lies inside the OSM outline of LOKL, and its Lienz ticket is listed at 'lienz-nikolsdorf', location Lengberg, the airfield's postal address. Its 2026 schedule, a published season calendar that the README accepts, lists jumps there on 27–28 Jun and 12–13 Sep 2026; take-off is the 500 m runway 12/30 and the AIP lists parachuting as an admitted activity. No source states the landing area, and I found no post, review or airfield notice showing either weekend took place: the Lienz ticket has 0 reviews (Airgasmo's Trieben ticket has 132) and the airfield site does not mention parachuting, so this is a two-weekend site whose seasonal status rests on the schedule alone. The recorded operator (Fallschirmzentrum Kärnten) no longer lists the site, and the coordinates match the AIP reference point within about 30 m.
- at-trieben: Codex active -> checked seasonal. Codex's evidence does not show jumps at Trieben. The ÖAeC register (issued 3 Feb 2026) only records that Internationaler Pink Parachute Club holds a school authorisation with LOGI as its training site, and no Pink Skyvan schedule from Jan 2025 to Nov 2026 lists Trieben (13 archived versions checked, plus the live page). The jumps are run by Airgasmo, the airfield's listed parachute operator in 2024. Its own 2026 'Wann und Wo' schedule lists nine Trieben weekends from 14–17 May to 3–4 Oct 2026, its 16 Jun 2026 Instagram reel is tagged #trieben, and customer reviews dated 27 Jun 2025 and 2 Jul 2026 name Trieben as the jump site. That is weekend operation in season, which AT.json records as seasonal; the recorded coordinates are within about 50 m of the OSM aerodrome.
- ch-le-chable-verbier: Codex active -> checked uncertain. Alpskydive offers helicopter tandem skydives, not paragliding. But no source names its heliport, exit area or landing area. Its site has no dated content and does not mention the aircraft training Codex cites. Its booking page shows no sessions, it is not on Swiss Skydive's school/club list, and its last own Instagram post visible without login is dated 14 Nov 2024. The 7 May 2026 Verbier Tourisme entry is a directory listing with a generic 'Toute l'année, 09:00–17:00 daily, horaires non garantis' field. Customer reels tagging @alpskydive, dated 2 Feb 2025 and 16 Dec 2025 (the second also tags @verbier), suggest the business operated in 2025. They do not show regular jumps at an identified place, and nothing supports the 'year-round' season correction.
- ba-visoko: Codex seasonal -> checked uncertain. The only evidence is one Slobodan Pad booking page offering tandems at Visoko airfield on 28-31 May 2026 from its Cessna 182 9A-DTD. No report shows the jumps took place, and no earlier or later jump days there were found in Bosnian or Croatian searches. Under the recurrence rule, a single visiting event does not make the place seasonal.
- si-lesce: Codex active -> checked seasonal. The only dated 2025+ jumping found at Lesce is the annual Skydive World Cup accuracy meet (36th edition, 26-28 June 2026, ALC aircraft plus a Slovenian Army aircraft; the 37th is announced for next year). The ALC parachute-section news category holds only a 2026 result from Slovakia and a 2024 display jump, and its student-course page is marked as a test page, so regular jumping outside the meet is not shown. This inventory classes recurring single-meet sites (e.g. Thalgau, Olomouc) as seasonal.
- si-murska-sobota: Codex active -> checked seasonal. All dated jumping at Rakičan comes from a visiting Austrian club (HSV Red Bull Salzburg) holding a spring training camp: 30 Apr-4 May 2025, which the press called an internal event, and again around 30 Apr-1 May 2026 with a Pilatus PC-6. The resident aeroclub's statement that it runs jumps, tandems and student training carries no date. So jumps recur each year, but regular or public operation is not shown.
- si-ptuj: Codex active -> checked seasonal. Dated evidence is the yearly Ptuj parachuting cup at Moškanjci (45th on 17-18 Aug 2024; 46th on 14-15 Jun 2025, held with five teams) and tandems at the club open day on 6 Sep 2025. The club's Cessna 206 tandem offer has no dates, and an independent tandem pilot books Moškanjci only on request; no 2026 jump date was found. That is recurring club and event jumping, which this inventory classes as seasonal, not a regularly operating dropzone.
- pl-zamosc: Codex active -> checked seasonal. Promoting the place to operating is supported. PKBWL records a parachute accident at EPZA on 30 Aug 2025 (PD Navigator 280 canopy, serious injury), so an aircraft jump was made there in 2025. The ULC register dated 22 May 2026 lists Aeroklub Ziemi Zamojskiej's parachute training (PJ to D, instructor) at EPZA, and the club's current product page and Instagram bio sell tandems from EPZA. 'Seasonal' fits better than 'active': the club's posts tie jumping to the spring season, nothing shows winter jumping, and the PL file labels similar aero clubs 'seasonal'.
- de-bad-duerkheim: Codex active -> checked seasonal. Aircraft jumping at EDRF from 2025 is confirmed: a solo jumper left a Cessna at about 3,000 m over the In den Almen field on Saturday 2025-08-30 (police/dpa), and the club's 13–14 June 2026 airfield festival programme lists tandem jumps. All dated jumps fall in June–September and Skyhopping (which names Bad Dürkheim as its recommended site) publishes no dates, so nothing supports 'active' (all-year); Codex inferred it from an absence of weekend restrictions.
- fr-charleville-mezieres-belval: Codex active -> checked uncertain. The 21 October 2025 Ardennes Développement article only lists parachuting in a generic list of leisure uses at the airfield. It names no operator and gives no jump dates. Press of May 2024 reports no parachute jumps at Belval since summer 2023 and the last operator unreachable, and a reseller marks the Charleville jump 'no longer offered'. No resumption in 2025 or later was found.
- fr-dinan-trelivan: Codex active -> checked uncertain. The FEPP map popup for Aero Tandem Celtic (Dinan) is undated marketing text. The operator's Dinan product page says Dinan dates are the days marked navy blue on its calendar (about one a month). The 2026 planning PDF has a navy 'TARIF DINAN' legend but no navy-marked day from April to October 2026; every session shown is Vannes. No dated jump at Dinan in 2025 or later was found.
- fr-le-blanc: Codex active -> checked closed. The school's own homepage still says it halted activity in 2023 and could not give a 2024 reopening date; its events calendar is empty. The Le Blanc municipal sports office page dated 24 September 2026 lists the school as 'Association en sommeil' (dormant). The FFP listing of school 3601 and an AIP mention are standing records, not proof of jumping. The only jumps traced since are military and state free-fall training on 11–14 November 2024. This is a dormant closure; a reopening is possible.
- fr-marennes: Codex active -> checked uncertain. The FEPP popup mentions Marennes as a secondary activity, but it is undated and its marker sits at Rochefort, not Marennes. Big Air's own site puts its dropzone at Rochefort airport and uses Marennes only as a scenic reference, and its 2026 planning PDFs do not mention Marennes. The 2026 Oléron–Marennes tourism listing sends customers to Rochefort airport at Saint-Agnant, '20 minutes de Marennes'. No jump at Marennes airfield in 2025 or later was found.
- fr-reims-prunay: Codex active -> checked seasonal. This is a label-only disagreement: operation is confirmed, more firmly than Codex's sources show. The operator sells a 'Saut flash' on 3–4 October 2026 at Reims Prunay, billed as the last weekend of the season, and its Instagram posts from August–September 2026 show the 2026 season. Because the season is bounded, 'seasonal' fits the file's convention. The cited Le Bonbon article (20 August 2025) says '20 minutes de Reims' but does not name Prunay.
- se-skavsta: Codex uncertain -> checked closed. The operator's own Instagram post, dated 12 February 2024 (decoded from the post ID, matching the date on the profile grid), announces the decision to shut down Nyköpings Fallskärmsklubb because operations can no longer continue. The same text appears on its Facebook page. The current SFF list has no club in Nyköping or Södermanland, and searches found no other operator jumping at Skavsta. The historical-operator correction is right: nyfk.se was the club's domain (info@nyfk.se, nyfk.se/tandemhopp), though it now serves only a self-signed certificate.
- gb-south-cerney: Codex uncertain -> checked not_a_dropzone. Added on the coordinator's follow-up. South Cerney is the Army's Duke of Gloucester Barracks, and RAF Brize Norton publishes it as the 'South Cerney Drop Zone' for scheduled military local training sorties (November 2026 schedule). The resident team, the RLC Silver Stars, is an Army display team for Regular and Reserve RLC personnel. A stakeholder response in a CAA airspace-change consultation says resident parachuting no longer takes place and any activity is rare and NOTAM-covered. British Skydiving lists no club here, though it does list military clubs that take civilians elsewhere (APA Netheravon, RAFSPA Weston-on-the-Green). The only civilian jumping found is a 2008 Red Devils / Click and Jump tandem day, so I treat it as a military-only drop zone. The main risk is that this partly rests on absence: I found no explicit 'military only' statement, only no civilian route.

## Worth re-checking later

- `gr-polykastro-nea-kavala`: closed since the 2016 camp; the runway has been freed and leased for reopening, restoration pending (club page, July 2025).
- `bg-erden`: seasonal on September 2025 alone; the 2026 national events moved elsewhere.
- `hu-tokol`: removed because its drop-zone airspace is designated but inactive (airport rules, April 2026); re-add if it becomes active.
- `at-lienz-nikolsdorf`: Airgasmo scheduled two 2026 weekends; no proof they took place.
- `gb-errol`: still in the UK AIP (Wed–Sun) with no operator named; latest operator evidence is from 2023.
- `de-untermuenkheim-brachbach`: new lead; 2026 dates seen only in a search snippet.
- `dk-ronne`: club website gone (fkr.dk shows a placeholder); public Facebook page used instead.
