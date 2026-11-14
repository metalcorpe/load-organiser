# France coverage — 2026-11-14

Researcher: codex. Scope: metropolitan France and Corsica, using FR; overseas territories with separate ISO country codes were excluded from this European inventory. This is a broad, deduplicated development inventory, not a claim that every historical lead is an operating dropzone.

## Counts

| Country | Active | Seasonal | Uncertain | Closed | Total | Without coordinates |
|---|---:|---:|---:|---:|---:|---:|
| FR | 45 | 19 | 43 | 3 | 110 | 5 |

The 64 active/seasonal records have federation or dated season/activity evidence. Active means current listed operation, not necessarily year-round or daily availability. Uncertain records preserve candidate or historical sites without implying confirmed present-day jumping; this explains why the total exceeds the expected count of operating centres. Three closed records concern parachuting operations, not necessarily closure of the airport.

## Sources checked and reconciliation

- [FFP school map](https://www.ffp.asso.fr/ou-pratiquer/), [all FFP structures](https://www.ffp.asso.fr/ou-pratiquer/liste-de-toutes-les-structures-ffp/), individual school pages, and [FFP announcement of 24 November 2025 promoting the map for 2026](https://www.ffp.asso.fr/en/envie-de-decouvrir-le-parachutisme/). The map contained 49 school entries, including overseas entries and several schools at Tallard. Individual schools were merged by actual airfield. Administrative addresses such as Gimouille, Bitche and Béthune were not used as separate dropzones or coordinate sources.
- [FEPP places to jump](https://www.fepp.aero/ou-pratiquer): cross-checked independent tandem operators and itinerant seasonal bases. Excluded tunnels and overseas entries, and did not use approximate map markers that can represent offices. The Tours operator now identifies Sorigny; the older federation label is not sufficient to place it at Tours airport.
- [Parachutisme France](https://parachutisme-france.fr/) individual zone pages supplied a broad metropolitan lead set. Each incorporated zone URL is recorded in FR.json. Their 2026 verification labels alone were not accepted as proof of current jumping. Directory providers may include intermediaries; uncertain entries need operator/aircraft responsibility confirmed before production use.
- [ExtrmSport France directory](https://app.extrmsport.com/skydive/dropzone/country/fr/): reviewed its 78 entries for additional historical fields, duplicates, camps and non-French or indoor entries. Individual unresolved entries were opened. Historical directory operators are not assumed still trading.
- [Skydiving.com France directory](https://skydiving.com/dropzone/location/france/): additional checks for FL140, Air65, historical locations and duplicate operators. Old dropzone.com links were encountered in directory entries; its successor France directory at https://skydiveforum.com/dropzones/europe/france/ could not be reliably retrieved, so this angle remains incomplete.
- [Wikipedia list of French airports](https://fr.wikipedia.org/wiki/Liste_des_a%C3%A9rodromes_et_a%C3%A9roports_en_France) and local-language searches helped reconcile airport names and codes. Coordinates came from individually opened [OurAirports airport pages](https://ourairports.com/), whose exact per-airport URLs are recorded. They describe airfield reference locations, not exact landing targets. The airport title and locality were compared with the intended site. No office-map marker was converted into a landing-area location.
- OpenStreetMap Overpass was attempted twice at https://overpass-api.de/api/interpreter with a metropolitan bounding-box sport=parachuting query (POST and GET); both attempts returned HTTP 406. No coordinates were invented from this unsuccessful query. A full OSM/aerodrome-club reconciliation remains open.
- Operator sites and calendars: Auvergne Parachutisme 2026 planning (including Clermont and Roanne); Kemp'Air 2026 Quimper news; Accel'Air 2026 Millau and Nîmes reopening news; Mike Air's May 2026 La Tranche resumption; Tandemotion 2026 calendar and post-accident resumption notice; Aero Tandem Celtic 2026 calendar; Tours'N Jump booking calendar; XLR Soulac season; Calais club 2026 weekends; 2Dive and regional tourism 2026 season; Corse Orientale 2026 Ghisonaccia season; Lessay tourism 2026 season. Exact supporting URLs are attached to records.
- Other primary checks included Parachutisme Occitan's five bases, Entre Ciel et Terre, Chute Libre Dordogne, Dragon Fly, Air Parachutisme (now Reims-Prunay), Sky Delivery, AirPlay, Dijon Parachutisme, Frétoy and Maubeuge. An undated live booking page by itself was kept insufficient to establish a dated operating season.
- Public Facebook (Para Groupe Jean Bart) and Instagram (Accel'Air) views were attempted but could not be retrieved in the browser tool. No login was attempted and no social-media activity claim relies on those failed fetches. Frétoy's public operator site embeds a review describing an October 2026 jump; it is supplementary to federation evidence, not an independently verified incident record.

## Important distinctions and open leads

- Five sites have null coordinates because a usable airport/operator-map coordinate was not verified: Bellême, Bouloc-en-Quercy, Frétoy-le-Château, La Tranche-sur-Mer and Sissonne. Obtain an official map/AIP or successful OSM result before plotting them. Bellême's LF6152 identifier is a ULM platform identifier, not an ICAO code.
- Nancy-Tomblaine appears in Tandemotion's 2026 calendar, but the current zones page omits it. The operator states that activity resumed after its June 2026 suspension; site-specific Nancy resumption is unresolved, so Nancy remains uncertain while Chambley and Épinal have current zone listings as well.
- Frétoy had a temporary-closure lead in May 2026; its live FFP entry, current operator site and later embedded October jump review support current listing but do not establish uninterrupted operation. Maubeuge has an explicit February 2026 reopening announcement.
- Sky Delivery indicates unresolved arrangements at Haguenau and Vesoul. Its Saint-Dié and Wissembourg leads need exact French airfield and current-operation confirmation; Wissembourg can refer to nearby Schweighofen in Germany. No guessed French record was created for that ambiguity.
- Historical Laon/Chambry and Dunkerque/Les Moëres are retained uncertain; the corresponding operators now advertise Reims-Prunay and Calais-Marck. Le Blanc remains a federation/historical lead; the school domain did not provide trustworthy current operating information. Annemasse, Lapalisse, Bellême and Sissonne need current civilian-operation evidence.
- Additional unlocated/weak leads: AAE Saint-Nazaire (office/provider versus actual aircraft base), 321 Chute Libre, Airboss and Airmoves camp listings, former FL140 Rhône-Alpes/Saint-Yan references, and Abbeville mentioned in an Olivair regional article. These did not establish a sufficiently clear regular current operating location to add a new site. FL140 at Saint-Laurent-Médoc and Air65 at Castelnau-Magnoac are already retained uncertain.
- Montpellier-Candillargues has a directory place entry but no identified current operator. La Baule, Dinan, Quiberon, Dijon, Aubenas, Marennes, Reims and other undated operator listings still need a dated site-specific calendar. Broader regional marketing pages were not treated as new dropzones.
- The three closed entries are La Rochelle (operator closure notice), La Ferté-Gaucher (historical closure described in a 2026 page) and Amiens-Glisy (2026 report of no regular jumping). Review these secondary historical claims before presenting definitive closure dates in a production app.
- Active/seasonal status may not mean the operator owns its aircraft: leases and shared aircraft are possible. Provider identity at uncertain directory-only sites is provisional. No reseller office was intentionally included as a separate place; the underlying airfield is the record unit.

## Uncertain records needing follow-up

| Key | Reason / next check |
|---|---|
| fr-albi-le-sequestre | Directory identifies a jump site (verification date 18 août 2026); recent operation not yet corroborated by a federation or operator calendar. |
| fr-annemasse | Historical school listing remains; no 2025-or-later regular parachuting operation or successor verified. |
| fr-aubenas-lanas | Operator describes May–October operation at Aubenas, but no 2025-or-later season evidence was verified. |
| fr-belleme | Historical directory lists parachute drops from this ULM base; no recent operating confirmation found. |
| fr-breville-sur-mer-granville | Directory identifies a jump site (verification date 23 août 2026); recent operation not yet corroborated by a federation or operator calendar. |
| fr-castelnau-magnoac | Directory identifies Air 65 at the airfield; recent operator calendar not verified. |
| fr-castelsarrasin-moissac | Directory identifies a jump site (verification date 18 août 2026); recent operation not yet corroborated by a federation or operator calendar. |
| fr-castres-mazamet | Directory identifies a jump site (verification date 19 septembre 2026); recent operation not yet corroborated by a federation or operator calendar. |
| fr-cazeres-palaminy | Directory identifies a jump site (verification date 18 août 2026); recent operation not yet corroborated by a federation or operator calendar. |
| fr-colmar-houssen | Directory identifies a jump site (verification date 23 août 2026); recent operation not yet corroborated by a federation or operator calendar. |
| fr-dijon-longvic | Operator calendar lists April–September weekends, but the visible calendar does not state its year. |
| fr-dinan-trelivan | Operator offers Dinan jumps but its 2026 PDF mainly labels Vannes; specific Dinan dates require confirmation. |
| fr-dunkerque-les-moeres | Older directory places the club at Les Moëres, whereas the operator’s 2026 calendar names Calais-Marck; continuation here unverified. |
| fr-fayence-tourrettes | Operator gives this airfield as a jump meeting point; dated operation and aircraft-operating responsibility require confirmation. |
| fr-haguenau | Operator marks Haguenau as pending; do not treat as an operational dropzone without confirmation. |
| fr-herret-condom | Directory identifies a jump site (verification date 18 août 2026); recent operation not yet corroborated by a federation or operator calendar. |
| fr-la-baule-escoublac | Operator identifies this as one of its two airfields; dated site-specific 2026 jump calendar not verified. |
| fr-la-llagonne-la-quillane | Directory identifies a jump site (verification date 18 août 2026); recent operation not yet corroborated by a federation or operator calendar. |
| fr-la-roche-sur-yon-les-ajoncs | Directory identifies a jump site (verification date 23 août 2026); recent operation not yet corroborated by a federation or operator calendar. |
| fr-laon-chambry | Historical directory links the Laon parachuting school; recent regular civilian jumping unverified. |
| fr-lapalisse-perigny | Historical directory identifies aircraft jumping at Lapalisse; no recent operating confirmation found. |
| fr-le-blanc | FFP lists the school; its own website returned unrelated defacement content, so recent jump operations remain unconfirmed. |
| fr-le-havre-octeville | Directory identifies a jump site (verification date 23 août 2026); recent operation not yet corroborated by a federation or operator calendar. |
| fr-le-val-saint-pere-mont-saint-michel | Directory identifies a jump site (verification date 23 août 2026); recent operation not yet corroborated by a federation or operator calendar. |
| fr-les-sables-d-olonne-talmont-aerodrome-de-la-lande | Directory identifies a jump site (verification date 23 août 2026); recent operation not yet corroborated by a federation or operator calendar. |
| fr-lons-le-saunier-courlaoux | Directory identifies a jump site (verification date 23 août 2026); recent operation not yet corroborated by a federation or operator calendar. |
| fr-marennes | FEPP describes Marennes as the operator’s secondary base; dated operation at this particular field remains unverified. |
| fr-montargis-vimory | FEPP professional-centre directory lists Vimory; dated operation not verified. |
| fr-montpellier-candillargues | Directory identifies a jump site (verification date 18 août 2026); recent operation not yet corroborated by a federation or operator calendar. |
| fr-mortagne-au-perche | Directory identifies a jump site (verification date 23 août 2026); recent operation not yet corroborated by a federation or operator calendar. |
| fr-nancy-essey | Listed in the 2026 calendar, but the current zones page omits Nancy after the 28 June 2026 accident; site-specific resumption not confirmed. |
| fr-quiberon | Operator identifies regular tandem jumps here; dated 2026 jump calendar still needs corroboration. |
| fr-reims-prunay | Current operator website sells jumps at Reims-Prunay; no dated season or recent activity post verified. |
| fr-revel-montgey | Directory identifies a jump site (verification date 24 août 2026); recent operation not yet corroborated by a federation or operator calendar. |
| fr-rodez-marcillac | Operator identifies a Rodez Aveyron jump base; dated operation not verified. |
| fr-saint-girons-antichan | Directory identifies a jump site (verification date 18 août 2026); recent operation not yet corroborated by a federation or operator calendar. |
| fr-saint-laurent-medoc | Directory identifies the airfield; recent operator calendar not verified. |
| fr-sarlat-domme | Operator identifies this jump base and offers booking; visible calendar did not provide dated activity. |
| fr-sissonne | Historical directory lists Sissonne and flags an operator website issue; present civilian access and regular operation unverified. |
| fr-tournus-cuisery | Directory identifies a jump site (verification date 23 août 2026); recent operation not yet corroborated by a federation or operator calendar. |
| fr-vesoul-frotey | Operator states activity near Vesoul is awaiting removal of an administrative blockage. |
| fr-vichy-charmeil | Directory identifies a jump site (verification date 23 août 2026); recent operation not yet corroborated by a federation or operator calendar. |
| fr-villefranche-de-rouergue | Directory identifies a jump site (verification date 18 août 2026); recent operation not yet corroborated by a federation or operator calendar. |

## Validation

`python3 -m json.tool docs/product/inventory/dropzones/FR.json > /dev/null` passed. Additional checks passed for required fields, unique place keys and ICAO identifiers, valid status values, source dates, paired coordinates, coordinate-source membership in sources, plausible metropolitan France bounds, and explanations for all null coordinates. These are structural and geographic plausibility checks; they do not substitute for the unresolved field-operation confirmations above. No temporary research files were retained.


## Follow-up — 2026-11-14

The counts above describe the initial snapshot. Rechecked all 43 initially uncertain records using operator calendars and booking pages, regional and municipal 2025–2026 publications, public social pages, and historical records for conflicting locations. No sign-in, messages or bookings were made. Search-result dates were not treated as dated activity when the opened page showed older material.

Current total: **110 records: 52 active, 37 seasonal, 18 uncertain, 3 closed; 1 without coordinates.** Of the 43 reviewed records, 18 seasonal, 7 active, 18 uncertain. No additional closure was inferred solely from a corporate liquidation or an old closure where a successor might exist.

### Status review

| Place key (without fr-) | Result | Evidence or remaining gap |
|---|---|---|
| albi-le-sequestre | seasonal | Operator publishes its 2027 season calendar and describes winter closure; this is an advertised future season, not evidence that future jumps have occurred. [Source](https://albi-parachutisme.fr/saut-en-parachute-toulouse/). |
| annemasse | uncertain | Registry updated July 2026 marks Parachutisme 74 and its Annemasse establishment closed in August 2024; no 2025-or-later successor jump operation was verified. [Source](https://www.pappers.fr/entreprise/parachutisme-74-412481954). |
| aubenas-lanas | seasonal | Regional tourism entry updated 10 October 2025 gives opening from 25 April to 25 October 2026 at Lanas. [Source](https://www.inauvergnerhonealpes.com/en/files/dragon-fly/). |
| belleme | uncertain | Survol du Perche describes aviation services and pilot qualifications, but no dated 2025-or-later regular skydiving schedule was found. [Source](https://www.survolduperche.fr/qui-sommes-nous). |
| breville-sur-mer-granville | seasonal | Operator news dated 22 November 2025 announces reopening on 3 April 2026; another announcement is dated 8 November 2026. [Source](https://www.parachutisme.pro/). |
| castelnau-magnoac | uncertain | Judicial asset-sale notice dated 30 June 2026 concerns Air 65 and its Pilatus; no successor operation or dated current jump schedule was verified. [Source](https://repreneurs.com/ao-735-avion-pilatus). |
| castelsarrasin-moissac | active | Operator presentation explicitly describes its management in 2026, names this airfield among its five operating bases and states ownership of its Cessna 182; individual session dates are not established. [Source](https://parachutismeoccitan.com/qui-sommes-nous/). |
| castres-mazamet | active | Castres-Mazamet official 2025–2026 student guide, page 23, identifies Chutextrem jump locations at Castres and Revel; the operator also offers both locations on its current website. [Source](https://www.castres-mazamet.fr/sites/castres-mazamet.fr/www.castres-mazamet.fr/files/images-joined-files/Guide%20etudiant%202025-2026%20bd.pdf). |
| cazeres-palaminy | active | Operator presentation explicitly describes its management in 2026, names this airfield among its five operating bases and states ownership of its Cessna 182; individual session dates are not established. [Source](https://parachutismeoccitan.com/qui-sommes-nous/). |
| colmar-houssen | seasonal | Booking listing updated 14 October 2026 records bookings since October 2025 for Alsace Parachutisme at Colmar; Colmar tourism describes May–October weekend operation. [Source](https://www.yumping.com/en/skydiving/alsace-parachutisme--e19681932). |
| dijon-longvic | seasonal | Booking listing updated 30 July 2026 reports bookings since August 2025 for Dijon Parachutisme; operator calendar lists selected spring and summer weekends. [Source](https://www.yumping.com/fr/parachutisme/dijon-parachutisme--e19866233). |
| dinan-trelivan | uncertain | Operator calendar research did not establish 2025-or-later Dinan sessions; dated schedules found concerned other airfields. [Source](https://www.saut-parachute-bretagne.com/calendrier/). |
| dunkerque-les-moeres | uncertain | Para Groupe Jean Bart publishes 2026 jump sessions but identifies its base as Calais-Marck; current jumping at Dunkerque-Les Moëres remains unverified. [Source](https://parachutismenord.wixsite.com/dunkerque/club). |
| fayence-tourrettes | seasonal | Operator booking page advertises Fayence jump sessions on 15–17 May, 7–9 August and 20–22 August 2027. [Source](https://airplayparachutisme.fr/produit/saut-en-parachute-tandem-fayence/). |
| haguenau | uncertain | Operator zone page describes Haguenau as awaiting availability; no dated 2025-or-later confirmed sessions at this field were found. [Source](https://sky-delivery.fr/zones-de-saut/). |
| herret-condom | active | Occitanie tourism listing gives 1 January–31 December 2026 opening for Parachutisme Occitan at the Herret aerodrome; operator also identifies this base in its 2026 presentation. [Source](https://www.tourisme-occitanie.com/fr/fiche/activite/parachutisme-occitan-condom_TFOSITRA2_ACT_7560583/). |
| la-baule-escoublac | seasonal | Operator publishes a 2026–2027 flight calendar explicitly covering La Baule and Quiberon, with separate site and closure legends. [Source](https://www.entrecieletterre.com/planning/). |
| la-llagonne-la-quillane | uncertain | Operator website was checked, but no 2025-or-later calendar tied specifically to civilian jumps at La Quillane was verified. [Source](https://pyrenees-parachutisme.com/). |
| la-roche-sur-yon-les-ajoncs | seasonal | Booking page identifies the Ajoncs airfield and April–October season, with customer jump reviews dated 13 July, 9 August and 8 September 2026; these are published customer reports. [Source](https://www.sport-decouverte.com/saut-parachute-la-roche-sur-yon.html). |
| laon-chambry | uncertain | Historical parliamentary evidence records CERPP closure in 2000; no dated 2025-or-later reopening or current civilian jump schedule at Laon was verified. [Source](https://www.senat.fr/questions/base/2000/qSEQ00020714S.html). |
| lapalisse-perigny | uncertain | Follow-up searches did not establish a dated 2025-or-later civilian club calendar; parachuting airspace notices alone do not establish civilian access. See existing directory sources in FR.json. |
| le-blanc | uncertain | Operator website did not yield a usable current calendar; 2025-or-later operation or reopening remains unverified. [Source](https://efpleblanc.com/). |
| le-havre-octeville | seasonal | Operator explicitly publishes the Le Havre season from 13 March to 31 October 2026, with selected operating weekdays and exclusions during Avranches sessions. [Source](https://www.abeilleparachutisme.fr/zones-de-saut). |
| le-val-saint-pere-mont-saint-michel | seasonal | Operator lists Avranches jump sessions on 22–25 May, 26–29 June, 24–27 July, 28–31 August and 25–29 September 2026, departing and landing at Le Val-Saint-Père. [Source](https://www.abeilleparachutisme.fr/zones-de-saut). |
| les-sables-d-olonne-talmont-aerodrome-de-la-lande | seasonal | Operator article published 16 October 2025 and updated 28 October 2025 presents its 2026 jump calendar. [Source](https://www.vendee-evasion.fr/calendrier-2026-quand-sauter-en-parachute/). |
| lons-le-saunier-courlaoux | seasonal | Operator 2026 calendar, revision 29 April 2026, explicitly allocates jump dates to both Lons-le-Saunier and Tournus-Cuisery. [Source](https://www.airextrem-parachutisme.fr/medias/le%2029%20avril%202026%20-%20Planning%202026%20.pdf). |
| marennes | uncertain | Big Air now identifies Rochefort as its dropzone; no dated 2025-or-later jump schedule at the separate Marennes airfield was verified. [Source](https://bigair-parachutisme.fr/dropzone/). |
| montargis-vimory | seasonal | Operator publishes its 2027 Montargis season calendar from the weekend of 20–21 March to 30–31 October; these are announced future sessions. [Source](https://flyattitude.com/). |
| montpellier-candillargues | uncertain | No identified aircraft-operating skydiving provider or dated 2025-or-later jump calendar was verified for this directory lead. See existing directory sources in FR.json. |
| mortagne-au-perche | uncertain | Operator calendar retrieved during follow-up still described 2024; no dated 2025-or-later sessions at Mortagne were verified. [Source](https://www.france-parachutisme.com/pages/calendrier). |
| nancy-essey | uncertain | Tandemotion current zone list omits Nancy-Essey; its 2026 announcements do not establish resumption at this particular field. [Source](https://parachutismelorraine.fr/zones-de-saut/). |
| quiberon | seasonal | Bay of Quiberon tourism page gives 4 April–1 November 2026 opening for Entre Ciel et Terre at Quiberon. [Source](https://www.baiedequiberon.bzh/a-voir-a-faire/sports-et-loisirs-en-bretagne-sud/entre-ciel-et-terre). |
| reims-prunay | uncertain | Operator booking presence is live but undated; public social access was restricted and no opened 2025-or-later dated jump evidence was verified. [Source](https://www.air-parachutisme.com/). |
| revel-montgey | active | Castres-Mazamet official 2025–2026 student guide, page 23, identifies Chutextrem jump locations at Castres and Revel; the operator also offers both locations on its current website. [Source](https://www.castres-mazamet.fr/sites/castres-mazamet.fr/www.castres-mazamet.fr/files/images-joined-files/Guide%20etudiant%202025-2026%20bd.pdf). |
| rodez-marcillac | seasonal | Operator booking terms updated November 2026 explicitly identify Sarlat-Domme and Rodez-Aveyron for tandem jumps and describe a winter interruption between October and May. [Source](https://www.chutelibre.fr/cgv.pdf). |
| saint-girons-antichan | active | Operator presentation explicitly describes its management in 2026, names this airfield among its five operating bases and states ownership of its Cessna 182; individual session dates are not established. [Source](https://parachutismeoccitan.com/qui-sommes-nous/). |
| saint-laurent-medoc | uncertain | Operator website remains present, but no opened 2025-or-later dated session calendar or public activity post was verified. [Source](https://www.fl140-parachutisme.com/). |
| sarlat-domme | seasonal | Operator booking terms updated November 2026 explicitly identify Sarlat-Domme and Rodez-Aveyron for tandem jumps and describe a winter interruption between October and May. [Source](https://www.chutelibre.fr/cgv.pdf). |
| sissonne | uncertain | Historical records describe a proposed CERPP move from Laon to Sissonne; no 2025-or-later civilian operation or reliable Sissonne jump-site position was verified. [Source](https://www.senat.fr/seances/s200006/s20000613/s20000613_mono.html). |
| tournus-cuisery | seasonal | Operator 2026 calendar, revision 29 April 2026, explicitly allocates jump dates to both Lons-le-Saunier and Tournus-Cuisery. [Source](https://www.airextrem-parachutisme.fr/medias/le%2029%20avril%202026%20-%20Planning%202026%20.pdf). |
| vesoul-frotey | uncertain | Operator zone page reports an administrative obstacle for Vesoul; no dated 2025-or-later resumption at this field was verified. [Source](https://sky-delivery.fr/zones-de-saut/). |
| vichy-charmeil | seasonal | Operator reservation page includes Vichy and displays a 2026 end-of-season announcement with resumption on 16 April 2027. [Source](https://auvergne-chutelibre.fr/reserver-un-saut/). |
| villefranche-de-rouergue | active | Operator presentation explicitly describes its management in 2026, names this airfield among its five operating bases and states ownership of its Cessna 182; individual session dates are not established. [Source](https://parachutismeoccitan.com/qui-sommes-nous/). |

### Coordinate follow-up

Four of the five missing pairs were resolved from opened sources:

- **belleme**: 48.30056, 0.58111. [FFPLUM airfield page coordinates for Bellême–Saint-Germain-de-la-Coudre; LF6152 is a platform identifier, not an ICAO code.](https://ffplum.fr/terrains/lf6152-belleme-st-germain-de-la-coudr)
- **bouloc-en-quercy**: 44.30779, 1.08056. [FFPLUM airfield page coordinates for Bouloc; LF8223 is a platform identifier, not an ICAO code.](https://ffplum.fr/en/terrains/lf8223-bouloc)
- **fretoy-le-chateau**: 49.665064, 2.968031. [Club dropzone access coordinates converted from degrees, minutes and seconds.](https://parasportcompiegnois.wifeo.com/drop-zone.php)
- **la-tranche-sur-mer**: 46.365556, -1.4275. [French SIA VAC chart dated 19 February 2026: aerodrome reference point, not a surveyed parachute landing target.](https://www.sia.aviation-civile.gouv.fr/media/dvd/eAIP_29_OCT_2026/Atlas-VAC/PDF_AIPparSSection/VAC/AD/AD-2.LFTA.pdf)

**Sissonne remains null.** [EXTRM Sport](https://app.extrmsport.com/skydive/dropzone/fr/sissonne/) names Sissonne but gives 49.5968, 3.6325, which locates Laon-Chambry. [The Senate record](https://www.senat.fr/seances/s200006/s20000613/s20000613_mono.html) describes a proposed move from Laon to Sissonne, not a confirmed landing-area position. No verified civilian dropzone coordinate was found; a military camp centroid was not substituted. Overpass was not retried.

### Duplicate audit

Checked all keys and non-null ICAO codes for repetition, and compared every available coordinate pair for separations under 3 km; none matched. Reviewed the apparent CERPP Laon/Sissonne conflict separately: evidence describes different places and a proposed relocation, so the erroneous directory pin is insufficient to merge them. Likewise, Dunkerque/Calais and Marennes/Rochefort are distinct airfields despite shared or relocated operators. No records were merged.

### Remaining gaps

The uncertain rows above each retain a specific one-line reason in FR.json. Public Facebook pages for Reims and FL140 did not supply accessible dated evidence; no sign-in was attempted. Vichy’s operator image explicitly announces the end of the 2026 season and an April 2027 restart, so temporary winter closure was treated as seasonal. The 2027 calendars at Albi, Fayence and Montargis are published plans rather than proof of completed future jumps. Occitan bases have an explicit 2026 operator presentation, but exact session dates remain unverified. Booking-site evidence for Colmar, Dijon and La Roche is weaker than operator calendars and should be confirmed with direct dated schedules in a future review. Sissonne remains the sole coordinate gap.

Validation: python3 -m json.tool FR.json; unique keys and ICAO codes, coordinate pairing/ranges, nonempty sources and status evidence checked. Only FR.json and this coverage file were edited in this follow-up.
