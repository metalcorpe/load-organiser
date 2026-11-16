import AxeBuilder from '@axe-core/playwright';
import { randomBytes } from 'node:crypto';
import { expect, test, type Page, type Request } from '@playwright/test';
import { PASSWORD, apiCall, createAccount, reviewerSession } from './support/accounts.ts';
import { SECURE_ORIGIN } from './support/origins.ts';

// The Map view of the dropzone directory (/dz?view=map). Tiles are never fetched from the real
// OpenStreetMap servers here: every tile request is answered with a 1x1 PNG.
const ORIGIN = SECURE_ORIGIN;
test.use({ baseURL: ORIGIN, ignoreHTTPSErrors: true });

const SOURCE = { source_url: 'https://example.org/dz-map', checked_on: '2026-11-01' };
const TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];
const PNG = Buffer.from(
	'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGO4e/fufwAIyQOXr/3newAAAABJRU5ErkJggg==',
	'base64'
);
const TILES = 'https://tile.openstreetmap.org/**';

interface Venue {
	id: string;
	name: string;
}

interface World {
	base: string;
	alpha: Venue;
	beta: Venue;
	closed: Venue;
	unplaced: Venue;
}

async function venue(reviewer: string, body: Record<string, unknown>): Promise<Venue> {
	const response = await apiCall('POST', '/directory/venues', {
		bearer: reviewer,
		body: { country: 'IS', ...SOURCE, ...body }
	});
	expect(response.status).toBe(201);
	return (await response.json()) as Venue;
}

/** Three Icelandic dropzones far enough apart not to cluster, and one without coordinates. */
async function world(): Promise<World> {
	const reviewer = await reviewerSession();
	const base = `Zm${randomBytes(5).toString('hex')}`;
	const alpha = await venue(reviewer, {
		name: `${base} Alpha`,
		locality: 'Reykjavik',
		latitude: 64.13,
		longitude: -21.94
	});
	const beta = await venue(reviewer, {
		name: `${base} Beta`,
		locality: 'Akureyri',
		latitude: 65.66,
		longitude: -18.07
	});
	const closed = await venue(reviewer, {
		name: `${base} Gamma`,
		latitude: 63.42,
		longitude: -19.0
	});
	const status = await apiCall('POST', `/directory/venues/${closed.id}/status`, {
		bearer: reviewer,
		body: { status: 'closed' }
	});
	expect(status.status).toBe(200);
	const unplaced = await venue(reviewer, { name: `${base} Delta` });
	return { base, alpha, beta, closed, unplaced };
}

interface Seen {
	tiles: string[];
	referers: Set<string>;
	/** Requests to any other host than the site (tiles included, answered locally). */
	external: string[];
	/** The map's own point requests to the site. */
	points: string[];
	/** Stylesheets requested from the site. */
	stylesheets: string[];
}

/** Answer tile requests locally, and record every request that leaves for another host. */
async function stubTiles(page: Page): Promise<Seen> {
	const seen: Seen = { tiles: [], referers: new Set(), external: [], points: [], stylesheets: [] };
	await page.route(TILES, (route) => {
		seen.tiles.push(route.request().url());
		seen.referers.add(route.request().headers()['referer'] ?? '');
		return route.fulfill({ status: 200, contentType: 'image/png', body: PNG });
	});
	page.on('request', (request: Request) => {
		const url = new URL(request.url());
		if (url.protocol === 'data:' || url.protocol === 'blob:') return;
		if (url.origin !== ORIGIN) seen.external.push(url.href);
		else if (url.pathname === '/dz/points') seen.points.push(url.search);
		else if (request.resourceType() === 'stylesheet') seen.stylesheets.push(url.href);
	});
	return seen;
}

/** Whether one of these stylesheets is Leaflet's (with Leaflet.markercluster's), by its rules. */
async function leafletCssAmong(page: Page, urls: string[]): Promise<boolean> {
	for (const url of urls) {
		const css = await (await page.request.get(url)).text();
		if (css.includes('.leaflet-tile-pane') || css.includes('.leaflet-cluster-anim')) return true;
	}
	return false;
}

/** Whether Leaflet's own rules are applied to the page (the page's overrides do not count). */
const leafletCssApplied = (page: Page) =>
	page.evaluate(() =>
		[...document.styleSheets].some((sheet) =>
			[...sheet.cssRules].some(
				(rule) => rule instanceof CSSStyleRule && rule.selectorText.includes('.leaflet-tile-pane')
			)
		)
	);

const offSite = (seen: Seen) =>
	seen.external.filter((url) => !url.startsWith('https://tile.openstreetmap.org/'));

async function showMap(page: Page) {
	await page.getByRole('button', { name: 'Show map' }).click();
	await expect(page.getByTestId('dz-map')).toHaveAttribute('aria-busy', 'false');
	await expect(page.locator('.dz-marker').first()).toBeVisible();
}

async function violations(page: Page): Promise<string[]> {
	const result = await new AxeBuilder({ page }).withTags(TAGS).analyze();
	return result.violations.flatMap((v) =>
		v.nodes.map((n) => `${v.id} (${v.impact}): ${n.target.join(' ')} — ${v.help}`)
	);
}

let shared: World;
test.beforeAll(async () => {
	shared ??= await world();
});

test.describe('dropzone map', () => {
	// Every test: tiles answered locally, and nothing else may leave the site.
	let seen: Seen;
	test.beforeEach(async ({ page }) => {
		seen = await stubTiles(page);
	});
	test.afterEach(() => {
		expect(offSite(seen), 'requests to hosts other than the site and the tile host').toEqual([]);
	});

	test('the Map view asks first, then loads the map with markers', async ({ page }) => {
		const { base } = shared;
		const response = await page.goto(`/dz?q=${base}`);
		// Images from the site and the one tile host only; scripts and styles are untouched.
		const csp = response?.headers()['content-security-policy'] ?? '';
		expect(csp).toContain("img-src 'self' data: https://tile.openstreetmap.org;");
		expect(csp).toContain("script-src 'self'");
		expect(csp).toContain("connect-src 'self';");
		await page.getByRole('navigation', { name: 'Show dropzones as' }).getByRole('link', { name: 'Map' }).click();
		await expect(page).toHaveURL(`${ORIGIN}/dz?q=${base}&view=map`);

		// Nothing third-party before the choice: a note, a real button and a way back to the list.
		await expect(page.getByText('Map images come from the OpenStreetMap tile servers')).toBeVisible();
		const button = page.getByRole('button', { name: 'Show map' });
		await expect(button).toBeVisible();
		await expect(page.getByRole('main').getByRole('link', { name: 'View as list' })).toHaveAttribute(
			'href',
			`/dz?q=${base}`
		);
		await expect(page.getByTestId('dz-map')).toHaveCount(0);
		await expect(page.getByTestId('map-needs-js')).toHaveCount(0);
		expect(seen.external).toEqual([]);
		// The points are not loaded either until the choice, nor Leaflet's CSS (list or Map view).
		expect(seen.points).toEqual([]);
		expect(seen.stylesheets.length).toBeGreaterThan(0);
		expect(await leafletCssAmong(page, seen.stylesheets), 'Leaflet CSS before the choice').toBe(false);
		expect(await leafletCssApplied(page)).toBe(false);

		await showMap(page);
		expect(seen.points).toEqual([`?q=${base}&country=`]);
		// Leaflet's CSS came with the map, and styles it: panes stacked over the tiles.
		expect(await leafletCssApplied(page)).toBe(true);
		await expect(page.locator('.leaflet-container')).toHaveCSS('overflow', 'hidden');
		await expect(page.locator('.leaflet-tile-pane')).toHaveCSS('position', 'absolute');
		await expect(page.locator('.leaflet-tile-pane')).toHaveCSS('z-index', '200');
		const map = page.getByRole('region', { name: 'Map of 3 dropzones' });
		await expect(map).toBeVisible();
		await expect(map).toBeFocused();
		// Two listed and one closed, each a named button; the one without coordinates is not drawn.
		await expect(page.getByRole('button', { name: `${base} Alpha`, exact: true })).toBeVisible();
		await expect(page.getByRole('button', { name: `${base} Beta`, exact: true })).toBeVisible();
		await expect(page.getByRole('button', { name: `${base} Gamma (closed)` })).toHaveClass(
			/dz-marker-closed/
		);
		await expect(page.getByRole('button', { name: new RegExp(`${base} Delta`) })).toHaveCount(0);
		const attribution = page.locator('.leaflet-control-attribution');
		await expect(attribution.getByRole('link', { name: 'OpenStreetMap' })).toHaveAttribute(
			'href',
			'https://www.openstreetmap.org/copyright'
		);
		await expect(attribution).toContainText('© OpenStreetMap contributors');
		// A plain Leaflet credit, without the default prefix's flag.
		await expect(attribution.getByRole('link', { name: 'Leaflet' })).toHaveAttribute(
			'href',
			'https://leafletjs.com'
		);
		await expect(attribution.locator('svg')).toHaveCount(0);
		await expect.poll(() => seen.tiles.length).toBeGreaterThan(0);
		// The tile servers require a Referer: they get the site's origin, never the page or query.
		expect([...seen.referers]).toEqual([`${ORIGIN}/`]);
		// The choice lasts for the session: the map loads again without asking.
		await page.reload();
		await expect(page.locator('.dz-marker').first()).toBeVisible();
		await expect(page.getByRole('button', { name: 'Show map' })).toHaveCount(0);
	});

	test('the search filters the map, and the views keep it', async ({ page }) => {
		const { base, alpha } = shared;
		await page.goto(`/dz?view=map&q=${base}`);
		await showMap(page);
		await page.getByLabel('Name, alias or former name').fill(`${base} Alpha`);
		await page.getByRole('button', { name: 'Search' }).click();
		await expect(page).toHaveURL(new RegExp(`/dz\\?q=${base}\\+Alpha&country=&view=map`));
		await expect(page.getByRole('region', { name: 'Map of 1 dropzone' })).toBeVisible();
		await expect(page.locator('.dz-marker')).toHaveCount(1);
		await expect(page.getByRole('button', { name: alpha.name, exact: true })).toBeVisible();

		await page.getByRole('navigation', { name: 'Show dropzones as' }).getByRole('link', { name: 'List' }).click();
		await expect(page).toHaveURL(new RegExp(`/dz\\?q=${base}\\+Alpha$`));
		await expect(page.getByRole('list', { name: 'Dropzones' }).getByRole('link')).toHaveText([alpha.name]);
	});

	test('a popup links to the dropzone page, which links out to OpenStreetMap', async ({ page }) => {
		const { base, alpha, closed } = shared;
		await page.goto(`/dz?view=map&q=${base}`);
		await showMap(page);

		// A click opens the popup and leaves focus where it was.
		await page.getByRole('button', { name: `${closed.name} (closed)` }).click();
		const closedPopup = page.locator('.leaflet-popup', { hasText: closed.name });
		await expect(closedPopup).toContainText('Closed');
		await expect(closedPopup.getByRole('link')).not.toBeFocused();

		// From the keyboard: Enter opens the popup and moves focus to its link; Escape closes it
		// and returns to the marker.
		const marker = page.getByRole('button', { name: alpha.name, exact: true });
		await marker.focus();
		await page.keyboard.press('Enter');
		// (The previous popup may still be fading out: find this one by its dropzone.)
		const popup = page.locator('.leaflet-popup', { hasText: alpha.name });
		const link = popup.getByRole('link', { name: alpha.name });
		await expect(link).toBeFocused();
		await expect(popup).toContainText('Reykjavik, Iceland');
		await expect(link).toHaveAttribute('href', `/dz/${alpha.id}`);
		await page.keyboard.press('Escape');
		await expect(popup).toHaveCount(0);
		await expect(marker).toBeFocused();
		await page.keyboard.press('Enter');
		await expect(link).toBeFocused();
		await page.keyboard.press('Enter');

		await expect(page).toHaveURL(`${ORIGIN}/dz/${alpha.id}`);
		await expect(page.getByRole('heading', { level: 1 })).toHaveText(alpha.name);
		await expect(page.getByText('64.13000° N, 21.94000° W')).toBeVisible();
		await expect(page.getByRole('link', { name: 'Open in OpenStreetMap' })).toHaveAttribute(
			'href',
			'https://www.openstreetmap.org/?mlat=64.13&mlon=-21.94#map=13/64.13/-21.94'
		);
	});

	test('the tab bar stays above the map: painted on top, and every tab takes its tap', async ({
		page
	}) => {
		const { base, alpha } = shared;
		// A phone 390px wide, short enough that a marker can be scrolled under the tab bar.
		await page.setViewportSize({ width: 390, height: 560 });
		await page.goto('/sign-in');
		await page.getByLabel('Email', { exact: true }).fill(await createAccount({ label: 'dzmaptabs' }));
		await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
		await page.getByRole('button', { name: 'Sign in' }).click();
		await expect(page.getByTestId('current-account')).toBeVisible();
		const tabs = page.getByRole('navigation', { name: 'Primary' });
		const targets: [string, RegExp][] = [
			['Explore', /\/$/],
			['Logbook', /\/jumps$/],
			['Friends', /\/activity$/],
			['Me', /\/profile$/]
		];
		const names = targets.map(([name]) => name);
		const tap = async (x: number, y: number) => page.touchscreen.tap(x, y);

		async function mapPage() {
			await page.goto(`/dz?view=map&q=${base}`);
			// The choice to show the map is remembered for the visit after the first time.
			const ask = page.getByRole('button', { name: 'Show map' });
			const marker = page.locator('.dz-marker').first();
			await expect(ask.or(marker)).toBeVisible();
			if (await ask.isVisible()) await showMap(page);
			await expect(marker).toBeVisible();
		}

		/** Scroll the page by the difference between a box's centre and the tab bar's centre. */
		async function scrollUnderTabs(box: { y: number; height: number }) {
			const bar = (await tabs.boundingBox())!;
			await page.evaluate((dy) => window.scrollBy(0, dy), box.y + box.height / 2 - (bar.y + bar.height / 2));
		}

		/** The map under the whole tab bar: its top a third of the way down the screen. */
		async function mapUnderTabs() {
			await mapPage();
			const map = (await page.getByTestId('dz-map').boundingBox())!;
			await page.evaluate((dy) => window.scrollBy(0, dy), map.y - 560 / 3);
			const [after, bar] = [(await page.getByTestId('dz-map').boundingBox())!, (await tabs.boundingBox())!];
			expect(after.y + after.height, 'the map runs under the tab bar').toBeGreaterThan(bar.y + bar.height);
		}

		/**
		 * What is painted on top at the centre of each tab. Leaflet's tiles let taps through
		 * (pointer-events: none), so for this measurement only every map layer takes them: the
		 * hit test then follows the painting order, tiles included.
		 */
		async function painted(): Promise<string[]> {
			return tabs.getByRole('link').evaluateAll((links) => {
				// Set through the style object: the site's CSP refuses an added <style>.
				const layers = [...document.querySelectorAll<HTMLElement>('.leaflet-container, .leaflet-container *')];
				for (const layer of layers) layer.style.setProperty('pointer-events', 'auto', 'important');
				const found = links.map((link) => {
					const box = link.getBoundingClientRect();
					const hit = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2);
					return hit && link.contains(hit) ? link.textContent!.trim() : `covered by ${hit?.className}`;
				});
				for (const layer of layers) layer.style.removeProperty('pointer-events');
				return found;
			});
		}

		for (const scheme of ['light', 'dark'] as const) {
			await page.emulateMedia({ colorScheme: scheme });
			await mapUnderTabs();
			expect(await painted(), scheme).toEqual(names);
			// With a popup open (the map's highest layer), scrolled under the bar.
			await page.getByRole('button', { name: alpha.name, exact: true }).click();
			const popup = page.locator('.leaflet-popup', { hasText: alpha.name });
			await expect(popup).toBeVisible();
			await scrollUnderTabs((await popup.boundingBox())!);
			expect(await painted(), `${scheme}, popup open`).toEqual(names);
		}

		// A marker right under the bar: tapping there opens the tab, not the marker's popup.
		await mapPage();
		const marker = page.getByRole('button', { name: alpha.name, exact: true });
		await scrollUnderTabs((await marker.boundingBox())!);
		const spot = (await marker.boundingBox())!;
		const bar = (await tabs.boundingBox())!;
		const x = spot.x + spot.width / 2;
		const y = bar.y + bar.height / 2;
		expect(y, 'the marker is under the tab bar').toBeGreaterThan(spot.y);
		expect(y).toBeLessThan(spot.y + spot.height);
		const under = await tabs.getByRole('link').evaluateAll(
			(links, px) => links.findIndex((link) => {
				const box = link.getBoundingClientRect();
				return px >= box.left && px < box.right;
			}),
			x
		);
		await tap(x, y);
		await expect(page).toHaveURL(targets[under][1]);

		// Each tab, tapped with the map under the whole bar.
		for (const [name, url] of targets) {
			await mapUnderTabs();
			const box = (await tabs.getByRole('link', { name }).boundingBox())!;
			await tap(box.x + box.width / 2, box.y + box.height / 2);
			await expect(page).toHaveURL(url);
		}
	});

	test('without JavaScript the Map view points to the list', async ({ browser }) => {
		const plain = await browser.newContext({ javaScriptEnabled: false, ignoreHTTPSErrors: true });
		const page = await plain.newPage();
		const plainSeen = await stubTiles(page);
		await page.goto(`${ORIGIN}/dz?view=map&q=${shared.base}`);
		await expect(page.getByText('The map needs JavaScript.')).toBeVisible();
		// The server-rendered Map view does not link Leaflet's CSS either.
		expect(plainSeen.stylesheets.length).toBeGreaterThan(0);
		expect(await leafletCssAmong(page, plainSeen.stylesheets)).toBe(false);
		await expect(page.getByRole('button', { name: 'Show map' })).toHaveCount(0);
		await page.getByRole('link', { name: 'View as list' }).click();
		await expect(page).toHaveURL(`${ORIGIN}/dz?q=${shared.base}`);
		await expect(page.getByRole('list', { name: 'Dropzones' }).getByRole('link')).toHaveCount(4);
		expect(plainSeen.external).toEqual([]);
		await plain.close();
	});

	test.describe('reduced motion', () => {
		test.use({ reducedMotion: 'reduce' });

		test('the map works without animation, keyboard included', async ({ page }) => {
			await page.goto(`/dz?view=map&q=${shared.base}`);
			await showMap(page);
			const marker = page.getByRole('button', { name: shared.beta.name, exact: true });
			await marker.focus();
			await page.keyboard.press('Enter');
			const popup = page.locator('.leaflet-popup', { hasText: shared.beta.name });
			await expect(popup.getByRole('link', { name: shared.beta.name })).toBeFocused();
			// No fade: the popup is fully shown at once and gone at once.
			await expect(popup).toHaveCSS('opacity', '1');
			await page.keyboard.press('Escape');
			await expect(popup).toHaveCount(0);
			await expect(marker).toBeFocused();
		});
	});

	for (const scheme of ['light', 'dark'] as const) {
		test.describe(scheme, () => {
			test.use({ colorScheme: scheme });

			test('axe passes on the Map view: asking, loaded, and with a popup open', async ({ page }) => {
				await page.goto(`/dz?view=map&q=${shared.base}`);
				await expect(page.getByRole('button', { name: 'Show map' })).toBeVisible();
				expect.soft(await violations(page), 'asking').toEqual([]);
				await showMap(page);
				expect.soft(await violations(page), 'loaded').toEqual([]);
				await page.getByRole('button', { name: shared.alpha.name, exact: true }).click();
				await expect(page.locator('.leaflet-popup', { hasText: shared.alpha.name })).toBeVisible();
				expect.soft(await violations(page), 'popup').toEqual([]);
			});
		});
	}
});
