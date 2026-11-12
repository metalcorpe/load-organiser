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

test.describe('wing loading', () => {
	test('exit weight and canopy size give a jump its loading; a higher one gets a calm note', async ({
		page
	}) => {
		const email = await createAccount({ label: 'wingload' });
		await signIn(page, email, '/profile');

		// The usual exit weight, a private setting on the profile.
		await page.getByLabel('Exit weight (optional)', { exact: true }).fill('81.6');
		await page.getByRole('radio', { name: 'Kilograms' }).check();
		await page.getByRole('button', { name: 'Save exit weight' }).click();
		await expect(page.getByText('Exit weight saved.', { exact: true })).toBeVisible();

		// A main canopy with its size, entered on the gear form.
		await page.goto('/gear/new');
		await page.getByLabel('Type', { exact: true }).selectOption('main');
		await page.getByLabel('Label', { exact: true }).fill('Sabre 170');
		await page.getByLabel('Canopy size in square feet (optional)', { exact: true }).fill('170');
		await page.getByRole('button', { name: 'Save component' }).click();
		await expect(page.getByText('Saved privately.', { exact: true })).toBeVisible();
		// A smaller main, through the API.
		const bearer = await apiSession(email);
		const smaller = await apiCall('POST', '/gear/components', {
			bearer,
			body: { client_key: randomUUID(), kind: 'main', label: 'Velo 135', canopy_size_sqft: 135 }
		});
		expect(smaller.status).toBe(201);

		// A jump with the 170: 81.6 kg over 170 sq ft is 1.06.
		await page.goto('/jumps/new');
		await page.getByLabel('Place name').fill('Loading strip');
		await page.getByLabel('Country', { exact: true }).selectOption('PT');
		await page.getByRole('button', { name: 'Use this place' }).click();
		await expect(page.getByText('Loading strip', { exact: true })).toBeVisible();
		const placeUrl = page.url();
		await page.getByLabel('Date', { exact: true }).fill('2026-10-10');
		await page.getByRole('checkbox', { name: /^Sabre 170/ }).check();
		// No loading recorded before: nothing to compare with, so no note.
		await expect(page.getByText(/highest wing loading so far/)).toHaveCount(0);
		await page.getByRole('button', { name: 'Save private jump' }).click();
		await expect(page.getByText('Saved privately.', { exact: true })).toBeVisible();
		await expect(page.getByTestId('wing-loading')).toContainText('1.06');

		// The logbook row shows it compactly.
		await page.goto('/jumps');
		await expect(page.getByRole('list', { name: 'Jumps' })).toContainText('wing loading 1.06');

		// The next jump with the 135: 1.33, more than 0.1 above 1.06, gets the note.
		await page.goto(placeUrl);
		await page.getByLabel('Date', { exact: true }).fill('2026-10-11');
		await page.getByRole('checkbox', { name: /^Velo 135/ }).check();
		await expect(
			page.getByText('This is your highest wing loading so far (1.33; previous highest 1.06).', {
				exact: true
			})
		).toBeVisible();
		// A lighter exit weight on this jump brings it back within 0.1: no note.
		await page.getByLabel('Exit weight on this jump in kg (optional)', { exact: true }).fill('70');
		await expect(page.getByText(/highest wing loading so far/)).toHaveCount(0);
		await page.getByLabel('Exit weight on this jump in kg (optional)', { exact: true }).fill('');
		await page.getByRole('button', { name: 'Save private jump' }).click();
		await expect(page.getByText('Saved privately.', { exact: true })).toBeVisible();
		await expect(page.getByTestId('wing-loading')).toContainText('1.33');

		// History: the highest per month, as a table behind the bars.
		await page.goto('/history');
		const table = page.getByRole('table', { name: 'Highest wing loading by month' });
		await expect(table.getByRole('row', { name: /Oct 2026/ })).toContainText('1.33');

		// The printable logbook prints it when asked.
		await page.goto('/records/print?loading=yes');
		await expect(page.getByRole('columnheader', { name: 'Wing loading' }).first()).toBeVisible();
	});

	test('a jump without the values says what is missing', async ({ page }) => {
		const email = await createAccount({ label: 'wingmiss' });
		const bearer = await apiSession(email);
		const place = await apiCall('POST', '/places', { bearer, body: { name: 'Bare strip', country: 'PT' } });
		const placeId = ((await place.json()) as { id: string }).id;
		const made = await apiCall('POST', '/jumps', {
			bearer,
			body: { client_key: randomUUID(), place_id: placeId, jumped_on: '2026-10-10', jump_type: 'belly' }
		});
		const jumpId = ((await made.json()) as { jump: { id: string } }).jump.id;
		await signIn(page, email, `/jumps/${jumpId}`);
		await expect(page.getByTestId('wing-loading')).toContainText(
			'Unknown: no exit weight is set and no main canopy is recorded on the jump.'
		);
		await expect(page.getByRole('link', { name: 'Set your exit weight' })).toBeVisible();
	});
});
