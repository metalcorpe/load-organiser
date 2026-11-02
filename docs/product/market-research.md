# Market research and product references

Research recorded on 2026-11-02. Sources were consulted during this discovery conversation. Product descriptions are vendor claims unless noted; applications, interoperability, customer adoption, and commercial outcomes were not independently tested. Prices can change and are not directly comparable across scopes.

## Dropzone operations platforms

| Product and source | Published capabilities | Implication for Load Organiser |
| --- | --- | --- |
| [Burble DZM](https://www.burblesoftware.com/products/burble-dzm-software/) | Drag-and-drop manifesting, standby lists, load timing, equipment/repack tracking, booking integration, automated calls | Local manifest functionality already has established alternatives; switching needs a concrete benefit |
| [DZ-Manager](https://www.dz-manager.com/en/manifest) | Multi-aircraft board, teams, combined student/staff/camera/gear assignment, accounts, payments, reports, printing | Group handling and resource coordination need operational depth |
| [Skymanifest](https://skymanifest.com/) | Browser interfaces, live updates, group transfers, self-manifesting, tickets | Browser access alone is weak differentiation |
| [SkyWin / SkyWinOne](https://skywin.se/) | Member records, logbook, transactions, self-manifest queue, live load display | Club needs extend beyond a one-day list of names |
| [EZDZ](https://ezdzskydive.com/features) | Manifest, bookings, payments, waivers, verification workflows, public load board, reporting | Commercial operators can compare an integrated operations offering |

Cross-dropzone identity is not automatically unique: Burble discusses reusing an existing Burble account at another Burble location, and DZ-Manager says its identification cards are not tied to one dropzone. This does not establish parity with the proposed shared logbook or permission model. [Burble overview](https://www.burblesoftware.com/products/burble-dzm-software/), [DZ-Manager self-manifesting](https://www.dz-manager.com/en/self-manifesting).

### Pricing observations

| Product | Published observation at research time |
| --- | --- |
| [Burble](https://www.burblesoftware.com/pricing/) | Price plans available on request; conditions vary by plan and booking usage |
| [DZ-Manager](https://www.dz-manager.com/en/editions/eur) | Free Community edition on one PC; Professional license listed at €35/month per concurrent connection, with additional modules/services and tax conditions |
| [Skymanifest](https://skymanifest.com/) | Advertises pay-per-jump pricing; a numerical rate was not established |
| [EZDZ](https://ezdzskydive.com/pricing) | Lists $0/month plus 4% platform fee or $199/month plus 2%, with standard payment processing additional; a quoted flat-rate option also exists |

Do not infer market size, willingness to switch, or a sustainable price from these listings. A low subscription price may coexist with transaction fees, integration costs, hardware, support, or migration effort.

## Personal jumper and specialist products

| Product and source | Published capability to learn from | Proposed connection in this app |
| --- | --- | --- |
| [PADI app](https://pros-blog.padi.com/new-padi-app/) — adjacent diving reference | Credentials, learning, offline/online logging, verification, destination discovery, and booking access | A connected personal journey across learning, logging, and future activities; PADI is not a skydiving competitor |
| [JumpTrack](https://www.lbaltimeters.com/jumptrack.html) | Digital logbook, maintenance tracking, exports, and Bluetooth downloads/settings for specified LB devices | Gear passport and device-supported entries; device configuration is outside initial scope |
| [Exits](https://exits.zone/en) | Paper-log recognition, review/rollback, gear service records, training, camps, media, statistics, and community | Reduce migration effort and connect personal history with events; broad feature bundling already exists |
| [Airspace](https://joinairspace.com/) | Coach availability, requests, events, discipline skill cards, and sky/tunnel discovery | Connect experience, goals, coaches, and booking |
| [Rhythm Skydiving 101](https://play.google.com/store/apps/details?id=com.rhythm.android) | Videos, diagrams, flashcards, and exercises for new skydivers | Original/licensed learning content linked to goals and instructor review |
| [Skydive Designer](https://apps.apple.com/us/app/skydive-designer/id1495969361) | Formation design, transitions, people and aircraft slotting, publishing/sharing | Attach shared plans to groups and loads; consider links or integration before rebuilding an editor |
| [FSNinja](https://play.google.com/store/apps/details?id=com.fsninja.fsninja) | Animated formations, saved dives, random draws, shared links | Team practice library and session history |
| [Spot Assist](https://www.spotassist.com/) | Skydiving weather, winds aloft, and canopy/spotting tools | Planning information connected to destination visits; avoid unsupported go/no-go automation |
| [Skyderby](https://skyderby.io/support) | FlySight 1/2, GPX/KML imports, device connections, and competition-related workflows | Telemetry attachments and debriefing; specialist flight tools already exist |
| [Paralog](https://paralog.net/desktop) | Skydiving logbook, device downloads, flight analysis | Maintain useful portability and import rather than assume users will abandon existing logs |
| [FreeFallFilms](https://freefall.ing/) | Editing, customer video delivery, purchase options, and notifications | Link delivered media to customer/jump records; investigate integration |
| [InTime Scoring](https://www.intimescoring.com/about) | Multi-discipline scoring, event management, publishing, broadcasting, remote judging | Event participation and external results before specialist judging work |

Other discovered products include [Tobu](https://www.tobuskydive.com/faq/getting-started-with-tobu), [Squifly](https://squifly.app/), and [Skydive LogBook](https://apps.apple.com/us/app/skydive-logbook/id1008308865). Their published materials cover overlapping personal recording, device/import, or event functions; no exhaustive feature comparison was performed.

Published early-access/beta examples [Jumpfolio](https://jumpfolio.app/) and [Swoop Log](https://swooplog.com/) also describe broad bundles. Treat advertised or planned features separately from verified released behavior. They are research leads, not proof of demand or mature competitors.

## Import-format references

- [FlySight original file format](https://www.flysight.ca/wiki/index.php/File_format): timestamps, coordinates, mean-sea-level height, velocity components, accuracy, fix, and satellite fields. The page advises tolerating additional unknown columns.
- [PyFlySight project](https://github.com/sco1/pyflysight): documents differing V1/V2 layouts, `TRACK.CSV`, `SENSOR.CSV`, and parsing workflows. A potential implementation reference, not a selected dependency.
- [Skyderby import support](https://skyderby.io/support): a useful reference for a user-facing upload experience and supported format claims.
- [Squifly migration template](https://squifly.app/blog/how-to-import-logbook-entries/): example of historical logbook CSV migration, which differs from telemetry import.

No format importer has been implemented or validated here. Real anonymized samples, device/firmware variants, permissions to use fixtures, and round-trip/export expectations are needed before compatibility claims.

## Research conclusions and limits

Additional association research: [USPA integration opportunities](uspa-integration.md) records primary-source evidence of approved API requests and distinguishes those precedents from access obtained for this project. It also identifies Aspire as a credential-sharing route to investigate. No integration has been tested.

Proposal: differentiate through continuity between personal records, trusted sharing, local acceptance, booking, and manifest operations. The existence of specialist products supports investigating these jobs; it does not prove that combining them will attract users or generate revenue.

Build core identity, record provenance, and operational workflows. Evaluate partner integrations for advanced editing, formation design, and scoring. Adopt product patterns using original implementation/content; external API access and licensing have not been established.
