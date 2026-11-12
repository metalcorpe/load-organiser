import { randomUUID } from 'node:crypto';
import { expect, test, type Page } from '@playwright/test';
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

/** A jumper with four belly jumps at a private place, numbered 1 to 4. */
async function jumper(): Promise<string> {
	const email = await createAccount({ label: 'batch' });
	const bearer = await apiSession(email);
	const place = await apiCall('POST', '/places', { bearer, body: { name: 'Batch strip', country: 'PT' } });
	expect(place.status).toBe(201);
	const placeId = ((await place.json()) as { id: string }).id;
	for (const n of [1, 2, 3, 4]) {
		const made = await apiCall('POST', '/jumps', {
			bearer,
			body: {
				client_key: randomUUID(),
				place_id: placeId,
				jumped_on: `2026-09-0${n}`,
				jump_type: 'belly',
				jump_number: n
			}
		});
		expect(made.status, await made.clone().text()).toBe(201);
	}
	return email;
}

test.describe('changing many jumps at once', () => {
	test('select three jumps, set their type, see them changed, then undo', async ({ page }) => {
		await signIn(page, await jumper());
		await page.getByRole('link', { name: 'Select jumps to change' }).click();
		await expect(page).toHaveURL(`${ORIGIN}/jumps?select=1`);

		const rows = page.getByRole('list', { name: 'Jumps' });
		for (const n of [2, 3, 4]) await rows.getByLabel(new RegExp(`#${n}\\b`)).check();
		// The filter form has a "Type" too: choose within "What they all get".
		const changes = page.getByRole('group', { name: 'What they all get' });
		await changes.getByLabel('Type', { exact: true }).selectOption('freefly');
		await page.getByRole('button', { name: 'Check the change' }).click();

		// Step 1 shows the change and the affected jumps; nothing is saved yet.
		await expect(page.getByRole('heading', { name: 'Change 3 jumps: type → Freefly' })).toBeVisible();
		await expect(page.getByRole('list', { name: 'Jumps to change' }).getByRole('listitem')).toHaveCount(3);
		await page.getByRole('button', { name: 'Change 3 jumps' }).click();

		// Step 2 applied: the three are freefly, the fourth is untouched.
		await expect(page).toHaveURL(/\/jumps\?changed=3&skipped=0&unchanged=0$/);
		await expect(page.getByText('Changed 3 jumps.')).toBeVisible();
		const list = page.getByRole('list', { name: 'Jumps' });
		await expect(list.getByRole('listitem').filter({ hasText: 'Freefly' })).toHaveCount(3);
		await expect(list.getByRole('listitem').filter({ hasText: '#1' })).toContainText('Belly');

		// Each changed jump keeps the change in its own history.
		await list.getByRole('link', { name: /#2/ }).click();
		await expect(page.getByText(/Changed together with other jumps/)).toBeVisible();
		await expect(page.getByText('Type: belly → freefly')).toBeVisible();

		// One undo for the whole change.
		await page.goto('/jumps');
		await page.getByRole('button', { name: 'Undo this change' }).click();
		await expect(page.getByText('Put back 3 jumps.')).toBeVisible();
		await expect(page.getByRole('list', { name: 'Jumps' }).getByRole('listitem').filter({ hasText: 'Freefly' })).toHaveCount(0);
		await expect(page.getByRole('button', { name: 'Undo this change' })).toHaveCount(0);
	});
});
