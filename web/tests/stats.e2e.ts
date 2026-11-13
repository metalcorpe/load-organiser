import { randomUUID } from 'node:crypto';
import { expect, test, type Page } from '@playwright/test';
import { PASSWORD, apiCall, apiSession, createAccount } from './support/accounts.ts';

// Same production-cookie preview as the logbook tests.
const ORIGIN = 'https://127.0.0.1:4175';
test.use({ baseURL: ORIGIN, ignoreHTTPSErrors: true });

async function signIn(page: Page, email: string, returnTo: string) {
	await page.goto(`/sign-in?returnTo=${encodeURIComponent(returnTo)}`);
	await page.getByLabel('Email', { exact: true }).fill(email);
	await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
	await page.getByRole('button', { name: 'Sign in' }).click();
	await expect(page).toHaveURL(`${ORIGIN}${returnTo}`);
}

test.describe('statistics', () => {
	test('jumps of two types give the right counts, for all years and for one', async ({ page }) => {
		const email = await createAccount({ label: 'stats' });
		const bearer = await apiSession(email);
		const place = await apiCall('POST', '/places', { bearer, body: { name: 'Stats strip', country: 'PT' } });
		const placeId = ((await place.json()) as { id: string }).id;
		const jumps: [string, string][] = [
			['2026-09-01', 'belly'],
			['2026-09-02', 'belly'],
			['2026-09-03', 'belly'],
			['2026-10-01', 'freefly'],
			['2026-10-02', 'freefly'],
			['2025-06-01', 'belly']
		];
		for (const [on, type] of jumps) {
			const made = await apiCall('POST', '/jumps', {
				bearer,
				body: { client_key: randomUUID(), place_id: placeId, jumped_on: on, jump_type: type }
			});
			expect(made.status, await made.clone().text()).toBe(201);
		}

		// Reached from History, not from a new tab.
		await signIn(page, email, '/history');
		await page.getByRole('link', { name: 'Statistics' }).click();
		await expect(page.getByRole('heading', { level: 1, name: 'Statistics' })).toBeVisible();
		await expect(page.getByText('6 jumps recorded here.', { exact: true })).toBeVisible();

		const types = page.getByRole('table', { name: 'Jumps by type' });
		await expect(types.getByRole('row', { name: /Belly/ }).getByRole('cell')).toHaveText('4');
		await expect(types.getByRole('row', { name: /Freefly/ }).getByRole('cell')).toHaveText('2');
		const years = page.getByRole('table', { name: 'Jumps per year' });
		await expect(years.getByRole('row', { name: /2026/ }).getByRole('cell')).toHaveText('5');
		await expect(years.getByRole('row', { name: /2025/ }).getByRole('cell')).toHaveText('1');
		const places = page.getByRole('table', { name: 'Jumps by place' });
		await expect(places.getByRole('row', { name: /Stats strip/ }).getByRole('cell')).toHaveText('6');

		// One year: everything but the years narrows to it.
		await page.getByLabel('Year', { exact: true }).selectOption('2026');
		await page.getByRole('button', { name: 'Show' }).click();
		await expect(page).toHaveURL(/year=2026/);
		await expect(page.getByText('5 jumps recorded in 2026.', { exact: true })).toBeVisible();
		const typesIn2026 = page.getByRole('table', { name: 'Jumps by type' });
		await expect(typesIn2026.getByRole('row', { name: /Belly/ }).getByRole('cell')).toHaveText('3');
		const months = page.getByRole('table', { name: 'Jumps per month in 2026' });
		await expect(months.getByRole('row', { name: /Sep 2026/ }).getByRole('cell')).toHaveText('3');
	});

	test('an empty logbook says so', async ({ page }) => {
		await signIn(page, await createAccount({ label: 'statsnone' }), '/stats');
		await expect(page.getByText('No jumps recorded yet.', { exact: true })).toBeVisible();
	});
});
