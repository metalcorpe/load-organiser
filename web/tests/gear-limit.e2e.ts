import { randomUUID } from 'node:crypto';
import { expect, test, type Page } from '@playwright/test';
import { PASSWORD, apiCall, apiSession, createAccount } from './support/accounts.ts';

// Same production-cookie preview as the account tests.
const ORIGIN = 'https://127.0.0.1:4175';
test.use({ baseURL: ORIGIN, ignoreHTTPSErrors: true });

async function signIn(page: Page, email: string, returnTo: string) {
	await page.goto(`/sign-in?returnTo=${encodeURIComponent(returnTo)}`);
	await page.getByLabel('Email', { exact: true }).fill(email);
	await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
	await page.getByRole('button', { name: 'Sign in' }).click();
	await expect(page).toHaveURL(`${ORIGIN}${returnTo}`);
}

test.describe('gear limits by jump count', () => {
	test('a canopy with a 10-jump limit and 9 linked jumps is due in 1 jump', async ({ page }) => {
		const email = await createAccount({ label: 'jumplimit' });
		const bearer = await apiSession(email);
		const made = await apiCall('POST', '/gear/components', {
			bearer,
			body: { client_key: randomUUID(), kind: 'main', label: 'Sabre 170' }
		});
		expect(made.status).toBe(201);
		const canopy = ((await made.json()) as { component: { id: string } }).component.id;
		const place = await apiCall('POST', '/places', { bearer, body: { name: 'Limit strip', country: 'PT' } });
		const placeId = ((await place.json()) as { id: string }).id;
		for (let n = 1; n <= 9; n++) {
			const jump = await apiCall('POST', '/jumps', {
				bearer,
				body: {
					client_key: randomUUID(),
					place_id: placeId,
					jumped_on: `2026-09-${String(n).padStart(2, '0')}`,
					jump_type: 'belly',
					component_ids: [canopy]
				}
			});
			expect(jump.status, await jump.clone().text()).toBe(201);
		}

		// The owner sets the limit; nothing is filled in for them.
		await signIn(page, email, `/gear/${canopy}`);
		await expect(page.getByLabel('Limit in jumps')).toHaveValue('');
		await page.getByLabel('Limit in jumps').fill('10');
		await page.getByLabel('What is due then').fill('Reline');
		await page.getByRole('button', { name: 'Save changes' }).click();
		await expect(page.getByText('Saved privately.')).toBeVisible();
		await expect(page.getByRole('list', { name: 'Due dates' })).toContainText('Reline due in 1 jump');

		await page.goto('/jumps');
		const due = page.getByRole('list', { name: 'Due soon' });
		await expect(due).toContainText('Reline due in 1 jump');
		await expect(due.getByRole('link', { name: 'Sabre 170' })).toBeVisible();
	});
});
