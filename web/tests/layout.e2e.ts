import { expect, test, type Page } from '@playwright/test';
import { PASSWORD, createAccount } from './support/accounts.ts';
import { SECURE_ORIGIN } from './support/origins.ts';

// Same production-cookie preview as the account tests.
const ORIGIN = SECURE_ORIGIN;
test.use({ baseURL: ORIGIN, ignoreHTTPSErrors: true });

/** Left edges of the brand, the tab bar and the page heading, in CSS pixels. */
async function edges(page: Page) {
	const left = async (locator: ReturnType<Page['locator']>) =>
		Math.round((await locator.boundingBox())!.x);
	return {
		brand: await left(page.getByRole('banner').getByRole('link', { name: 'Load Organiser' })),
		tabs: await page
			.getByRole('navigation', { name: 'Primary' })
			.getByRole('list')
			.boundingBox()
			.then((box) => [Math.round(box!.x), Math.round(box!.width)]),
		heading: await left(page.getByRole('heading', { level: 1 }))
	};
}

test.describe('layout rule (navigation.ts, pageLayout)', () => {
	test('on a large screen the primary pages share one frame; other pages are a centred column', async ({
		page
	}) => {
		await page.setViewportSize({ width: 1440, height: 900 });
		await page.goto('/sign-in?returnTo=%2Fjumps');
		await page.getByLabel('Email', { exact: true }).fill(await createAccount({ label: 'frame' }));
		await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
		await page.getByRole('button', { name: 'Sign in' }).click();
		await expect(page).toHaveURL(`${ORIGIN}/jumps`);

		const first = await edges(page);
		// The heading starts at the header's content edge.
		expect(first.heading).toBe(first.brand);
		for (const path of ['/', '/dz', '/activity', '/profile']) {
			await page.goto(path);
			// Same heading edge, and the header and tabs do not move.
			expect(await edges(page), path).toEqual(first);
		}

		// A form page is one narrow column, centred under the same header and tabs.
		await page.goto('/jumps/new');
		const narrow = await edges(page);
		expect(narrow.brand).toBe(first.brand);
		expect(narrow.tabs).toEqual(first.tabs);
		const main = (await page.locator('main').boundingBox())!;
		expect(Math.abs(main.x + main.width / 2 - 720)).toBeLessThanOrEqual(10);
		expect(main.width).toBeLessThanOrEqual(640);
	});
});

/** A fresh member, signed in and landed on `path`. */
async function signInTo(page: Page, path: string, label: string) {
	await page.goto(`/sign-in?returnTo=${encodeURIComponent(path)}`);
	await page.getByLabel('Email', { exact: true }).fill(await createAccount({ label }));
	await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
	await page.getByRole('button', { name: 'Sign in' }).click();
	await expect(page).toHaveURL(`${ORIGIN}${path}`);
}

const TRANSPARENT = 'rgba(0, 0, 0, 0)';

test.describe('graphite surfaces (design H)', () => {
	test('a card has no visible outline but a shadow, in light', async ({ page }) => {
		await page.emulateMedia({ colorScheme: 'light' });
		await signInTo(page, '/gear', 'surface');
		const style = await page
			.locator('section.card')
			.first()
			.evaluate((el) => {
				const s = getComputedStyle(el);
				return { color: s.borderTopColor, width: s.borderTopWidth, shadow: s.boxShadow };
			});
		expect(style.color).toBe(TRANSPARENT);
		expect(style.width).toBe('1px');
		expect(style.shadow).not.toBe('none');
	});

	test('in forced colours the card keeps a drawn edge', async ({ page, browserName }) => {
		test.skip(browserName !== 'chromium', 'forced-colours emulation is Chromium-only');
		await signInTo(page, '/gear', 'forced');
		await page.emulateMedia({ forcedColors: 'active' });
		const edge = await page
			.locator('section.card')
			.first()
			.evaluate((el) => {
				const s = getComputedStyle(el);
				return { color: s.borderTopColor, width: s.borderTopWidth, style: s.borderTopStyle };
			});
		expect(edge.style).toBe('solid');
		expect(edge.width).toBe('1px');
		expect(edge.color).not.toBe(TRANSPARENT);
	});
});

test.describe('floating tab bar (design H, phones)', () => {
	const primary = (page: Page) => page.getByRole('navigation', { name: 'Primary' });

	test('the tab bar floats inside the screen edges', async ({ page }) => {
		await signInTo(page, '/jumps', 'float');
		const nav = (await primary(page).boundingBox())!;
		const viewport = page.viewportSize()!;
		expect(nav.x).toBeGreaterThanOrEqual(12);
		expect(viewport.width - (nav.x + nav.width)).toBeGreaterThanOrEqual(12);
		expect(viewport.height - (nav.y + nav.height)).toBeGreaterThanOrEqual(12);
	});

	test('the active tab is a filled pill, marked in forced colours too', async ({ page, browserName }) => {
		await signInTo(page, '/jumps', 'pill');
		const current = primary(page).locator('a[aria-current="page"]');
		const fill = () => current.evaluate((el) => getComputedStyle(el).backgroundColor);
		expect(await fill()).not.toBe(TRANSPARENT);
		if (browserName === 'chromium') {
			await page.emulateMedia({ forcedColors: 'active' });
			expect(await fill()).not.toBe(TRANSPARENT);
		}
	});

	test('the footer scrolls fully clear of the tab bar', async ({ page }) => {
		await signInTo(page, '/jumps', 'clear');
		await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
		const last = (await page.locator('footer a').last().boundingBox())!;
		const nav = (await primary(page).boundingBox())!;
		expect(last.y + last.height).toBeLessThanOrEqual(nav.y);
	});

	test('at 320px and 200% text every tab label stays whole and 44px tall', async ({ page }) => {
		await page.setViewportSize({ width: 320, height: 640 });
		await signInTo(page, '/jumps', 'zoom');
		// Text-only zoom as in reflow.e2e.ts: rem sizes and the body's 16px base doubled (the CSP
		// blocks an injected stylesheet; inline style set by script is allowed).
		await page.evaluate(() => {
			document.documentElement.style.fontSize = '200%';
			document.body.style.fontSize = '32px';
		});
		for (const tab of await primary(page).locator('a').all()) {
			expect((await tab.boundingBox())!.height).toBeGreaterThanOrEqual(44);
			expect(await tab.locator('span').evaluate((el) => el.getClientRects().length)).toBe(1);
		}
	});
});
