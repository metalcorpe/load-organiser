import { expect, test, type Page } from '@playwright/test';
import { randomBytes, randomUUID } from 'node:crypto';
import { PASSWORD, apiCall, apiSession, createAccount, reviewerSession } from './support/accounts.ts';

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

/** A listed dropzone, and a jumper who logged two jumps there (through the API). */
async function setUp(): Promise<{ venueId: string; owner: string }> {
	const created = await apiCall('POST', '/directory/venues', {
		bearer: await reviewerSession(),
		body: {
			name: `Yj${randomBytes(5).toString('hex')} Skydive`,
			country: 'ES',
			source_url: 'https://example.org/dz',
			checked_on: '2026-11-01'
		}
	});
	expect(created.status).toBe(201);
	const venueId = ((await created.json()) as { id: string }).id;
	const owner = await createAccount({ label: 'dzmine' });
	const bearer = await apiSession(owner);
	for (const day of ['2026-08-01', '2026-09-14']) {
		const sent = await apiCall('POST', '/jumps', {
			bearer,
			body: { client_key: randomUUID(), jumped_on: day, jump_type: 'belly', venue_id: venueId }
		});
		expect(sent.status, await sent.clone().text()).toBe(201);
	}
	return { venueId, owner };
}

test.describe('your jumps at a dropzone', () => {
	test('the owner sees their own count, guests and others do not', async ({ page, browser }) => {
		const { venueId, owner } = await setUp();

		// A guest: nothing of it, not even in the page data.
		const guest = await browser.newContext({ ignoreHTTPSErrors: true });
		const guestPage = await guest.newPage();
		const response = await guestPage.goto(`${ORIGIN}/dz/${venueId}`);
		await expect(guestPage.getByRole('heading', { level: 1 })).toBeVisible();
		await expect(guestPage.getByRole('region', { name: 'Your jumps here' })).toHaveCount(0);
		await expect(guestPage.getByRole('link', { name: 'Log a jump here' })).toHaveCount(0);
		const html = (await response?.text()) ?? '';
		expect(html).not.toContain('You logged');
		expect(html).not.toMatch(/"?mine"?:\{/);
		await guest.close();

		// The owner.
		await signIn(page, owner);
		await page.goto(`/dz/${venueId}`);
		const mine = page.getByRole('region', { name: 'Your jumps here' });
		// "Sep", "Sept" or "September", depending on the format and locale data.
		await expect(mine).toContainText(/You logged 2 jumps here, last on 14 Sep(?:t|tember)? 2026\./);
		await expect(mine.getByRole('link', { name: 'Log a jump here' })).toHaveAttribute(
			'href',
			`/jumps/new?venue=${venueId}`
		);
		await mine.getByRole('link', { name: '2 jumps' }).click();
		await expect(page.getByRole('list', { name: 'Jumps' }).getByRole('listitem')).toHaveCount(2);

		// Another signed-in jumper sees only their own (none), never the owner's.
		const other = await browser.newContext({ ignoreHTTPSErrors: true, baseURL: ORIGIN });
		const otherPage = await other.newPage();
		await signIn(otherPage, await createAccount({ label: 'dzother' }));
		await otherPage.goto(`/dz/${venueId}`);
		const theirs = otherPage.getByRole('region', { name: 'Your jumps here' });
		await expect(theirs).toContainText('You have not logged a jump here yet.');
		await expect(theirs).not.toContainText('You logged');
		await theirs.getByRole('link', { name: 'Log a jump here' }).click();
		await expect(otherPage).toHaveURL(`${ORIGIN}/jumps/new?venue=${venueId}`);
		await other.close();
	});
});
