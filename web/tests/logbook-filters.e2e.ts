import { expect, test, type Page } from '@playwright/test';
import { randomUUID } from 'node:crypto';
import { PASSWORD, apiCall, apiSession, createAccount } from './support/accounts.ts';

// Same production-cookie preview as the logbook tests.
const ORIGIN = 'https://127.0.0.1:4175';
test.use({ baseURL: ORIGIN, ignoreHTTPSErrors: true });

async function signIn(page: Page, email: string, returnTo = '/jumps') {
	await page.goto(`/sign-in?returnTo=${encodeURIComponent(returnTo)}`);
	await page.getByLabel('Email', { exact: true }).fill(email);
	await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
	await page.getByRole('button', { name: 'Sign in' }).click();
	await expect(page).toHaveURL(`${ORIGIN}${returnTo}`);
}

/** A jumper with four jumps at one private place, logged through the API. */
async function jumper(label: string): Promise<string> {
	const email = await createAccount({ label });
	const bearer = await apiSession(email);
	const place = await apiCall('POST', '/places', { bearer, body: { name: 'Filter strip', country: 'PT' } });
	expect(place.status).toBe(201);
	const placeId = ((await place.json()) as { id: string }).id;
	const jumps = [
		{ jumped_on: '2026-01-05', jump_type: 'belly', jump_number: 10, freefall_seconds: 50, notes: 'Sunset load' },
		{ jumped_on: '2026-02-05', jump_type: 'freefly', jump_number: 11 },
		{ jumped_on: '2026-03-05', jump_type: 'belly', jump_number: 12, freefall_seconds: 40 },
		{ jumped_on: '2026-04-05', jump_type: 'belly', jump_number: 13 }
	];
	for (const jump of jumps) {
		const sent = await apiCall('POST', '/jumps', {
			bearer,
			body: { client_key: randomUUID(), place_id: placeId, ...jump }
		});
		expect(sent.status, await sent.clone().text()).toBe(201);
	}
	return email;
}

const rows = (page: Page) => page.getByRole('list', { name: 'Jumps' }).getByRole('listitem');

test.describe('logbook search and filters', () => {
	test('filter by type and date range, page through, then clear', async ({ page }) => {
		await signIn(page, await jumper('filters'));
		await expect(rows(page)).toHaveCount(4);

		await page.getByText('Filters', { exact: true }).click();
		await page.getByLabel('Type', { exact: true }).selectOption('belly');
		await page.getByLabel('From date').fill('2026-02-01');
		await page.getByLabel('To date').fill('2026-03-31');
		await page.getByRole('button', { name: 'Show jumps' }).click();

		// The filters are in the address, so the result can be bookmarked or shared with yourself.
		await expect(page).toHaveURL(/type=belly/);
		await expect(page).toHaveURL(/from=2026-02-01/);
		await expect(page).toHaveURL(/to=2026-03-31/);
		await expect(rows(page)).toHaveCount(1);
		await expect(rows(page)).toContainText('#12');
		const matched = page.getByRole('region', { name: 'Matching jumps' });
		await expect(matched).toContainText('1 jump matches');
		await expect(matched).toContainText('40 s of freefall');
		// The form shows what is applied.
		await expect(page.getByLabel('Type', { exact: true })).toHaveValue('belly');
		await expect(page.getByLabel('From date')).toHaveValue('2026-02-01');

		// Text search covers the owner's private notes.
		await page.getByLabel('Place or notes').fill('sunset');
		await page.getByLabel('From date').fill('');
		await page.getByLabel('To date').fill('');
		await page.getByRole('button', { name: 'Search' }).click();
		await expect(rows(page)).toHaveCount(1);
		await expect(rows(page)).toContainText('#10');

		// No match: an empty state with a way back.
		await page.goto('/jumps?type=wingsuit');
		await expect(page.getByText('No jumps match these filters.')).toBeVisible();
		await page.getByRole('link', { name: 'Clear filters' }).first().click();
		await expect(page).toHaveURL(`${ORIGIN}/jumps`);
		await expect(rows(page)).toHaveCount(4);
	});

	test('dates out of order are explained, not ignored', async ({ page }) => {
		await signIn(page, await jumper('filterorder'));
		await page.goto('/jumps?from=2026-03-01&to=2026-02-01');
		await expect(page.getByRole('alert')).toContainText('on or before');
		await expect(page.getByLabel('To date')).toHaveAttribute('aria-invalid', 'true');
	});

	test('filters work without JavaScript', async ({ page, browser }) => {
		await signIn(page, await jumper('filternojs'));
		const nojs = await browser.newContext({
			storageState: await page.context().storageState(),
			javaScriptEnabled: false,
			ignoreHTTPSErrors: true
		});
		const plain = await nojs.newPage();
		await plain.goto(`${ORIGIN}/jumps`);
		await plain.getByText('Filters', { exact: true }).click();
		await plain.getByLabel('From jump number').fill('11');
		await plain.getByLabel('To jump number').fill('12');
		await plain.getByRole('button', { name: 'Show jumps' }).click();
		await expect(plain).toHaveURL(/from_number=11/);
		await expect(rows(plain)).toHaveCount(2);
		await nojs.close();
	});
});
