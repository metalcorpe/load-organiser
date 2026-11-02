# Mobile journeys and review walkthrough

Status: selected planning/design baseline for [#142](https://github.com/metalcorpe/load-organiser/issues/142), based on the [release brief](release-brief.md). Scope is settled by [delegated product decisions](beta-decisions.md). No Svelte screens, API behavior, persistence, accessibility compliance, or real-device behavior are implemented or validated by this walkthrough.

The [clickable phone mockup](mockups/mobile-walkthrough.html) is a standalone design artifact. All people, venues, dates and activity in it are explicitly illustrative. Buttons demonstrate screen transitions; they do not authenticate, store records, send reports, register attendees, or connect to services. Open the file in a browser to review it; it has no external dependencies or network calls.

The [two-pass product review](product-review.md) records scope/value risks and corrections; the decision sheet resolves the remaining product choices. The mockup remains an illustration; its Previous/Next controls are review navigation, not the application flow.

## Navigation and screen inventory

Recommended compact phone navigation: **Discover · Activity · Add jump · Records · Profile**. Discover is the guest landing page. Signed-in users keep the same tabs; the application does not switch into the existing staff dashboard after login. Records groups Logbook, Gear, and Saved/planned visits. Profile contains discoverability, follow requests, account/recovery, blocked users, data export/restore, and deletion. Account controls remain separate from the public profile preview.

| Screen | Main content and action | Audience |
| --- | --- | --- |
| Discover | Search, country/category/date filters, sourced opportunity list, separate DZ/provider results | Public |
| Opportunity detail | Source/status/date/time zone/venue/organizer/prerequisites/last check; save and external registration | Public; saves private |
| DZ/provider detail | Source-backed identity and related listings; venue shows only viewer-authorized shared cards | Public shell; audience-filtered content |
| Sign in/create account/recover | Preserve allowed return destination, explain the requested action, identify current account | No private content rendered while signed out |
| Logbook | Recorded totals, dated entries, Add jump; entry detail/edit/delete | Owner only |
| Add/edit jump | Date, DZ/provisional place, type; optional number, gear and measurements/notes/links | Owner only until a separate summary is published |
| DZ picker | Existing venue search; private provisional name/country fallback | Selection does not notify an operator |
| Gear list/detail/edit | Component label/type and private identifiers; archive and recorded use | Owner only |
| Save result | Confirmed private entry and totals; View jump, Log another, optional Share summary | Owner only |
| Share preview/post detail | Exact selected fields, explicit audience, canonical location choice, publish/unpublish | Owner preview; audience governs published summary |
| Activity/profile/follow requests | Chronological permitted cards, activity/publication dates, follow approval, block/report | Viewer-scoped; public profile only if opted in |
| Saved opportunities/visits | Separate private bookmark and destination/event/date plan; edit/cancel controls | Owner only; shared future intentions deferred |
| Reports/maintainer review | User report confirmation; owner queue and actions on allowed content | Reporter and scoped maintainer views |
| Export/restore/account recovery | Personal record export, import review/results, expired-session recovery | Owner only; identity rechecked as needed |

Desktop can use a wider list/detail layout with the same permissions and labels. Search/filter state and return navigation should survive normal in-app transitions. No installation, GPS, contacts access, push permission, map, or calendar view is required.

## J1 — Discover, save, and register externally

1. **Guest opens Discover.** Show real coverage, selected filters, readable results and source/status badges. No signup wall before browsing. An empty result offers Clear filters and Suggest a listing; it does not silently expand to another country or invent activity.
2. **Open opportunity.** Show provider and venue separately, source link, dates/time zone, last check and missing prerequisites/price/capacity. The visually primary action is Open organizer registration/contact; Save privately is also directly available. Source-backed/organizer-managed labels cannot imply partnership.
3. **Save requires an account.** Explain “Sign in to save this privately.” Preserve the validated destination, filters and intended save action. Cancel returns to the public detail. Registration/recovery returns to the same safe context; never accept an arbitrary external redirect.
4. **After sign-in.** Verify the account, re-read listing state and complete an idempotent save. Show “Saved privately — you are not registered.” If login took long enough for cancellation/expiry, show current status before proceeding. A repeated save is one saved item. It creates a bookmark, not a dated visit plan; Plan a visit is a separate optional action.
5. **External registration.** Open the clearly labeled external destination. Returning shows the saved record and current source status; the service does not mark registration as successful. Missing/broken source links offer Report a correction.

A guest who chooses the external link directly can leave without signing in. Expired/postponed/cancelled opportunities retain a readable detail and source, but never appear as confirmed upcoming availability. Schools/coaches may be identified as offering providers, but standalone ongoing professional directories are deferred.

## J2 — Log a jump anywhere, with optional gear

1. **Add jump immediately.** No onboarding questionnaire or gear inventory is required first. Show date, location picker and type/discipline; Other/unspecified is valid. Date defaults to the user's current local day and stays editable. Optional fields are progressively disclosed. Jump number and exact exit time are never fabricated.
2. **Pick a DZ.** Search stable listed venues. If missing, use a private provisional name/country and return to the form immediately. Public suggestion/review is a separate action. Location resolution never blocks the private log.
3. **Choose equipment actually used, optionally.** Select existing components, describe borrowed/rented gear, or leave unknown. Never preselect the current rig as if it were used. If the user chooses Add component, open a short optional branch and preserve the active jump draft when returning. Cancel returns without requiring gear.
4. **Optional component entry.** Require type and a readable label; serial/manufacturer/model/dates stay optional and private. Unknown serial is allowed. Show a confirmed/uncertain/failed save accurately and avoid duplicate creation. Manufacture/service dates retain their precision. The same component form is reachable independently from Records → Gear.
5. **Save privately.** Label the action Save private jump. Show a server-confirmed entry and recorded total; sharing later adds no jump. Result actions are View jump, Log another and optional Share summary. Normal private logging ends here without a social step. Records offers an optional self-declared prior-jump count/cutoff setting; it does not block logging. Show detailed recorded entries separately from the reported total under the [baseline rules](beta-decisions.md).

A likely duplicate receives a warning and an explicit choice to view the earlier entry or save a distinct jump. Two real jumps on the same day are valid. A timed-out request is “Save not confirmed,” not definitely failed: retry/reconcile must resolve the original submission identity before creating another entry. Technical details belong in #143, not product-facing copy.

No durable offline drafts are promised. The current page may retain unsaved input in memory; leaving/reloading/closing it can lose that input and must be explained. Navigating away from a dirty form offers Keep editing or Discard. Sensitive drafts must not appear in URLs or survive logout into another user's view.

## J3 — Share a summary without sharing the logbook

1. **Open a private jump → Share summary.** Render a new preview containing only activity date and chosen type/summary, plus optional canonical venue/caption/external link. Private notes, gear/serials, acquisition/service details and full history are absent, not merely visually collapsed.
2. **Choose audience.** Require Approved followers or Public; there is no inherited last-used public choice. Offer “Keep private” as an ordinary exit. Public explains that anyone may view/copy it, including someone browsing anonymously despite an account block.
3. **Publish.** Only explicit confirmation publishes. Show a success result with audience, actual jump date and publication date. A failed response preserves the preview and its private state; recheck publication state before retrying an uncertain request.
4. **View in feed/venue.** Apply the same audience rules on direct links, profiles and DZ pages. A provisional private venue is omitted from sharing until there is a canonical public reference; allow sharing without a venue.
5. **Correct or unpublish.** Unpublish removes service access and retains the private jump. Editing only unshared private notes or equipment leaves the summary unchanged. Editing fields actually shared in the card warns that it will be withdrawn before that source change is committed; deletion also withdraws it. Any later publication requires a fresh preview. Audience narrowing cannot leave the old content visible through a stale feed/detail/cache.

If another viewer opens an unavailable card, show a generic unavailable state without revealing whether the cause is blocking, a private audience or deletion. The owner gets useful own-record controls without sharing those explanations with other viewers. No live presence, visitor totals, comments or reactions are introduced.

## J4 — Find a person, approve a follow, and read activity

1. **Activity empty state.** Show “No shared activity yet,” people search and separately identified discovery links. Do not manufacture a community or import address books.
2. **Person search/profile.** Return opted-in profiles only. A private/non-discoverable person is not enumerated through email, serials, saved destinations or logs. New accounts can skip public discoverability and still use private records.
3. **Request follow.** Show Requested, Cancel request, or Unfollow as appropriate. The recipient reviews incoming requests from Profile/Activity. A pending request gives no follower access; approval does not publish any old private jump. Explain that approval lets the follower see existing follower-shared summaries as well as future ones. A manually shared opted-in profile URL/handle provides a route to an existing friend without platform invitations or address-book access.
4. **Activity feed.** Show only permitted cards in publication order, with the activity date visible separately. Load more preserves position; no constant real-time polling is required. Show a loading indicator distinct from an empty feed.
5. **Unfollow/remove follower/block.** Confirm the meaningful access effect. Blocking removes both-direction connections and denies authenticated discovery/profile/post access through every entry point, with the public-content limitation explained to the blocker. Reporting is a separate action and does not notify the reported user of the reporter's identity.

No public counts of followers, private visitors or jumps are needed. Profile self-description and social activity never imply recognized qualifications, currency acceptance, or a verified completed jump.

## J5 — Save and plan a visit privately

1. **Save an opportunity.** A private bookmark has no attendance meaning and does not require choosing a date.
2. **Plan a visit separately.** From a saved opportunity or DZ, choose a date/range for a private plan. If source dates changed, show the difference and let the user review their own plan.
3. **Edit/cancel.** Update the private plan; no feed/profile/venue audience receives it. There is no Share intention control in this beta. Organizer cancellation updates source information, not proof that the user changed plans.
4. **After visiting.** A separate Add jump action can suggest a location that the jumper checks. The plan never creates or pre-confirms a completed jump. Past plans never imply current presence.

Shared future intentions are deferred to #159, outside the beta dependency graph.

## J6 — Report/correct and review as maintainer

1. **On a listing, post or profile → Report.** Show the target, reason, optional explanation and send/cancel. Distinguish incorrect event/location information from social abuse. State who reviews the report, without promising an unvalidated response time.
2. **Submit.** Authenticate for in-app report tracking; guests can use a minimal correction submission route with abuse controls. A report acknowledgement means received, not reviewed/resolved. A failed acknowledgement is not a resolution claim.
3. **Owner's review queue.** Separate listing corrections from profile/post reports. Show relevant source/target/reason/history, restrict access by role, and allow a reviewer to record a decision. Do not expose unrelated private logs, serials or the reporter's identity on public screens.
4. **Review action.** Correct/retire/merge a listing with provenance; hide reported shared content or restrict publishing with a recorded reason. A listing merge preserves jump references without exposing them. Notify/display reporter status only in the authorized report view; no email/push promise is implied.
5. **Capacity unavailable.** Pause new public publishing or submissions as needed and explain the temporary limit. Keep personal records and export usable. A queue does not replace the owner's agreed maintenance routine.

## J7 — Export, restore, and recover access

1. **Profile → Your data → Export.** Show included personal records/references and privacy implications. Produce an authenticated, owner-scoped download; never a public URL. Show In progress, Ready, or Failed without pretending an empty file is a successful backup.
2. **Restore → Select file.** Explain that the beta supports this app's structured export, not FlySight/GPX/FIT or unrelated logbooks. Check format/version/limits and file content before writes. Unsupported or invalid input shows a useful explanation without applying partial silent changes.
3. **Review counts and eligibility.** Restore is supported into empty personal records only. Show records/baseline/reference counts before writes. An exact repeat of a completed restore shows Already restored without reapplying; it never overwrites later edits or refills deletions. A different archive into nonempty records is rejected before mutation, with existing records still readable/exportable. Do not suggest deleting existing records as a workaround. General merge/conflict selection is deferred.
4. **Confirm and result.** Show actual restored counts or the already-restored receipt. Personal records and baseline remain owner-scoped; restoring never republishes posts or restores other people's follow approvals. External canonical venues may be resolved, but no public venue/profile/listing is created automatically from a backup.
5. **Session expiry.** Hide private content and request sign-in. Returning to the same authenticated account can resume a safe workflow; switching accounts discards the prior account's in-memory private state. Do not automatically restore into a newly signed-in different account.
6. **Account recovery.** Generic acknowledgement must not reveal whether an email exists. A reset link may be invalid/expired/used; offer request-new-link and return-to-sign-in. Password reset is not a completed restore and does not guarantee recovery of an export never downloaded.

Recovery and export cannot depend on a contribution, public profile, following anyone, a participating DZ, or provider registration. Account-deletion confirmation explains which owned records/publications will be removed and what backup-retention delay applies after #143 defines it; do not invent a retention duration here.

## Shared state and accessibility contract

| State/interaction | Expected behavior |
| --- | --- |
| Loading vs empty | Distinct labels; retain safe prior list context and avoid representing an unfinished request as zero results |
| Lost connection | Show disconnected/unsaved/unconfirmed appropriately; no automatic success, durable offline-sync promise, or duplicate writes |
| Session expired | Hide private records; safe return after authentication with explicit account identity checks |
| Removed/inaccessible content | Generic unavailable view for other users; no cause-specific privacy disclosures |
| Validation | Persistent labels, required/optional markers, field errors and an error summary; focus the first relevant problem |
| Saving | Disable repeated submission while pending and show progress; confirmed, uncertain and rejected outcomes are distinct |
| Touch/keyboard | Proposed 44 CSS-pixel primary target minimum, visible focus, logical tab order, operable filters/menus and no hover-only actions; validate rather than claim conformance |
| Phone layout | Review at 320/360/390 CSS-pixel widths, larger text/zoom and an open keyboard; actions remain reachable without horizontal form scrolling or covering focused fields |
| Drawers/dialogs | Announce title/purpose, manage focus, restore it to the trigger, provide a visible close/cancel, and keep destructive confirmation explicit |
| Status communication | Text/icons as well as color; announce errors and save results without stealing focus during ordinary list refreshes |
| Safe defaults | No automatic geolocation, contacts access, profile publication, private-note sharing, or current-gear attribution |
| Browser back/external return | Preserve safe search/list state; warn about leaving unsaved forms; do not expose private form values in return URLs |

These are design requirements. Screen-reader operation, actual tap targets, zoom, keyboard avoidance and mobile browser behavior require later implementation/device checks. The clickable mockup itself is not evidence that the application meets them.

## Walkthrough review and implementation handoff

Review artifact produced: seven reconciled journey specifications, screen inventory, clickable phone mockup and error/privacy matrix. Delegated expert product review accepts this planning baseline. #141/#142 can close for scope/design preparation; representative-user walkthrough and device acceptance remain **not performed** and are release evidence in #160. This is not a fabricated owner task test or application acceptance.

Suggested review tasks:

- Find an event as a guest, save it after login and explain why you are not registered.
- Record two jumps at a missing DZ using unknown gear; explain which data stays private and what the total counts.
- Publish only one selected summary to approved followers, then remove access and inspect its direct link/DZ view.
- Approve a follow and save/edit/cancel a private visit plan without publishing an intention or creating a jump.
- Report a source correction and shared-content problem; explain what the maintainer can see.
- Export, review a repeated restore, and recover an expired session without creating duplicates or switching private account context.

For each task, record completion/hesitation, misunderstanding, inaccessible interaction and an explicit keep/change decision. No task timing, usability success rate, retention benefit or owner sign-off is fabricated.

Handoff to #143 must settle: safe route/return rules; authentication and account-switch behavior; date/units representation; idempotent saves and uncertain results; audiences and shared-card withdrawal; deletion/backup expiry; canonical/provisional reference resolution; empty-record restore, exact-repeat acknowledgement and atomicity; moderation permissions; and measured limits/hosting behavior. API paths, database schema and Svelte components are intentionally not designed as implementation code here.
