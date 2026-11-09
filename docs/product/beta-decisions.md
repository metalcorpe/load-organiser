# First-beta product decisions

Status: selected working product baseline. The product owner delegated the remaining product calls to the assistant after the two-pass review. These are expert design decisions made under that delegation, not invented user-research results or a claim that each detail was separately dictated by the owner. Feature implementation remains for Claude Code; no public launch or paid-service commitment is authorized here.

This decision sheet and the updated [release brief](release-brief.md) supersede conflicting broader proposals in the discovery documents. Architecture #143 can proceed against this baseline. User/device validation and real inventory/maintenance evidence remain release conditions, not reasons to keep repeating scope approval.

## Product and first audience

Build for active recreational skydivers: **find a worthwhile European jumping opportunity, keep your own records wherever you jump, and selectively share completed activity with people you know.** English interface first, original source names/languages preserved. No discipline restriction and no participating DZ required.

The private log and discovery board must each be useful without a social network. Social features connect those activities; they are not the only route to first value. Demand and return behavior still need evidence.

## Selected boundaries

| Decision | First beta | Reason |
| --- | --- | --- |
| Discovery geography | Europe; accept European suggestions, show actual published coverage | Preserve the owner's direction without promising complete coverage |
| Opportunity inventory | Dated events, boogies, camps and courses; basic provider identity attached to offerings | Focus maintenance on actionable opportunities rather than a general professional directory |
| DZ directory | Source-backed public venues plus private provisional places worldwide for logging | Logging cannot depend on operator registration or public listing review |
| Coaches/schools | Show as offering organizers/providers where sourced; defer standalone searchable coaching/school directories | Avoid availability, credential and broad profile-maintenance work before the core board is useful |
| Personal records | Manual private log, optional component/serial records, accurate recorded summaries and optional prior-history baseline | Useful for both new and experienced jumpers without requiring a rig inventory or historical re-entry |
| Saves and plans | Private bookmarks and simple dated private visit plans; no shared future intentions | Keep trip preparation while reducing social/location obligations |
| Social | Opted-in profiles, approved follows, selected completed-jump cards, chronological feed and authorized venue activity | Retain the social value the owner requested without adding chat, reactions or future-attendance features |
| Media | Structured text and explicitly selected external links; no hosted media/documents | Bound storage and moderation costs |
| Portability | Free versioned export; own-export restore into empty personal records; exact repeat acknowledgement without reapplying | Recovery is essential; a general merge/conflict interface is not |
| Operations/funding | Owner reviews initial listings and social reports; optional external support link; no paid provider/account selected | Keep responsibility explicit and expenditure bounded |

Keep the release brief's field/text/link limits as working design defaults. Technical account quotas, restore size limits and rate limits are to be measured/selected in #143/#161; their absence does not reopen audience or feature scope. No native/PWA/offline sync, device imports, live forecasts, USPA retrieval, verified ownership transfers, bookings/payments or DZ operations enter this beta.

## Prior-history baseline

An optional private setting records **B jumps completed before calendar date D**, explicitly self-declared. It does not manufacture dated jump entries, gear uses, signatures or recent-activity evidence. It is not part of profile setup or a condition for saving the first jump.

- Show detailed recorded entries separately from declared prior history.
- With a baseline, the reported lifetime total is B plus the number of distinct detailed entries dated on or after D. Entries before D remain usable history but are already represented by B and are not added again.
- Without a baseline, show the recorded count and label it accordingly; do not infer lifetime total from the highest jump number.
- Example fixture: B=200 before D; three entries on/after D produce a reported total of 203. Adding one detailed pre-D entry leaves 203 unchanged. Recorded component uses reflect only detailed entries with explicit equipment, regardless of which side of D they fall on.
- If detailed pre-D entries exceed B, flag the inconsistency and require review before presenting a combined lifetime total; do not reject the jump or silently inflate B.
- Editing B/D previews the effect on totals and preserves correction provenance. Deleting an old detailed entry does not silently rewrite the separately declared B.
- Export/restore includes the baseline, cutoff and provenance. Keep it private and outside shared cards. No eligibility/currency clearance is derived from it.

#154 owns this behavior, with date/boundary representation settled in #143 and regression evidence in #160.

## Restore boundary

The personal export contains the owner's records, baseline and needed references in a documented version. Restore validates it and previews counts before writing to **empty personal records**. Account identity/settings are separate; an authenticated account need not be newly registered to have empty records.

A completed restore has a receipt. Repeating the same completed archive/operation returns Already restored with no writes; it does not undo later edits or refill later deletions. If an unrelated archive is supplied while records already exist, reject it before writes and explain that merging is deferred. Do not ask the user to delete existing records as a workaround. Existing records remain readable/exportable.

Invalid/unsupported input, foreign reference collisions, excessive file size, and partial failure must not silently alter existing records. #143 chooses the atomic restore/recovery mechanism; #155 tests round-trip, repeat acknowledgement, rejection-without-mutation and reference ownership. Restore never republishes cards, restores follow approvals, grants roles or claims third-party verification.

## Maintenance and validation

The owner remains the initial maintainer and report reviewer. Start with a curated subset of sourced European dated opportunities and related DZs, not every country/category at equal depth. Record source, status, last check and actual coverage. The proposed weekly/60-day review routine is an operating default, not evidence that the workload fits the owner's schedule.

Owner decisions recorded 2026-11-09 (#162):

- Initial coverage: Greece, Bulgaria, Spain and Portugal; categories event, boogie, camp and course, with the dropzones and organizers they need. Other European countries keep accepting suggestions but are not actively populated.
- Sources: the association directories, operator calendars and organizers' own sites listed in the release brief's source table, entered by hand from each source page.
- Entry: candidate records are drafted from public sources by the assistant (`docs/product/inventory/`); the owner checks each against its source and enters and publishes it through `/review`. A draft is not a reviewed record.
- Maintenance: the owner confirmed the weekly routine (release brief, "Maintenance cadence"). The 60-day profile recheck stays the documented default and was not separately confirmed.
- Funding: a voluntary support link is wanted. Provider, link and the cost figures to disclose are not chosen yet.

#151/#162 must perform a real inventory/review exercise before launch: collect permitted records for the enabled categories, walk the discovery query, check changes/expiry and record effort and gaps. Limit published inventory or pause expansion if maintenance is not sustainable. No numerical inventory target, time budget, acquisition/retention result or volunteer capacity is invented.

#160 owns representative mobile/user validation after implementation, including independent discovery/logging value, no-friends first use, history totals, save reliability, private/public access, account switching and recovery. Closing planning issues does not mark those release checks complete.

## Tracking changes

- #141: scope decision complete under delegated product judgment.
- #142: planning walkthrough accepted through the delegated expert review once reconciled to this cut. User/device acceptance remains #160, not a fabricated result of the mockup.
- #143: architecture planning complete in [architecture](architecture.md) and [data contracts](data-contracts.md); [Claude Code handoff](claude-code-handoff.md) prepares #144. Runtime and host assumptions remain untested.
- #159: shared future intentions deferred outside V1; remove it as a blocker of #160 and from the P4 milestone/epic.
- #149/#150: dated opportunities/basic provider identities and private bookmarks/plans; standalone professional directories are later work.
- #154/#155: selected baseline and bounded restore behavior above.
- #135/P0 planning is complete. #144 is the next implementation task; implementation/release issues remain open.

Review history: [two-pass findings](product-review.md). The review's risks remain evidence needs even where this sheet selects a direction.
