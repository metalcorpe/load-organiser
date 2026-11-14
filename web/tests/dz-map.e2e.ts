import AxeBuilder from '@axe-core/playwright';
import { randomBytes } from 'node:crypto';
import { expect, test, type Page, type Request } from '@playwright/test';
import { apiCall, reviewerSession } from './support/accounts.ts';

// The Map view of the dropzone directory (/dz?view=map). Tiles are never fetched from the real
// OpenStreetMap servers here: every tile request is answered with a 1x1 PNG.
const ORIGIN = 'https://127.0.0.1:4175';
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

/** Answer tile requests locally, and record every request that leaves for another host. */
async function stubTiles(
	page: Page
): Promise<{ tiles: string[]; referers: Set<string>; external: string[] }> {
	const seen = { tiles: [] as string[], referers: new Set<string>(), external: [] as string[] };
	await page.route(TILES, (route) => {
		seen.tiles.push(route.request().url());
		seen.referers.add(route.request().headers()['referer'] ?? '');
		return route.fulfill({ status: 200, contentType: 'image/png', body: PNG });
	});
	page.on('request', (request: Request) => {
		const url = new URL(request.url());
		if (url.origin !== ORIGIN && !url.protocol.startsWith('data')) seen.external.push(url.href);
	});
	return seen;
}

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
	test('the Map view asks first, then loads the map with markers', async ({ page }) => {
		const seen = await stubTiles(page);
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
		await expect(page.getByRole('main').getByRole('link', { name: 'list', exact: true })).toHaveAttribute(
			'href',
			`/dz?q=${base}`
		);
		await expect(page.getByTestId('dz-map')).toHaveCount(0);
		await expect(page.getByTestId('map-needs-js')).toHaveCount(0);
		expect(seen.external).toEqual([]);

		await showMap(page);
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
		await expect(page.getByRole('link', { name: 'OpenStreetMap' })).toHaveAttribute(
			'href',
			'https://www.openstreetmap.org/copyright'
		);
		await expect.poll(() => seen.tiles.length).toBeGreaterThan(0);
		// The tile servers require a Referer: they get the site's origin, never the page or query.
		expect([...seen.referers]).toEqual([`${ORIGIN}/`]);
		// Only tiles leave the site, and only from the one tile host.
		expect(seen.external.every((url) => url.startsWith('https://tile.openstreetmap.org/'))).toBe(true);

		// The choice lasts for the session: the map loads again without asking.
		await page.reload();
		await expect(page.locator('.dz-marker').first()).toBeVisible();
		await expect(page.getByRole('button', { name: 'Show map' })).toHaveCount(0);
	});

	test('the search filters the map, and the views keep it', async ({ page }) => {
		await stubTiles(page);
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
		await stubTiles(page);
		const { base, alpha, closed } = shared;
		await page.goto(`/dz?view=map&q=${base}`);
		await showMap(page);

		await page.getByRole('button', { name: `${closed.name} (closed)` }).click();
		await expect(page.locator('.leaflet-popup', { hasText: closed.name })).toContainText('Closed');

		// From the keyboard: Enter opens the popup and moves focus to its link.
		const marker = page.getByRole('button', { name: alpha.name, exact: true });
		await marker.focus();
		await page.keyboard.press('Enter');
		// (The previous popup may still be fading out: find this one by its dropzone.)
		const popup = page.locator('.leaflet-popup', { hasText: alpha.name });
		const link = popup.getByRole('link', { name: alpha.name });
		await expect(link).toBeFocused();
		await expect(popup).toContainText('Reykjavik, Iceland');
		await expect(link).toHaveAttribute('href', `/dz/${alpha.id}`);
		await page.keyboard.press('Enter');

		await expect(page).toHaveURL(`${ORIGIN}/dz/${alpha.id}`);
		await expect(page.getByRole('heading', { level: 1 })).toHaveText(alpha.name);
		await expect(page.getByText('64.13000° N, 21.94000° W')).toBeVisible();
		await expect(page.getByRole('link', { name: 'Open in OpenStreetMap' })).toHaveAttribute(
			'href',
			'https://www.openstreetmap.org/?mlat=64.13&mlon=-21.94#map=13/64.13/-21.94'
		);
	});

	test('without JavaScript the Map view points to the list', async ({ browser }) => {
		const plain = await browser.newContext({ javaScriptEnabled: false, ignoreHTTPSErrors: true });
		const page = await plain.newPage();
		const seen = await stubTiles(page);
		await page.goto(`${ORIGIN}/dz?view=map&q=${shared.base}`);
		await expect(page.getByText('The map needs JavaScript.')).toBeVisible();
		await expect(page.getByRole('button', { name: 'Show map' })).toHaveCount(0);
		await page.getByRole('link', { name: 'Use the list' }).click();
		await expect(page).toHaveURL(`${ORIGIN}/dz?q=${shared.base}`);
		await expect(page.getByRole('list', { name: 'Dropzones' }).getByRole('link')).toHaveCount(4);
		expect(seen.tiles).toEqual([]);
		await plain.close();
	});

	for (const scheme of ['light', 'dark'] as const) {
		test.describe(scheme, () => {
			test.use({ colorScheme: scheme });

			test('axe passes on the Map view: asking, loaded, and with a popup open', async ({ page }) => {
				await stubTiles(page);
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
