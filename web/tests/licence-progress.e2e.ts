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

test.describe('progress to the next licence', () => {
	test('a B licence holder with 60 jumps and 40 minutes of freefall sees progress toward C', async ({
		page
	}) => {
		const email = await createAccount({ label: 'progress' });
		const bearer = await apiSession(email);
		expect((await apiCall('PUT', '/me/licence', { bearer, body: { licence: 'b' } })).status).toBe(200);
		// 50 declared before 2025, then 10 entries of 4 minutes each: 60 jumps, 40 minutes.
		const baseline = await apiCall('PUT', '/history/baseline', {
			bearer,
			body: { prior_jumps: 50, before_on: '2025-01-01' }
		});
		expect(baseline.status).toBe(200);
		const place = await apiCall('POST', '/places', { bearer, body: { name: 'Farm strip', country: 'PT' } });
		const { id } = (await place.json()) as { id: string };
		for (let i = 1; i <= 10; i++) {
			const made = await apiCall('POST', '/jumps', {
				bearer,
				body: {
					client_key: randomUUID(),
					jumped_on: `2025-06-${String(i).padStart(2, '0')}`,
					jump_type: 'belly',
					place_id: id,
					freefall_seconds: 240
				}
			});
			expect(made.status).toBe(201);
		}

		await signIn(page, email, '/jumps');
		await expect(page.getByTestId('licence-progress')).toContainText(
			'Toward a C licence: 60 of 200 jumps, 40 minutes of 60 minutes of freefall.'
		);

		await page.getByRole('link', { name: 'Next licence details' }).click();
		const section = page.getByRole('region', { name: 'Next licence' });
		await expect(section).toContainText('Toward a C licence');
		await expect(section).toContainText('Jumps: 60 of 200 (140 to go).');
		await expect(section).toContainText(
			'Recorded freefall time: 40 minutes of 60 minutes (20 minutes to go).'
		);
		await expect(section).toContainText('in the jump total but not in the freefall time');
		await expect(section).toContainText(
			'checked by USPA and your instructors, not by this app (USPA SIM 3-1)'
		);
	});

	test('without a licence there is no progress, only the existing prompt', async ({ page }) => {
		const email = await createAccount({ label: 'noprogress' });
		await signIn(page, email, '/history');
		await expect(page.getByRole('region', { name: 'Jump currency' })).toContainText(
			'Set your licence to see your jump currency.'
		);
		await expect(page.getByRole('region', { name: 'Next licence' })).toHaveCount(0);
	});
});
