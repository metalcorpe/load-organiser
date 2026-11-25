import { expect, test, type Page } from '@playwright/test';
import { PASSWORD, createAccount } from './support/accounts.ts';
import { SECURE_ORIGIN } from './support/origins.ts';

// Same production-cookie preview as the account tests.
const ORIGIN = SECURE_ORIGIN;
test.use({ baseURL: ORIGIN, ignoreHTTPSErrors: true });

async function signInTo(page: Page, path: string, label: string) {
	await page.goto(`/sign-in?returnTo=${encodeURIComponent(path)}`);
	await page.getByLabel('Email', { exact: true }).fill(await createAccount({ label }));
	await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
	await page.getByRole('button', { name: 'Sign in' }).click();
	await expect(page).toHaveURL(`${ORIGIN}${path}`);
}

const tabs = (page: Page) => page.getByRole('navigation', { name: 'Primary' });

test.describe('tab switching (perf)', () => {
	test('a data request says where its time went (Server-Timing)', async ({ page }) => {
		await signInTo(page, '/', 'timing');
		const data = page.waitForResponse((response) => response.url().includes('/jumps/__data.json'));
		await tabs(page).getByRole('link', { name: 'Logbook' }).click();
		const timing = (await data).headers()['server-timing'];
		expect(timing).toMatch(/api-getSession;dur=\d+\.\d/);
		expect(timing).toMatch(/api-listJumps;dur=\d+\.\d/);
		expect(timing).toMatch(/viewer;dur=\d+\.\d/);
		expect(timing).toMatch(/total;dur=\d+\.\d/);
	});

	test('the tapped tab answers at once; a slow page shows a skeleton until its data arrives', async ({
		page
	}) => {
		await signInTo(page, '/', 'pending');
		let release: () => void = () => {};
		const held = new Promise<void>((resolve) => (release = resolve));
		await page.route('**/jumps/__data.json*', async (route) => {
			await held;
			await route.continue();
		});
		const logbook = tabs(page).getByRole('link', { name: 'Logbook' });
		await logbook.click();
		// At once: the tapped tab carries the pill, while the page it shows is still Explore.
		await expect(logbook).toHaveAttribute('data-pending', 'true');
		await expect(tabs(page).getByRole('link', { name: 'Explore' })).toHaveAttribute('aria-current', 'page');
		await expect(page.locator('main')).toHaveAttribute('aria-busy', 'true');
		// Past the short grace period, a skeleton of the page stands in for the old content.
		await expect(page.getByTestId('tab-skeleton')).toBeVisible();
		await expect(page.getByRole('heading', { level: 1, name: 'Events' })).toBeHidden();

		release();
		await expect(page).toHaveURL(`${ORIGIN}/jumps`);
		await expect(logbook).toHaveAttribute('aria-current', 'page');
		await expect(logbook).not.toHaveAttribute('data-pending');
		await expect(page.getByTestId('tab-skeleton')).toHaveCount(0);
		await expect(page.locator('main')).not.toHaveAttribute('aria-busy');
		await expect(page.getByRole('heading', { level: 1, name: 'Logbook' })).toBeVisible();
	});

	test('the tab bar loads every tab’s code ahead of a tap', async ({ page }) => {
		await signInTo(page, '/', 'precode');
		for (const link of await tabs(page).getByRole('link').all()) {
			await expect(link).toHaveAttribute('data-sveltekit-preload-code', 'viewport');
			await expect(link).not.toHaveAttribute('data-sveltekit-preload-data');
		}
	});
});
