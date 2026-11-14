# Coverage: Western Balkans and the east (RS, BA, ME, MK, AL, XK, MD, UA)

Researcher: claude. Researched on 2026-11-14. Development data only.

Common method for every country:
- OpenStreetMap through Overpass. The main overpass-api.de endpoint refused connections, so the queries went to
  the maps.mail.ru public mirror, one country at a time with pauses. Each query asked for `sport~parachuting|skydiving`;
  name, operator or description matching parachuting words in local languages (padobran, падобран, парашут,
  parașut, parashut, стрибк); and all `aeroway=aerodrome`. The overpass.osm.ch mirror returned an empty result
  for UA because it only holds Swiss data, so that result was discarded.
- Web searches in English and the local language. Public pages only, with no sign-in. Facebook and Instagram
  showed only page titles or login walls, so no social post served as dated evidence.
- No country-level dev-listings venues exist for these countries in `../dev-listings.json`, which covers only GR, BG,
  ES and PT. None of the eight files existed before, so there was nothing to merge.
- dropzone.com redirected to an unrelated domain, and dropzonesandtunnels.com redirected to a gambling site.
  Neither was used.

Status counts: active / seasonal / uncertain / closed.

## RS Serbia: 6 records (2 / 0 / 4 / 0)
Sources checked:
- the Civil Aviation Directorate register of declared training organisations (2026 PDF), which lists 2 parachutist DTOs, both at Lisičji Jarak;
- CAD pages for parachutists and ATOs;
- Ministry of Defence news on the Balkan Friendship Jump 2026;
- operator sites tandemskokbeograd.com, skydiveserbia.com, padobranskicentarbeograd.rs, skydivingserbia.rs and aeroklubpn.org.rs;
- news from novosti.rs, nistv.rs and rtvparacin.rs;
- tourism pages serbia.com and novisad.travel;
- OSM.

Records:
- active: Lisičji Jarak (LYBJ, Belgrade) and Paraćin/Davidovac (LYPN);
- uncertain: Čenej/Novi Sad, Ečka/Zrenjanin, Kikinda and Subotica.

Open:
- No dated 2025 or later activity was found for Čenej (November-Sierra), Ečka, Kikinda or Subotica (Aeroklub Ivan Sarić, "Kup Subotice").
- The Vazduhoplovni savez Srbije site (vss.rs) did not load, so its club list was not checked.
- Niš hosted the 72nd open championship in September 2026 at the JKP "Naissus" grounds, with a police Super Puma. This was an event, not a regular dropzone, so it has no record.
- Military jumping (63rd Parachute Brigade at Niš and Batajnica) is excluded because it is not open to civilians.
- Smederevo, Kraljevo (Morava), Vršac and Kragujevac were not checked individually.

## BA Bosnia and Herzegovina: 2 records (0 / 1 / 1 / 0)
Sources checked:
- the Prijedor 2025 competition bulletin (aeroclub.at PDF);
- seesrpska.com and gradprijedor.com;
- a tourism page for the Banja Luka club;
- go-bosnia;
- OSM.

Records:
- seasonal: Urije/Prijedor (LQPD), where competition and training jumps took place in July 2025 with a PC-6;
- uncertain: Zalužani/Banja Luka (LQBZ), whose newest dated event is from 2014.

Open:
- The aviation federations of BiH and Republika Srpska have no club lists online that were found.
- No parachuting was found at Livno, Visoko, Tuzla, Mostar or Bijeljina.
- The OSM node "Skydive" at Jahorina (node 10576128227, `tourism=attraction`, operator OC Jahorina) appears to be a resort ride, not a dropzone, so it was excluded.

## ME Montenegro: 2 records (1 / 0 / 1 / 0)
Sources checked:
- the Podgorica tourism organisation's 2025 active-tourism brochure (PDF) and skydiving page;
- gopodgorica.com;
- the CAA Montenegro airfield list (updated 2018);
- OSM.

Records:
- active: Ćemovsko polje / Špiro Mugoša (LYPO), with two tandem operators;
- uncertain: Kapino polje / Nikšić (LYNK), which is CAA-approved for parachuting but has no recent evidence.

## MK North Macedonia: 1 record (1 / 0 / 0 / 0)
Sources checked:
- the Aeroklub Skopje sites aeroklubskopje.mk and aeroclub.mk;
- umno.mk and kanal5 (centenary at Stenkovec, 2023);
- kupinapopust.mk;
- OSM.

Records:
- active: Stenkovec (LWSN). This status rests on the maintained club site, which offers tandem jumps and has files uploaded in 2026, not on a dated jump post.

Open:
- Kumanovo (AK "Done Božinov") and other airfields found in OSM have no parachuting evidence.

## AL Albania: 0 records
Sources checked:
- the national aero club federation page nac.org.al (parachuting discipline), which names Aeroclub Tirana and Aeroclub Durrësi but gives no airfield;
- web searches in Albanian and English, which return only paragliding (Dajti, Llogara, Vlorë);
- OSM, which has no parachuting features.

Open:
- Find out which airfield, if any, Aeroclub Tirana and Aeroclub Durrësi jump from.
- An aviation academy registered in December 2025 lists parachute training among its activities, but no place is given.

## XK Kosovo: 0 records
Sources checked:
- Prishtina Insight, which reports that no active small-aircraft airfields remain;
- the CAA Kosovo parachuting regulation 11/2018;
- cereport.eu (2026), whose aeronautical club does paragliding;
- OSM.

Open:
- OSM node 5626163121 "Parashutizmi pista" is tagged `name:en=Motor Paragliding`, so it was excluded.
- Gjakova airfield is in military use.

## MD Moldova: 2 records (2 / 0 / 0 / 0)
Sources checked:
- the Parachuting Federation site skydive.md;
- diez.md (19 July 2025);
- the Aero Team Moldova site;
- the g0.md listing;
- sporter.md (2019 championship at Vadul lui Vodă);
- OSM.

Records:
- active: Vadul lui Vodă (LUKV) and Horești (LUKH).

Open:
- It is not confirmed that Aero Team Moldova jumps at Horești itself, because its site describes the location as "near Vadul lui Vodă".
- The Avdarma (Gagauzia) cup took place in 2018, and its airfield was not identified.
- The OSM node "Turn de Parașutism" in Chișinău is a jump tower, so it was excluded.
- Transnistria (Tiraspol LUTR) was not researched.

## UA Ukraine: 9 records (0 / 0 / 9 / 0)
Sources checked:
- the EASA conflict zone bulletin (revised 24 July 2026, valid to 31 January 2027; NOTAM A0021/26 closes the Ukrainian FIRs to civil flights);
- operator pages for Chayka, the Kharkiv aeroclub, the Chernihiv club (skok.kiev.ua) and Tsuniv;
- the kava.ua reseller;
- a t1.ua overview, which is pre-war (2020);
- OSM, which returned 627 matching features.

Records, all uncertain:
- Chayka (UKKJ);
- Borodianka / DZ Boro (UKKB);
- Korotych (UKEK);
- Chemer / Progres (UKAC);
- Tsuniv (UKGC), whose operator page says jumps are temporarily not conducted;
- Maiske / Avia-Soyuz (UKDQ), where the reseller marks the service as not operating;
- Hidroport / Odesa (UKOE);
- Voroniv (UKGW);
- Filiutka, an OSM lead only.

No dated evidence of civilian jumping after 24 February 2022 was found anywhere. The newest Kharkiv aeroclub items are from 2023 and describe members jumping abroad.

Open, and needing an owner decision:
- Occupied territory was left out on purpose. OSM has "Пара-Крым" (node 6761324515, Crimea, Russian phone number) and a `sport=parachuting` node near it (2390029367), plus a DOSAAF airfield at Yenakiieve (Donetsk). Whether places in occupied territory belong on the map is a product and legal question, so no records were written for them.
- If civil airspace reopens, Ukraine should be re-checked first.

## Check

Checked on 2026-11-14 by a second pass (claude), trying to prove records wrong. All 22 original records were checked.

Coordinates: every record's OSM element was re-opened through the OSM API (osm.org/api/0.6), and its centre was recomputed.
All 22 match the stored point to within 0.01 km, and each element is the named airfield (or, for Lisičji Jarak and
Borodianka, a landing area or club building on it). The ICAO codes match the OSM `icao` tags. No duplicates were found.

Corrected:
- RS `rs-cenej-novi-sad`: uncertain → active. The operator (Tandem Skok Novi Sad / Skydiving Novi Sad) has dated
  posts naming Čenej: Instagram on 7 Jun, 26 Jun and 10 Sep 2025 ("every weekend"), and Facebook on 27 Jun 2025.
  These were read from search-result snippets because the pages are behind a login wall. The operator was added.
- RS `rs-subotica`: uncertain → active. The operator site, Skydive 024, gives the airfield road address, says
  "every weekend at the airfield" and carries a 2026 footer. An Instagram @skydive_subotica tandem reel is dated
  27 May 2026 (search snippet). The operator was added.
- RS `rs-ecka-zrenjanin`: status unchanged (uncertain). The operator was identified (Aeroklub Zrenjanin,
  ecka.aero; tandem offer since August 2021). No dated jumps from 2025 or later were found.
- BA `ba-prijedor-urije`: still seasonal, with 2026 evidence added: Prijedor Boogie ran 29 Jun to 3 Jul 2026 with
  tandem jumps for the public from a PC-6, and Prijedor Open 2026 followed. Skydive Banjaluka was added as an
  operator; its tandem jumps at Urije on 4 Jul 2025 rest on a YouTube title seen in search results.
- MK `mk-stenkovec-skopje`: active → uncertain. The club pages are undated (the aeroclub.mk footer reads 2023), and
  the newest dated jumping item found is a training report from March 2023. Airfield documents from 2025 do not
  count as evidence of jumps.
- MD `md-horesti`: active → uncertain. The 2025 article gives prices but no place. The operator site names both
  "aerodromul Horesti" and "Vaduleni - Vadul lui Vodă", and its listed fleet is for pleasure flights.
- MD `md-vadul-lui-voda`: DZM Skydive MoldAVIA (dzm.md) was added as an operator. Its site names the Vadul lui Vodă
  sport airfield and uses the same phone number as "Skydive Moldova" in diez.md.
- UA `ua-filiutka`: uncertain → closed. The place is a youth military-patriotic camp. Its only public jump offer
  dates from 2015, its An-2 UR-71206 was deregistered in 2018, and civil airspace has been closed since 2022. It
  should not be shown on the map.
- UA `ua-chayka-kyiv`: Para-Skuf, which is based at Chayka, was added as an operator. Its newest news item, from
  24 Feb 2022, says "Chayka airfield is not working".
- UA `ua-borodianka`: the operator entry was split. Para-Skuf ran the jumps but is based at Chayka; DZ Boro is the
  club building tagged in OSM.

Added:
- BA `ba-bihac-golubic` (LQBI), uncertain. Aero centar Panorama Bihać runs tandem jumps for groups of 15 or more
  only, and the newest dated item is from 24 Sep 2022.
- BA `ba-visoko` (LQVI), uncertain. Slobodan Pad, a visiting team from Croatia, ran tandem jumps here on
  28–31 May 2026. These were scheduled jump days, not a resident dropzone. This corrects the earlier note that
  Visoko had no parachuting.
- UA `ua-sutysky` (Vinnytsia), uncertain. An undated pre-war article says jumps ran every weekend. The coordinates
  come from OSM way 1371244258.

Still doubtful:
- Kikinda (RS), Zalužani (BA) and Kapino polje (ME) have no dated evidence; they were searched again without result.
- In the Čenej and Subotica statuses, the dates come from search snippets of Instagram and Facebook pages, not from
  the pages themselves.
- Skydive Montenegro is advertised on Instagram as tandem jumps near the Bay of Kotor from a Cessna, with the phone
  number of Skydive Bulgaria. No airfield was found, so there is no record. It is a lead for Tivat.
- Ukraine: no dated civilian jumping from 2025 or later was found anywhere. All UA records stay uncertain, except
  Filiutka, which is closed.
- Ćemovsko polje (ME) is active on the strength of a February 2025 tourism brochure only. No dated jump post was
  found.

Counts after the check (active / seasonal / uncertain / closed): RS 6 (4/0/2/0), BA 4 (0/1/3/0), ME 2 (1/0/1/0),
MK 1 (0/0/1/0), AL 0, XK 0, MD 2 (1/0/1/0), UA 10 (0/0/9/1). All eight JSON files pass `python3 -m json.tool`.
