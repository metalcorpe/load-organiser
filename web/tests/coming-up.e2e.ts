import { randomBytes } from 'node:crypto';
import { expect, test, type Page } from '@playwright/test';
import {
	PASSWORD,
	apiCall,
	apiSession,
	createAccount,
	reviewerSession
} from './support/accounts.ts';

// Same production-cookie preview as the account tests.
const ORIGIN = 'https://127.0.0.1:4175';
test.use({ baseURL: ORIGIN, ignoreHTTPSErrors: true });

const SOURCE = { source_url: 'https://example.org/coming-up', checked_on: '2026-11-01' };

async function signIn(page: Page, email: string, returnTo: string) {
	await page.goto(`/sign-in?returnTo=${encodeURIComponent(returnTo)}`);
	await page.getByLabel('Email', { exact: true }).fill(email);
	await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
	await page.getByRole('button', { name: 'Sign in' }).click();
	await expect(page).toHaveURL(`${ORIGIN}${returnTo}`);
}

const pad = (n: number) => String(n).padStart(2, '0');
/** The local calendar day `offset` days from today, as YYYY-MM-DD. */
function day(offset: number): string {
	const d = new Date();
	d.setDate(d.getDate() + offset);
	return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

async function created(path: string, bearer: string, body: unknown): Promise<{ id: string }> {
	const response = await apiCall('POST', path, { bearer, body });
	expect(response.status, `${path}: ${await response.clone().text()}`).toBeLessThan(300);
	return (await response.json()) as { id: string };
}

/** A published listing from `start` to `end`, optionally moved on to `status`. */
async function listing(title: string, start: string, end: string, status?: string) {
	const reviewer = await reviewerSession();
	const provider = await created('/directory/providers', reviewer, {
		name: `${title} Org`,
		kind: 'organization',
		...SOURCE,
		publish: true
	});
	const item = await created('/directory/opportunities', reviewer, {
		title,
		category: 'boogie',
		provider_id: provider.id,
		country: 'PT',
		location_note: 'Evora airfield',
		starts_on: start,
		ends_on: end,
		time_zone: 'Europe/Lisbon',
		registration_url: 'https://example.org/register',
		...SOURCE
	});
	for (const next of ['review', 'published', ...(status ? [status] : [])]) {
		await created(`/directory/opportunities/${item.id}/status`, reviewer, { status: next });
	}
	return item.id;
}

test.describe('coming up on the logbook', () => {
	test('a saved listing next month and a plan next week appear soonest first', async ({ page }) => {
		const tag = randomBytes(3).toString('hex');
		const boogie = await listing(`Autumn boogie ${tag}`, day(35), day(37));
		const cancelled = await listing(`Cancelled camp ${tag}`, day(20), day(21), 'cancelled');

		const email = await createAccount({ label: 'coming' });
		const bearer = await apiSession(email);
		for (const id of [boogie, cancelled]) {
			expect((await apiCall('PUT', `/saved/${id}`, { bearer })).status).toBeLessThan(300);
		}
		const place = await created('/places', bearer, { name: 'Farm strip', country: 'PT' });
		await created('/plans', bearer, {
			title: `Week trip ${tag}`,
			starts_on: day(7),
			ends_on: day(8),
			place_id: place.id
		});

		await signIn(page, email, '/jumps');
		const list = page.getByRole('list', { name: 'Coming up' });
		const items = list.getByRole('listitem');
		await expect(items).toHaveCount(2);
		await expect(items.nth(0)).toContainText(`Week trip ${tag}`);
		await expect(items.nth(0)).toContainText('Farm strip');
		await expect(items.nth(1)).toContainText(`Autumn boogie ${tag}`);
		await expect(list).not.toContainText('Cancelled camp');

		await expect(page.getByRole('link', { name: 'See all saved' })).toHaveAttribute('href', '/saved');
		await expect(page.getByRole('link', { name: 'See all plans' })).toHaveAttribute('href', '/plans');
		await items.nth(1).getByRole('link', { name: `Autumn boogie ${tag}` }).click();
		await expect(page).toHaveURL(`${ORIGIN}/events/${boogie}`);

		// A filtered logbook shows none of it.
		await page.goto('/jumps?type=belly');
		await expect(page.getByRole('list', { name: 'Coming up' })).toHaveCount(0);
	});

	test('nothing coming up shows nothing', async ({ page }) => {
		await signIn(page, await createAccount({ label: 'nothing' }), '/jumps');
		await expect(page.getByRole('heading', { name: 'Logbook' })).toBeVisible();
		await expect(page.getByRole('list', { name: 'Coming up' })).toHaveCount(0);
	});
});
