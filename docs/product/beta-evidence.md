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
| Keyboard: skip link first and focuses main | e2e `shell`; WebKit uses Option+Tab, as Safari on macOS does |
| No-friends first use | e2e `posts` test 2 (empty feed with people search, profile and discovery links) |
| Failed or unconfirmed saves | e2e `discover` and `directory` (unconfirmed accounts), `auth` (unconfirmed writes blocked); older-tab conflicts in `gear`, `logbook`, `history`, `maintenance` |

### 5. Access boundaries, sessions and payloads

| Item | Evidence |
| --- | --- |
| Anonymous, owner, other user and reviewer on every parameterised route | backend `test_access_matrix.py`: the owner creates one of each private record (place, component, service entry, rig, jump, plan, follower-only post, non-discoverable profile). Every parameterised operation in the app's OpenAPI document is called with the owner's ids by another verified user, a reviewer (except reviewer tools) and anonymously: none succeeds or echoes private text, and the owner's records are unchanged. New routes are included automatically; an unmapped parameter fails the test. |
| Session expiry, revocation and account switching | e2e `auth`: sign-out revocation and back navigation, switching accounts in one browser, two browsers with separate identities, forged or stale cookie, reset revokes other sessions, sign out everywhere |
| Origin enforcement | e2e `auth`: cross-site, `null` and absent Origin refused on sign-in; cross-site sign-out ignored. e2e `boundaries`: cross-site POST to the JSON export route refused with a valid session cookie |
| Cache and HTML/data payload boundaries | `no-store` on every page and API response (`shell` headers test; API `no_store` dependencies). e2e `boundaries`: the raw HTML and `__data.json` of a public post and profile, read signed out and as another user, contain the shared caption and never the place name, notes, other equipment, jump number or account email; the owner's private jump page data is not served without a session |

## Findings from this run

- **WebKit (iPhone emulation) passes the full suite.** Two tests needed engine-specific
  handling, neither an application change:
  - **Keyboard focus:** WebKit moves focus to links with Option+Tab, not Tab (Safari's
    default on macOS). The skip link works with that key.
  - **Sign-out headers:** WebKit's network instrumentation omits `Clear-Site-Data` and
    `Set-Cookie` from the sign-out redirect it reports; its trace shows only `Location`
    and `Cache-Control`. The server sets the header the same way for every browser
    (`hooks.server.ts`), and the cookie removal, server-side revocation and
    back-navigation checks pass in WebKit. Whether Safari itself honours
    `Clear-Site-Data: "cache"` is not verified. Private pages are `no-store` regardless.
- **No material failure was found by the automated checks.**

## Not yet verified (needs people or devices)

- **Real devices:** iPhone Safari and Android Chrome. Emulation does not cover real
  keyboards, autofill, OS text size, safe areas, back-forward cache or network
  conditions.
- **Owner walkthrough:** a representative walkthrough by the owner and at least one other
  user of the journeys above, with notes. Earlier design acceptance does not count.
- **Assistive technology:** screen-reader runs (VoiceOver, TalkBack). Automated checks
  cover labels, roles, focus order and target size only.
- **Concurrency:** races that the compare-and-swap design argues are safe, for example
  publish versus edit and restore versus concurrent writes beyond the injected-write
  test, are reasoned about rather than forced by tests.
- **Production hosting:** cookies, Origin and caching on the real host (#161).
