import { expect, test, type Page } from '@playwright/test';
import { PASSWORD, createAccount } from './support/accounts.ts';
import { openJumpSections } from './support/jump-form.ts';

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

test.describe('aircraft on each jump', () => {
	test('a jump logged with an aircraft; the next jump at that place starts with it', async ({
		page
	}) => {
		await signIn(page, await createAccount({ label: 'aircraft' }));
		await page.goto('/jumps/new');
		await page.getByLabel('Place name').fill('Aircraft strip');
		await page.getByLabel('Country', { exact: true }).selectOption('PT');
		await page.getByRole('button', { name: 'Use this place' }).click();
		await expect(page.getByText('Aircraft strip', { exact: true })).toBeVisible();
		const placeUrl = page.url();
		// Nothing recorded at this place yet: the field starts empty.
		await openJumpSections(page);
		await expect(page.getByLabel('Aircraft (optional)')).toHaveValue('');
		await page.getByLabel('Date', { exact: true }).fill('2026-10-10');
		await page.getByLabel('Type', { exact: true }).selectOption('belly');
		await page.getByLabel('Aircraft (optional)').fill('Cessna 208 SX-ABC');
		await page.getByRole('button', { name: 'Save private jump' }).first().click();
		await expect(page.getByText('Saved privately.')).toBeVisible();
		await expect(page.getByText('Cessna 208 SX-ABC', { exact: true })).toBeVisible();

		// The logbook row shows it compactly, and the text search finds it.
		await page.goto('/jumps');
		const rows = page.getByRole('list', { name: 'Jumps' });
		await expect(rows).toContainText('Cessna 208 SX-ABC');
		await page.getByLabel('Place, aircraft or notes').fill('sx-abc');
		await page.getByRole('button', { name: 'Search' }).click();
		await expect(page.getByText('1 jump matches')).toBeVisible();

		// A new jump at the same place starts with the aircraft, editable, with a hint.
		await page.goto(placeUrl);
		await openJumpSections(page);
		const aircraft = page.getByLabel('Aircraft (optional)');
		await expect(aircraft).toHaveValue('Cessna 208 SX-ABC');
		await expect(aircraft).toHaveAccessibleDescription(/From your last jump here/);
		await aircraft.fill('Twin Otter');
		await page.getByLabel('Date', { exact: true }).fill('2026-10-11');
		await page.getByRole('button', { name: 'Save private jump' }).first().click();
		await expect(page.getByText('Saved privately.')).toBeVisible();

		// "Log the next jump" carries the aircraft of the jump it starts from.
		await page.getByRole('link', { name: 'Log the next jump' }).click();
		await openJumpSections(page);
		await expect(page.getByLabel('Aircraft (optional)')).toHaveValue('Twin Otter');
	});
});
