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

/** A jumper with a private place and these jumps (by number, null for none), via the API. */
async function jumper(label: string, numbers: (number | null)[]) {
	const email = await createAccount({ label });
	const bearer = await apiSession(email);
	const place = await apiCall('POST', '/places', { bearer, body: { name: 'Number strip', country: 'PT' } });
	expect(place.status).toBe(201);
	const placeId = ((await place.json()) as { id: string }).id;
	const ids: string[] = [];
	for (const [i, number] of numbers.entries()) {
		const sent = await apiCall('POST', '/jumps', {
			bearer,
			body: {
				client_key: randomUUID(),
				place_id: placeId,
				jumped_on: `2026-09-${String(i + 1).padStart(2, '0')}`,
				jump_type: 'belly',
				jump_number: number,
				confirm_distinct: true
			}
		});
		expect(sent.status, await sent.clone().text()).toBe(201);
		ids.push(((await sent.json()) as { jump: { id: string } }).jump.id);
	}
	return { email, placeId, ids };
}

test.describe('suggested next jump number', () => {
	test('a new jump proposes the next number, editable, with a hint', async ({ page }) => {
		const { email, placeId } = await jumper('nextnum', [119, 120]);
		await signIn(page, email);
		await page.goto(`/jumps/new?place=${placeId}`);
		const number = page.getByLabel('Your jump number');
		await expect(number).toHaveValue('121');
		await expect(page.getByText('Your last numbered jump is #120.')).toBeVisible();
		await expect(number).toHaveAccessibleDescription(/Your last numbered jump is #120/);
		// The proposal is only a starting value.
		await number.fill('130');
		await page.getByLabel('Date', { exact: true }).fill('2026-10-10');
		await page.getByRole('button', { name: 'Save private jump' }).click();
		await expect(page.getByText('Saved privately.')).toBeVisible();
		await expect(page.getByText('#130', { exact: true })).toBeVisible();
	});

	test('"Log the next jump" keeps counting from its source jump', async ({ page }) => {
		const { email, placeId, ids } = await jumper('nextfrom', [119, 120]);
		await signIn(page, email);
		await page.goto(`/jumps/new?place=${placeId}&from=${ids[0]}`);
		await expect(page.getByLabel('Your jump number')).toHaveValue('120');
		await expect(page.getByText('Your last numbered jump is')).toHaveCount(0);
	});

	test('a jumper who never numbered a jump gets no proposal', async ({ page }) => {
		const { email, placeId } = await jumper('nonum', [null]);
		await signIn(page, email);
		await page.goto(`/jumps/new?place=${placeId}`);
		await expect(page.getByLabel('Your jump number')).toHaveValue('');
		await expect(page.getByText('Your last numbered jump is')).toHaveCount(0);
	});

	test('the logbook notes gaps and repeats, linking to the jumps', async ({ page }) => {
		const { email, ids } = await jumper('numgaps', [120, 125, 125]);
		await signIn(page, email);
		const notes = page.getByRole('region', { name: 'Jump numbers to check' });
		await expect(notes).toContainText('Numbers 121–124 are missing, between #120 and #125.');
		await expect(notes).toContainText('#125 is used twice');
		await notes.getByRole('link', { name: '#120' }).click();
		await expect(page).toHaveURL(`${ORIGIN}/jumps/${ids[0]}`);
	});

	test('nothing is noted when the numbering is in order', async ({ page }) => {
		const { email } = await jumper('numok', [1, 2, 3]);
		await signIn(page, email);
		await expect(page.getByRole('list', { name: 'Jumps' }).getByRole('listitem')).toHaveCount(3);
		await expect(page.getByRole('region', { name: 'Jump numbers to check' })).toHaveCount(0);
	});
});
