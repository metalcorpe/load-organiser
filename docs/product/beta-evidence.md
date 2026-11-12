# Beta verification evidence (#160)

Recorded 2026-11-06 on `feat/160-beta-verification`. Every automated check below ran with
`scripts/verify.sh backend web e2e` against disposable local PostgreSQL 17 databases, the
SvelteKit production build in `workerd` (Wrangler preview, HTTPS with the production
`__Host-` session cookie) and an isolated FastAPI process. Nothing was deployed and no
real person's data was used.

Results of that run: backend 474 passed; web check clean, unit 97 passed; end-to-end 234
passed (78 tests × 3 browser projects).

Browser projects: **Pixel 7** (Chromium, Android viewport/touch/UA), **iPhone 13**
(Playwright WebKit 27.2, iPhone viewport/touch/UA) and **Chromium at 320 px** with touch.
These are emulations, not the devices themselves (see "Not yet verified").

## Acceptance criteria and evidence

### 1. Guest discovery, organiser link, save/login return, plans, provisional-DZ logging

| Journey | Evidence |
| --- | --- |
| Guest dated-opportunity discovery and sourced external organiser link without an account | e2e `discover`: "a guest filters the board and opens a sourced listing"; `directory`: alias search, merged redirect, closed/draft visibility |
| Save, sign-in and return to the same listing | e2e `discover`: "sign in to save returns to the listing and saves only on request"; `auth`: "sign-in returns to the saved deep link" |
| Private visit plans | backend `test_saves.py` (plan lifecycle, owner-only, limits); no plan e2e journey |
| Logging at a private (provisional) place with unknown gear and an optional new component | e2e `logbook`: "log a jump at an unlisted place with a new component, without gear setup"; listed-DZ search; duplicate warning |

### 2. History baseline, export and restore

| Behaviour | Evidence |
| --- | --- |
| Cutoff and double counting, too many pre-cutoff entries flagged, corrections | backend `test_history.py` (decision fixture B=200, flagged not rejected, compare-and-swap corrections with provenance); e2e `history` (3 tests) |
| Export and restore into an empty account; exact repeat acknowledged with no writes | backend `test_records.py` round trip and exact repeat; e2e `records` |
| Non-empty records rejected with no mutation; malformed, oversized and partial failures roll back | backend `test_records.py` (non-empty refusal before any write, malformed/oversized bodies, failure part way, write landing during restore) |

### 3. Profiles, follows, posts, feed and dropzone activity

| Behaviour | Evidence |
| --- | --- |
| Profiles and approved follows, blocks, reports and reviewer hiding | backend `test_social.py`; e2e `social` (2 tests) |
| Selected cards, private-only versus shared-field edits, unpublish, audience narrowing | backend `test_posts.py` (13 tests incl. withdrawal per shared part, discoverability-off withdrawal, reviewer removal); e2e `posts` test 1 |
| Feed and dropzone activity, revocation by unpublish, narrowing, follower removal and blocks | backend `test_posts.py` feed and dropzone tests; e2e `posts` test 2 |

No shared future-intention flow exists (#159 deferred).

### 4. Walkthrough and device checks

| Item | Evidence |
| --- | --- |
| Direct links on every private path redirect to sign-in without private HTML | e2e `shell`: one test per private path, including `/jumps/{id}/share` |
| Small screens: 44 px targets, no horizontal scroll | e2e `shell` on all three projects |
| Keyboard: skip link first and focuses main | e2e `shell` with Tab in Chromium; in WebKit only with Option+Tab (see findings) |
| No-friends first use | e2e `posts` test 2 (empty feed with people search, profile and discovery links) |
| Failed or unconfirmed saves | e2e `discover` and `directory` (unconfirmed accounts), `auth` (unconfirmed writes blocked); older-tab conflicts in `gear`, `logbook`, `history`, `maintenance` |

### 5. Access boundaries, sessions and payloads

| Item | Evidence |
| --- | --- |
| Anonymous, owner, other user and reviewer on every parameterised route | backend `test_access_matrix.py`: the owner creates one of each private record (place, component, service entry, rig, jump, plan, follower-only post, non-discoverable profile). Every parameterised operation in the app's OpenAPI document except public catalogue and caller-scoped routes is called with the owner's ids by another verified user, a reviewer (except reviewer tools, which members and guests are refused) and anonymously. Writes carry a valid body with the owner's current versions, so validation cannot answer before ownership does. Each answer is 401/403/404, equals the answer for a nonexistent id, and echoes no private text; the owner's records are unchanged and no report or follow was created. The public dropzone post list is checked separately: it answers 200 without the owner's follower-only post. New routes are included automatically; an unmapped parameter or write body fails the test. |
| Anonymous on every route without a parameter | backend `test_access_matrix.py` `test_collection_routes_refuse_anonymous_callers` (added 2026-11-11): every such operation in the OpenAPI document, including `/plans`, `/records`, `/records/export` and `/records/restore`, answers 401 without a session and echoes no private text. Only the explicit public list is exempt: registration, sign-in, email confirmation, password reset, sign-out, health, listings, covered countries and the dropzone list. New routes are included automatically. |
| Session expiry, revocation and account switching | e2e `auth`: sign-out revocation and back navigation, switching accounts in one browser, two browsers with separate identities, forged or stale cookie, reset revokes other sessions, sign out everywhere. Added 2026-11-11: after switching, the first account's jump note, place and plan appear in neither the HTML nor the `__data.json` of `/jumps`, `/places`, `/plans`, `/records`, `/history`, `/activity` and `/saved`, and the second account's logbook shows its own empty state |
| Origin enforcement | e2e `auth`: cross-site, `null` and absent Origin refused on sign-in; cross-site sign-out ignored. e2e `boundaries`: cross-site POST to the JSON export route refused with a valid session cookie |
| Cache and HTML/data payload boundaries | Pages: `no-store` set in `hooks.server.ts` for every response and checked by the `shell` headers test; since 2026-11-11 also asserted, signed in, on every private page and its `__data.json` (e2e `auth` "signed-in private pages and their data are never cached"). API: each beta router adds `no-store` through a router dependency; no test enumerates every API response. e2e `boundaries`: the raw HTML and `__data.json` of a public post and profile (both 200 and both carrying the caption), read signed out and as another user, contain neither the place name, notes, other equipment nor account email, nor the field names of private values; the owner's jump page data contains those values for the owner and is not served without a session (303) |

## Findings from this run

- **WebKit (iPhone emulation) passes the full suite** with two engine-specific
  adjustments, neither an application change:
  - **Keyboard focus:** in WebKit the test presses Option+Tab, because by default Tab
    there (as in Safari on macOS) skips links. Verified: the skip link is the first link
    and moves focus to the main content. Not verified: what a Safari user with default
    settings and a hardware keyboard reaches with Tab alone (likely form controls only),
    which is browser behaviour rather than something the page can change.
  - **Sign-out headers:** WebKit's network instrumentation omits `Clear-Site-Data` and
    `Set-Cookie` from the sign-out redirect it reports; its trace shows only `Location`
    and `Cache-Control`. The server sets the header the same way for every browser
    (`hooks.server.ts`), and the cookie removal, server-side revocation and
    back-navigation checks pass in WebKit. Whether Safari itself honours
    `Clear-Site-Data: "cache"` is not verified. Private pages are `no-store` regardless.
- **No material failure was found by the automated checks** in the 2026-11-06 run.

## Re-run 2026-11-11 (after the design E pages)

Checks added for gaps found by mapping each criterion to its tests, highest privacy risk
first. Results: backend 548 passed; e2e passed on all three projects (see the pull
request for the full gate).

- **Material failure found and fixed: two different files restored at once merged.**
  Both restores passed the emptiness check before either committed; each recount saw
  only its own rows and the receipts did not conflict, so both committed and the account
  held two archives' records. That breaks "restore into empty records only, never
  merge". Test: `test_records.py` `test_two_different_files_restored_at_once_never_merge`
  holds both restores at the recount, then requires one `restored`, one refused as not
  empty, one archive's rows and one receipt. It failed before the fix (`['restored',
  'restored']`). Fix, without locks: each restore reads its person's next receipt
  sequence before the emptiness check, and `(owner, sequence)` is unique (migration
  `b9e4d1a7c3f5`). The loser rolls back and gets "already restored" for the same file,
  or "records not empty" for a different one.
- **Minor ordering fix:** resending the confirmation email checked that mail was
  configured before checking the session, so a caller without a session could learn
  that mail was down. The session is now checked first.
- No other failure found.

Still covered by backend tests only, judged lower risk because pages are rendered per
request and `no-store`: blocking's effect on posts and the feed, and turning
discoverability off. Not added: null or absent Origin on authenticated form actions
other than sign-in (one central check, unit tested), a "starts today" listing case, a
private save while the API is down, a dedicated first-use test of `/people`, `/plans`,
`/gear` and `/records`, and automated accessibility (axe) checks.

## Not yet verified (needs people or devices)

- **Real devices:** iPhone Safari and Android Chrome. Emulation does not cover real
  keyboards, autofill, OS text size, safe areas, back-forward cache or network
  conditions.
- **Safari keyboard defaults:** Tab-only navigation in real Safari, with and without
  "Press Tab to highlight each item".
- **Owner walkthrough:** a representative walkthrough by the owner and at least one other
  user of the journeys above, with notes. Earlier design acceptance does not count.
- **Assistive technology:** screen-reader runs (VoiceOver, TalkBack). Automated checks
  cover labels, roles, focus order and target size only.
- **Concurrency:** races that the compare-and-swap design argues are safe, for example
  publish versus edit, are reasoned about rather than forced by tests. Restore is now
  forced for an injected write and for two simultaneous restores.
- **Production hosting:** cookies, Origin and caching on the real host (#161).

## Owner checklist for real devices

For the iPhone (Safari) and Android (Chrome) pass. Use a fresh account and the local
stack or a test host, never real records. Note the device, OS and browser version, and
anything that fails.

1. **Signed out:** open a listing from a shared link, then the organiser link; save it,
   sign in in the sheet, and check you return to the same listing and it saves only
   when you press save.
2. **First use:** with a new account, open Logbook, Friends, Me and Your data. Each
   empty page should say what to do next.
3. **Log a jump** at a place that is not listed, with gear you have not set up. Turn on
   airplane mode before pressing save and note what happens. Expected: what you typed
   is kept and the page says the jump was not saved. Untested: no automated test
   covers a save while offline.
4. **Text size:** set the largest system text size and repeat step 3. Nothing should be
   cut off or need sideways scrolling.
5. **Autofill and keyboard:** sign in with the password manager. On iPhone with a
   hardware keyboard, check Tab with and without Safari's "Press Tab to highlight each
   item".
6. **Back and forward:** sign out, then press Back. No private page may reappear.
7. **Sharing:** share a jump to followers, view it from a second account that follows
   you, then narrow it to private and reload on the second device.
8. **Screen reader:** VoiceOver (iPhone) and TalkBack (Android): the tab bar, the sign-in
   sheet (opens, Escape or Back closes it), a jump form, and a listing card.
9. **Export and restore:** export on the phone, then restore the file into a new empty
   account from the phone's file picker.

# Beta content, moderation and feedback (#162)

Status recorded 2026-11-12. "Built" means implemented and tested; it says nothing about
real use. Nothing here has been run with real listings or real users.

| Criterion | Status | Evidence, or what is needed |
| --- | --- | --- |
| Real listing coverage | **Owner** | The researched Greece, Bulgaria, Spain and Portugal records are development data only (`scripts/dev.sh seed`, beta decisions 2026-11-09). Before beta the owner publishes a reviewed subset on the real host (#161) and records country/category coverage, gaps and time spent (release brief, "Maintenance cadence"). |
| Maintainer ownership | Decided | The owner is the only maintainer and report reviewer (beta decisions). The reviewer role is granted by an operator command, not a screen. |
| Stale content | Built | Ended listings leave upcoming results by their own time zone (`test_opportunities.py`). Maintenance shows listings, organisers and dropzones due a check on the weekly/60-day routine (e2e `maintenance`). Undated profiles are not published in this beta (#206), so the 90-day recheck label has nothing to apply to yet. |
| Abuse reports | Built | Reports on posts and profiles, reviewer decisions with hide/restrict (`test_social.py`, `test_posts.py`, e2e `social`); reports on listings, organisers and dropzones through `/submit` (`test_moderation.py`). |
| Feedback route | Built | `/submit` "Feedback about the beta"; the sender sees status and the reviewer's note. |
| Pausing when the queue outgrows the owner | Built | Submissions: `SKYDIVER_SUBMISSIONS_OPEN`. Publishing: `SKYDIVER_PUBLISHING_OPEN` (added 2026-11-12, `test_posts.py` `test_a_publishing_pause_stops_new_disclosure_only`); narrowing, unpublishing, logging and export stay available. Registration: `SKYDIVER_REGISTRATION_OPEN` and `SKYDIVER_MAX_ACCOUNTS`. All closed by default. |
| Privacy, sharing and retention expectations; known limits; export and recovery instructions | Built | `/privacy` sections "What you can share", "Deleting your account", "Export and restore", "Backups and recovery" and "Known limits". The backup schedule it describes depends on hosting (#161). |
| Optional support link; costs disclosed; no invented funding account | Built, **owner** | `/support` links the owner-supplied Ko-fi page and lists running costs (none yet, `web/src/lib/support.ts`). The owner is checking with an accountant before the link is used publicly. |
| Bounded cohort; repeat activity observed; feedback recorded | **Owner** | Cohort: the owner alone (beta decisions 2026-11-09). Observation and feedback need real use on a host; no success metric or launch date is set. |
| A real review cycle and its actual time | **Owner** | Not done. Needs published listings and a week of the routine. |
