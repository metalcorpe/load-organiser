import { expect, test, type Page } from '@playwright/test';
import { PASSWORD, createAccount } from './support/accounts.ts';

// Same production-cookie preview as the account tests.
const ORIGIN = 'https://127.0.0.1:4175';
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
