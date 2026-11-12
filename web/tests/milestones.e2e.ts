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

async function jumps(bearer: string, count: number, from: string, extra: Record<string, unknown> = {}) {
	const place = await apiCall('POST', '/places', { bearer, body: { name: 'Farm strip', country: 'PT' } });
	const { id } = (await place.json()) as { id: string };
	const start = new Date(`${from}T00:00:00Z`);
	for (let i = 0; i < count; i++) {
		const on = new Date(start.getTime() + i * 86_400_000).toISOString().slice(0, 10);
		const made = await apiCall('POST', '/jumps', {
			bearer,
			body: { client_key: randomUUID(), jumped_on: on, jump_type: 'belly', place_id: id, ...extra }
		});
		expect(made.status).toBe(201);
	}
}

test.describe('milestones', () => {
	test('a 25th jump shows "25th jump" with its date, newest first', async ({ page }) => {
		const email = await createAccount({ label: 'milestone' });
		const bearer = await apiSession(email);
		await jumps(bearer, 25, '2026-02-01'); // the 25th on 25 February 2026

		await signIn(page, email, '/history');
		const list = page.getByRole('list', { name: 'Milestones' });
		const items = list.getByRole('listitem');
		await expect(items.first()).toContainText('25th jump');
		await expect(items.first()).toContainText('25 February 2026');
		await expect(list).toContainText('1st jump');
		await expect(list).toContainText('First belly / formation jump');
		await expect(list).toContainText('First jump at Farm strip');
	});

	test('a milestone within the prior jump count is listed before this logbook', async ({ page }) => {
		const email = await createAccount({ label: 'prior' });
		const bearer = await apiSession(email);
		const baseline = await apiCall('PUT', '/history/baseline', {
			bearer,
			body: { prior_jumps: 40, before_on: '2026-01-01' }
		});
		expect(baseline.status).toBe(200);
		await jumps(bearer, 10, '2026-03-01'); // jumps 41 to 50: the 50th on 10 March

		await signIn(page, email, '/history');
		const list = page.getByRole('list', { name: 'Milestones' });
		await expect(list.getByRole('listitem').first()).toContainText('50th jump');
		await expect(list.getByRole('listitem').first()).toContainText('10 March 2026');
		await expect(list.getByRole('listitem').filter({ hasText: '25th jump' })).toContainText(
			'before you kept this logbook'
		);
	});
});
