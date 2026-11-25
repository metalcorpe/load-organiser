# Graphite Look (Design H) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the E/G surface treatment with graphite (dark) and a matching neutral light theme: no decorative outlines, cards lifted by shade or shadow, a floating rounded tab bar on phones with a neutral active pill.

**Architecture:** Colours and elevation live in Style Dictionary tokens (`web/src/lib/design/tokens/{shared,light,dark}.json` → generated `tokens-*.css`). Components switch decorative borders to `transparent` (kept for forced colours) and cards gain `--shadow-card`. The tab bar (`AppNav.svelte`) floats on phones; one CSS custom property, `--nav-clearance`, replaces four hand-kept clearance values.

**Tech Stack:** SvelteKit 3 / Svelte 5, plain scoped CSS, Style Dictionary 5 (DTCG), vitest + colorjs.io contrast spec, Playwright e2e (pixel-7, iphone-13, chromium-320, desktop projects).

**Spec:** `docs/superpowers/specs/2026-11-25-graphite-look-design.md`; approved mockup `docs/product/mockups/graphite-look.html`.

## Global Constraints

- web/ has no formatter: never run prettier or eslint. Tabs, single quotes, match surrounding style by hand.
- WCAG 2.1 AA: text 4.5:1, non-text edges, focus rings and the active pill 3:1 — in light and dark.
- Fields keep `--field-border` as a visible edge; no new field token.
- Decorative borders become `transparent`, never removed (box size unchanged; forced colours draw them).
- Kept visible: field edges, warning/semantic borders (`app.css:421`), meaning-carrying side rules (`DueList.svelte:44`), in-card row dividers, hover outlines (`ListingItem.svelte:75`, retuned).
- Active tab: neutral filled pill (dark: light pill, dark text; light: dark pill, white text). The orange active-tab bar is removed. Owner confirmed 2026-11-25.
- Large screens (≥48rem): nav stays a static top bar; new colours and the same pill; does not float.
- Floating bar (phones): inset `max(12px, env(safe-area-inset-left/right))`, bottom `12px + env(safe-area-inset-bottom)`, radius 20px, no safe-area padding inside the bar; `viewport-fit=cover` in `app.html`.
- Targets 44px; no layout, copy, font or navigation changes.
- Values to match: dark `bg #111214`, `surface #1c1d21`; light `bg #f5f5f7`, `surface #ffffff` (others tuned to pass contrast).

## Review Focus

1. 320px phone at 200% text size: the narrower floating bar must still keep every tab label whole and 44px tall (Task 3 test).
2. Landscape iPhone with side safe-area insets: the bar must stay inside the insets (Task 3 test checks left/right ≥ 12px in a 844×390 viewport).
3. Windows high contrast (forced colours): cards keep a visible edge and the active tab stays marked (Task 2 and Task 3 tests with `emulateMedia({ forcedColors: 'active' })`).
4. The last thing on a long page (footer links) must scroll fully clear of the floating bar (Task 3 test).
5. Browsers without `backdrop-filter`: the bar must stay readable — contrast is tested on the opaque `nav-bg` (Task 1), translucency only inside `@supports`.

---

### Task 1: Graphite tokens

**Files:**
- Modify: `web/src/lib/design/tokens/light.json`, `dark.json`, `shared.json`
- Regenerate: `web/src/lib/design/tokens-{light,dark}.css`, `tokens-{light,dark}-forced.css` (`npm run tokens:build`)
- Test: `web/src/lib/design/tokens.spec.ts`

**Interfaces:**
- Produces CSS custom properties used by Tasks 2–4: `--nav-bg`, `--nav-pill`, `--nav-pill-fg`, `--shadow-card` (plus new values for every existing token). `--shadow-card` must be a valid `box-shadow` value in both themes.

- [ ] **Step 1: Add the failing contrast pairs and a shadow check**

Append to `PAIRS`:
```ts
['fg', 'nav-bg', 4.5],
['muted', 'nav-bg', 4.5],
['nav-pill-fg', 'nav-pill', 4.5],
['nav-pill', 'nav-bg', 3],
['focus', 'nav-bg', 3],
['focus', 'nav-pill', 3],
```
Add:
```ts
describe('elevation', () => {
	for (const theme of ['light', 'dark']) {
		it(`${theme}: --shadow-card is generated`, () => {
			expect(readFileSync(`src/lib/design/tokens-${theme}.css`, 'utf8')).toMatch(/--shadow-card: [^;]+;/);
		});
	}
});
```

- [ ] **Step 2: Run, expect failures** — `cd web && npx vitest run src/lib/design/tokens.spec.ts` → FAIL (missing `nav-bg` etc.).

- [ ] **Step 3: Set the values.** Both files: new `bg`, `surface`, `surface-soft`, `fg`, `muted`, `border`, `field`, `field-border`, and retune `accent` (dark may move to `#ff7a45`), `accent-soft`, `focus`, `brand` (dark: deep graphite, light: near-black), `brand-fg`, `brand-muted`, `highlight`, the event-type, warn/ok/bad pairs. Dark `field` is no longer navy. Add `nav-bg` (opaque), `nav-pill`, `nav-pill-fg`, `shadow-card` (light: two-layer soft shadow like `0 1px 2px rgb(0 0 0 / 4%), 0 6px 20px rgb(0 0 0 / 6%)`; dark: `inset 0 1px 0 rgb(255 255 255 / 5%)`). Use DTCG `"$type": "shadow"` if Style Dictionary's `css` transform group emits a valid shorthand; otherwise a plain string value without `$type`. `$description` of each file: "Design H (graphite), chosen by the owner on 2026-11-25."

- [ ] **Step 4: Build and test** — `npm run tokens:build && npx vitest run src/lib/design/tokens.spec.ts` → PASS (all pairs, both themes, generated-output check).

- [ ] **Step 5: Commit** — `git commit -m "feat(design): graphite tokens (design H)"`

### Task 2: Surfaces without decorative outlines

**Files:**
- Modify: `web/src/app.css` (`.card` at :523, chips, panels, dividers), and the components/routes among the 33 files using `var(--border)` (`git grep -l 'var(--border)' -- web/src`), plus the 8 `var(--brand)` consumers checked for look (`+layout.svelte`, `ExploreSwitch`, `FeaturedListing`, `events/[id]`, `(private)/jumps`, `(private)/jumps/[id]`, `(private)/profile`, `(private)/history`).
- Test: `web/tests/layout.e2e.ts`

**Interfaces:**
- Consumes: `--shadow-card`, new palette (Task 1).

- [ ] **Step 1: Write the failing test** in `layout.e2e.ts`:

```ts
test.describe('graphite surfaces', () => {
	test('a listing card has no visible outline but a shadow, in light', async ({ page }) => {
		await page.emulateMedia({ colorScheme: 'light' });
		await page.goto('/');
		const card = page.locator('.card').first();
		const style = await card.evaluate((el) => {
			const s = getComputedStyle(el);
			return { color: s.borderTopColor, width: s.borderTopWidth, shadow: s.boxShadow };
		});
		expect(style.color).toBe('rgba(0, 0, 0, 0)');
		expect(style.width).toBe('1px');
		expect(style.shadow).not.toBe('none');
	});

	test('in forced colours the card keeps a drawn edge', async ({ page }) => {
		await page.emulateMedia({ forcedColors: 'active' });
		await page.goto('/');
		const color = await page.locator('.card').first().evaluate((el) => getComputedStyle(el).borderTopColor);
		expect(color).not.toBe('rgba(0, 0, 0, 0)');
	});
});
```
(If `.card` is not the listing card's class on `/`, use the class `ListingItem.svelte` renders; the forced-colours test is Chromium-only: `test.skip(browserName !== 'chromium')`.)

- [ ] **Step 2: Run, expect failure** — `E2E_ARGS="tests/layout.e2e.ts" scripts/verify.sh e2e` (with the `PG_BIN`/port variables from the README) → the light test FAILS on border colour.

- [ ] **Step 3: Implement.** For each `var(--border)` use, decide: decorative card/chip/panel edge → `border-color: transparent` (cards also `box-shadow: var(--shadow-card)`); in-card row divider → keep `var(--border)`; shadow/gradient uses → retune or keep. Leave the kept-visible list in Global Constraints alone. Check each `var(--brand)` consumer still reads well.

- [ ] **Step 4: Run** the same command → PASS; `npm run check` → 0 errors.

- [ ] **Step 5: Commit** — `git commit -m "feat(design): cards and chips lift by shade, not outline"`

### Task 3: Floating tab bar with neutral pill

**Files:**
- Modify: `web/src/lib/components/AppNav.svelte`, `web/src/app.css:23` (scroll padding), `web/src/routes/+layout.svelte:278-281` (footer clearance), `web/src/routes/+page.svelte:420-429` (Apply bar, scroll padding), `web/src/app.html:5`
- Test: `web/tests/layout.e2e.ts` (new phone describe), existing `discover.e2e.ts:849`, `layout.e2e.ts:25`, `shell.e2e.ts:49` unchanged

**Interfaces:**
- Consumes: `--nav-bg`, `--nav-pill`, `--nav-pill-fg` (Task 1).
- Produces: `--nav-clearance` on `:root` in `app.css`: `calc(var(--nav-height) + 12px + env(safe-area-inset-bottom))` on phones, used by every clearance rule; `0px` at ≥48rem.

- [ ] **Step 1: Write the failing tests** (phone projects only: `test.skip(!isMobile)` or a 390×844 viewport; sign in with `createAccount` + the sign-in form as in `discover.e2e.ts:849`):

```ts
test('the tab bar floats inside the screen edges', async ({ page }) => {
	// signed in, at '/'
	const nav = (await page.getByRole('navigation', { name: 'Primary' }).boundingBox())!;
	const vp = page.viewportSize()!;
	expect(nav.x).toBeGreaterThanOrEqual(12);
	expect(vp.width - (nav.x + nav.width)).toBeGreaterThanOrEqual(12);
	expect(vp.height - (nav.y + nav.height)).toBeGreaterThanOrEqual(12);
});

test('in landscape the bar stays inside the side insets', async ({ page }) => {
	await page.setViewportSize({ width: 844, height: 390 });
	// same three assertions
});

test('the active tab is a pill, marked in forced colours too', async ({ page }) => {
	const current = page.locator('nav[aria-label="Primary"] a[aria-current="page"]');
	expect(await current.evaluate((el) => getComputedStyle(el).backgroundColor)).not.toBe('rgba(0, 0, 0, 0)');
	await page.emulateMedia({ forcedColors: 'active' }); // chromium only
	expect(await current.evaluate((el) => getComputedStyle(el).backgroundColor)).not.toBe('rgba(0, 0, 0, 0)');
});

test('the footer scrolls fully clear of the tab bar', async ({ page }) => {
	await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
	const last = (await page.locator('footer a').last().boundingBox())!;
	const nav = (await page.getByRole('navigation', { name: 'Primary' }).boundingBox())!;
	expect(last.y + last.height).toBeLessThanOrEqual(nav.y);
});

test('at 320px and 200% text every tab label stays whole and 44px tall', async ({ page }) => {
	await page.setViewportSize({ width: 320, height: 640 });
	await page.addStyleTag({ content: 'html { font-size: 200% }' });
	for (const tab of await page.locator('nav[aria-label="Primary"] a').all()) {
		const box = (await tab.boundingBox())!;
		expect(box.height).toBeGreaterThanOrEqual(44);
		const span = tab.locator('span');
		expect(await span.evaluate((el) => el.getClientRects().length)).toBe(1);
	}
});
```

- [ ] **Step 2: Run, expect failures** — `E2E_ARGS="tests/layout.e2e.ts" scripts/verify.sh e2e` → the float and pill tests FAIL.

- [ ] **Step 3: Implement.** `app.html`: `content="width=device-width, initial-scale=1, viewport-fit=cover"`. `app.css`: define `--nav-clearance` and use it for `scroll-padding-bottom`. `AppNav.svelte` phones: `inset: auto max(12px, env(safe-area-inset-right)) calc(12px + env(safe-area-inset-bottom)) max(12px, env(safe-area-inset-left))`, `border-radius: 20px`, `background: var(--nav-bg)`, `border: 1px solid transparent`, no `padding-bottom`; `@supports (backdrop-filter: blur(12px))` adds translucency. Active `a[aria-current='page']`: pill `background: var(--nav-pill); color: var(--nav-pill-fg); border-radius: 14px`, remove the orange gradient bar; `@media (forced-colors: active) { a[aria-current='page'] { forced-color-adjust: none; background: Highlight; color: HighlightText; } }`. ≥48rem: static top bar as today, `background: var(--nav-bg)`, same pill. Footer and Discover Apply bar and Discover scroll padding use `--nav-clearance`.

- [ ] **Step 4: Run** `E2E_ARGS="tests/layout.e2e.ts tests/discover.e2e.ts tests/shell.e2e.ts" scripts/verify.sh e2e` → PASS on all projects.

- [ ] **Step 5: Commit** — `git commit -m "feat(nav): floating tab bar with a neutral active pill"`

### Task 4: Storybook, docs and full gate

**Files:**
- Modify: `web/src/lib/design/Foundations.mdx:80` (keep `ColorItem` to colour tokens; add a `shadow-card` sample), `web/src/lib/design/README.md` (design H), `docs/product/mobile-journeys.md:11` ("design H replaced E/G on 2026-11-25")

- [ ] **Step 1:** Update the three files.
- [ ] **Step 2: Full gate** — `PG_BIN=/opt/homebrew/opt/postgresql@17/bin VERIFY_PG_PORT=<free> VERIFY_API_PORT=<free> scripts/verify.sh backend web storybook e2e` → exit 0 (axe light and dark included).
- [ ] **Step 3: Manual pass** on the local dev stack: Discover, an event page, a dropzone page, Logbook, Statistics, profile, review form at 320/390/768/1440 px, light and dark, Tab through the nav. Note anything untested.
- [ ] **Step 4: Commit** — `git commit -m "docs(design): design H in Storybook and product docs"`
