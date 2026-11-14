import { randomBytes } from 'node:crypto';
import { expect, test, type Page } from '@playwright/test';
import { PASSWORD, createAccount } from './support/accounts.ts';

// Same production-cookie preview as the account tests.
const ORIGIN = 'https://127.0.0.1:4175';
test.use({ baseURL: ORIGIN, ignoreHTTPSErrors: true });

const token = () => `Zr${randomBytes(5).toString('hex')}`;

async function signIn(page: Page, email: string, password = PASSWORD, returnTo = '/profile') {
	await page.goto(`/sign-in?returnTo=${encodeURIComponent(returnTo)}`);
	await page.getByLabel('Email', { exact: true }).fill(email);
	await page.getByLabel('Password', { exact: true }).fill(password);
	await page.getByRole('button', { name: 'Sign in' }).click();
	await expect(page).toHaveURL(`${ORIGIN}${returnTo}`);
}

async function signInReviewer(page: Page, returnTo = '/review') {
	const email = process.env.E2E_REVIEWER_EMAIL;
	const password = process.env.E2E_REVIEWER_PASSWORD;
	if (!email || !password) throw new Error('E2E_REVIEWER_EMAIL/PASSWORD must be set');
	await signIn(page, email, password, returnTo);
}

/** Creates a published organizer and a published listing through the reviewer pages. */
async function publishThroughTools(page: Page, base: string): Promise<string> {
	await page.goto('/review/organizers/new');
	await page.getByLabel('Name', { exact: true }).fill(`${base} Org`);
	await page.getByLabel('Source link', { exact: true }).fill('https://example.org/org');
	await page.getByLabel('Source last checked').fill('2026-11-01');
	await page.getByLabel(/Publish now/).check();
	await page.getByRole('button', { name: 'Save' }).click();
	await expect(page.getByText('Saved.')).toBeVisible();

	await page.goto(`/review/listings/new?org_q=${base}`);
	await page.getByLabel('Title', { exact: true }).fill(`${base} Boogie`);
	await page.getByLabel('Type', { exact: true }).selectOption('boogie');
	await page.getByLabel('Organizer', { exact: true }).selectOption({ label: `${base} Org` });
	await page.getByLabel('Location note').fill('Airfield north of town');
	await page.getByLabel('Country', { exact: true }).selectOption('ES');
	await page.getByLabel('First day', { exact: true }).fill('2027-08-01');
	await page.getByLabel('Last day', { exact: true }).fill('2027-08-03');
	await page.getByLabel('Time zone of the dates').fill('Europe/Madrid');
	await page.getByLabel('Registration or contact link').fill('https://example.org/register');
	await page.getByLabel('Source link', { exact: true }).fill('https://example.org/events');
	await page.getByLabel('Source last checked').fill('2026-11-01');
	await page.getByRole('button', { name: 'Create draft' }).click();
	await expect(page.getByText('Saved.')).toBeVisible();
	const id = page.url().split('/').pop()!.split('?')[0];

	await page.getByRole('button', { name: 'Make review' }).click();
	await expect(page.getByText(/^review · version/)).toBeVisible();
	await page.getByRole('button', { name: 'Make published' }).click();
	await expect(page.getByText(/^published · version/)).toBeVisible();
	return id;
}

test.describe('maintenance tools', () => {
	test('members cannot open the tools', async ({ page }) => {
		await signIn(page, await createAccount({ label: 'member' }));
		const response = await page.goto('/review');
		expect(response?.status()).toBe(404);
		await expect(page.getByRole('link', { name: 'Maintenance' })).toHaveCount(0);
	});

	test('a reviewer publishes a sourced listing that guests then see', async ({ page, browser }) => {
		const base = token();
		await signInReviewer(page);
		const id = await publishThroughTools(page, base);

		const guest = await browser.newContext({ baseURL: ORIGIN, ignoreHTTPSErrors: true });
		const guestPage = await guest.newPage();
		await guestPage.goto(`/?q=${base}`);
		await expect(guestPage.getByRole('link', { name: `${base} Boogie` })).toHaveAttribute(
			'href',
			// The link carries the search, for "Back to results".
			`/events/${id}?results=${encodeURIComponent(`/?q=${base}`)}`
		);
		await guest.close();
	});

	test('an edit based on an old version is refused, not overwritten', async ({ page, browser }) => {
		const base = token();
		await signInReviewer(page);
		const id = await publishThroughTools(page, base);

		const second = await browser.newContext({ baseURL: ORIGIN, ignoreHTTPSErrors: true });
		const other = await second.newPage();
		await signInReviewer(other, `/review/listings/${id}`);

		await page.goto(`/review/listings/${id}`);
		await page.getByLabel('Summary (optional)').fill('First reviewer');
		await page.getByRole('button', { name: 'Save changes' }).click();
		await expect(page.getByText('Saved.')).toBeVisible();

		// The second reviewer's page still holds the old version.
		await other.getByLabel('Summary (optional)').fill('Second reviewer');
		await other.getByRole('button', { name: 'Save changes' }).click();
		await expect(other.getByRole('alert')).toContainText(
			'Someone changed this since you opened it'
		);
		await expect(other.getByLabel('Summary (optional)')).toHaveValue('Second reviewer');
		await second.close();

		await page.reload();
		await expect(page.getByLabel('Summary (optional)')).toHaveValue('First reviewer');
	});

	test('a member reports a problem and sees the reviewer outcome', async ({ page, browser }) => {
		const base = token();
		await signInReviewer(page);
		const id = await publishThroughTools(page, base);

		const memberContext = await browser.newContext({ baseURL: ORIGIN, ignoreHTTPSErrors: true });
		const member = await memberContext.newPage();
		await signIn(member, await createAccount({ label: 'reporter' }));
		await member.goto(`/events/${id}`);
		await member.getByRole('link', { name: 'Suggest a correction or report a problem' }).click();
		await member.getByLabel('Correct information').check();
		await member.getByLabel('Details', { exact: true }).fill(`${base}: the dates moved to September.`);
		await member.getByRole('button', { name: 'Send' }).click();
		await expect(member.getByText('Sent. You can follow its status below.')).toBeVisible();
		await expect(member.getByText('Waiting for review').first()).toBeVisible();

		await page.goto('/review/submissions');
		const item = page.getByRole('listitem').filter({ hasText: base });
		await expect(item).toBeVisible();
		await item.getByLabel('Note to the sender (optional)').fill('Dates updated from the source.');
		await item.getByRole('button', { name: 'Accept' }).click();
		await expect(page.getByText('Resolved as accepted.')).toBeVisible();

		await member.reload();
		const mine = member.getByRole('listitem').filter({ hasText: base });
		await expect(mine.getByText('Accepted')).toBeVisible();
		await expect(mine.getByText('Reviewer: Dates updated from the source.')).toBeVisible();
		await memberContext.close();
	});
});
