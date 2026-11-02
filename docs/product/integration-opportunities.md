# Integration and connected-data opportunities

Research recorded on 2026-11-02. Discovery inventory for a skydiver-first application. No listed integration has been implemented, tested end to end, selected as a dependency, or agreed with a provider. Public information, file formats, and partner APIs require different implementation and permission models.

## Opportunities beyond USPA credentials

| Opportunity | Personal user value | Evidence / integration boundary |
| --- | --- | --- |
| FIT activity import | Attach supported watch recordings to logbook entries | Garmin publishes a FIT format and SDK; actual skydiving files, sampling quality, fields, and device compatibility need testing |
| Device-cloud synchronization | Avoid repeated manual file uploads | Garmin publishes an approval-based Activity API opportunity; access is not established. Its page was indexed but direct retrieval returned 404 in this research; confirm the current program before planning against it |
| Aviation observations and forecasts | Review nearby station conditions while planning | Aviation Weather Center publishes a machine-readable METAR/TAF API with coverage and usage restrictions; a station observation is not a dropzone observation |
| Numerical forecasts | Add hourly conditions and winds where supported | Open-Meteo publishes API documentation and commercial licensing; check exact variables, altitude levels, coverage, terms, and costs |
| Equipment notices and service references | Connect a gear passport to relevant manufacturer information | PIA publishes technical resources and manufacturers publish service material; a public document is not a structured API or complete alert feed |
| Lost/stolen gear references | Help a user investigate a matching equipment report before purchase | USPA publishes stolen-equipment reports including serials. No automated lookup API or complete/current registry was established |
| Rigger service confirmation | Add attributable servicing evidence to the component's history | A proposed in-app collaboration workflow; no third-party API or rigger participation assumed |
| Coaching and tunnel history | Keep coached goals, session duration, notes, and media alongside outdoor progression | Manual personal entries can be independent; automated booking/session imports require specific providers and agreements |
| Calendar and shareable visit documents | Remember booked activities and prepare records for travel | Candidate standards-based calendar export and private document export; recipient adoption need not be required. No account-calendar connector is selected |

## Sources

- [Garmin FIT Activity files](https://developer.garmin.com/fit/articles/file-types/activity.html) describe timestamps, GPS/sensor records, optional fields, and variable sampling.
- [Garmin FIT SDK](https://developer.garmin.com/fit/get-the-sdk/) supplies format tooling; decoding a file does not validate jump events or prove wearer identity.
- [Garmin Activity API](https://developer.garmin.com/gc-developer-program/activity-api/) is a program lead to recheck because direct retrieval failed despite indexed program information.
- [Aviation Weather Center API](https://aviationweather.gov/data/api/) documents observations, forecasts, station information, and request restrictions. Winds coverage depends on the chosen product; METAR/TAF alone is not a complete winds-aloft forecast.
- [Open-Meteo documentation](https://open-meteo.com/en/docs) and [licensing/pricing](https://open-meteo.com/en/pricing) distinguish evaluation/noncommercial access from commercial service.
- [PIA public documents](https://www.pia.com/resources/public-documents/) provide technical standards and references; no automated manufacturer serial verification or ownership API was found.
- [CYPRES maintenance information](https://www.cypres.aero/services/maintenance/) illustrates why maintenance references depend on the exact model/manufacture period. Do not copy a single service interval to every device.
- [USPA stolen gear](https://www.uspa.org/information/news/stolen-gear) publishes reports that can be linked as a research/reference tool. Lack of a matching report is not proof of ownership or that an item is not stolen.

## Equipment notice workflow proposal

Use manufacturer, model, manufacture date, and serial information to identify potentially relevant notices. Show the original source, publication/revision date, applicability, and when the reference was last checked. Keep applicability review distinct from completion of any action, and let an identified professional record supporting service evidence where appropriate.

Never label an item cleared or airworthy merely because no notice matched. A public archive may be incomplete or outdated; the [APF historical bulletin library](https://www.apf.com.au/members/safety-training/equipment/equipment-pages/racs-and-sbs/all-sbs/service-bulletins) explicitly says it is no longer maintained. Manufacturer-source review and an update responsibility would be needed before offering an alert service.

## Lost/stolen workflow proposal

Start with user-controlled reports and links to existing sources, preserving report provenance and dispute/correction history. If pursuing automated matching later, establish permitted access, update frequency, minimum matching identifiers, and a private review process. A possible match should not publish an accusation, reveal a private owner, or transfer a claim automatically.

## Discovery emphasis

Investigate weather and supported file imports as practical independent utilities. Equipment-reference links, private service records, and personal tunnel/coaching entries can deepen the gear/logbook experience without operator adoption. Cloud synchronization, external registries, formal sign-offs, and booking imports remain conditional opportunities rather than promised functionality.

For each source, record its exact access mechanism, permitted uses, data scope, identity matching, timestamp/freshness, outage behavior, provenance, costs, and export behavior before selecting it. Expand the needs inventory first; these opportunities do not establish an MVP.

Related: [USPA research](uspa-integration.md), [gear ownership](gear-ownership.md), [feature catalog](feature-catalog.md), and [adoption strategy](adoption-strategy.md).
