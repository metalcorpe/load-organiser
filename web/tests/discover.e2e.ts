import { randomBytes } from 'node:crypto';
import { expect, test, type Page } from '@playwright/test';
import { PASSWORD, apiCall, createAccount, reviewerSession } from './support/accounts.ts';

// Same production-cookie preview as the account tests.
const ORIGIN = 'https://127.0.0.1:4175';
test.use({ baseURL: ORIGIN, ignoreHTTPSErrors: true });

const SOURCE = { source_url: 'https://example.org/events', checked_on: '2026-11-01' };
const token = () => `Zd${randomBytes(5).toString('hex')}`;

interface Listing {
	id: string;
	title: string;
	provider: string;
}

async function ok(response: Response, status = 200): Promise<Record<string, string>> {
	expect(response.status).toBe(status);
	return (await response.json()) as Record<string, string>;
}

/** A published, sourced listing created through the reviewer API. */
async function publishListing(
	title: string,
	extra: Record<string, unknown> = {}
): Promise<Listing> {
	const reviewer = await reviewerSession();
	const provider = await ok(
		await apiCall('POST', '/directory/providers', {
			bearer: reviewer,
			body: { name: `${title} Org`, kind: 'organization', ...SOURCE, publish: true }
		}),
		201
	);
	const draft = await ok(
		await apiCall('POST', '/directory/opportunities', {
			bearer: reviewer,
			body: {
				title,
				category: 'boogie',
				provider_id: provider.id,
				country: 'PT',
				location_note: 'Coastal airfield',
				starts_on: '2027-07-10',
				ends_on: '2027-07-14',
				time_zone: 'Europe/Lisbon',
				disciplines: ['freefly'],
				audience: ['licensed'],
				prerequisites: 'C licence or 200 jumps',
				registration_url: 'https://example.org/register',
				...SOURCE,
				...extra
			}
		}),
		201
	);
	for (const status of ['review', 'published']) {
		await ok(
			await apiCall('POST', `/directory/opportunities/${draft.id}/status`, {
				bearer: reviewer,
				body: { status }
			})
		);
	}
	return { id: draft.id, title, provider: `${title} Org` };
}

async function signInHere(page: Page, email: string) {
	await page.getByLabel('Email', { exact: true }).fill(email);
	await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
	await page.getByRole('button', { name: 'Sign in' }).click();
}

test.describe('discover board', () => {
	test('a guest filters the board and opens a sourced listing', async ({ page }) => {
		const base = token();
		const listing = await publishListing(`${base} Summer boogie`);

		await page.goto('/');
		// The country filter offers covered countries only (no listing anywhere uses AF).
		const countries = page.getByLabel('Country');
		await expect(countries.locator('option[value="PT"]')).toHaveCount(1);
		await expect(countries.locator('option[value="AF"]')).toHaveCount(0);
		// A shared link to an uncovered country keeps its selection.
		await page.goto('/?country=AF');
		await expect(page.getByLabel('Country')).toHaveValue('AF');
		await page.goto('/');
		await page.getByLabel('Title or organizer').fill(base);
		// The filters beyond the search box are folded away until asked for.
		await expect(page.getByLabel('Country')).toBeHidden();
		await page.locator('summary', { hasText: 'Filters' }).click();
		await page.getByLabel('Country').selectOption('PT');
		await page.getByLabel('Discipline').selectOption('freefly');
		await page.getByRole('button', { name: 'Show listings' }).click();
		await expect(page).toHaveURL(new RegExp(`q=${base}.*country=PT`));
		const results = page.getByRole('list', { name: 'Listings' });
		await expect(results.getByRole('link')).toHaveText([listing.title]);
		// Active filters show as chips; each removes only itself.
		await expect(page.locator('summary', { hasText: 'Filters (2)' })).toBeVisible();
		const chips = page.getByRole('list', { name: 'Active filters' });
		await chips.getByRole('link', { name: 'Remove Freefly' }).click();
		await expect(page).toHaveURL(new RegExp(`q=${base}.*country=PT`));
		await expect(page).not.toHaveURL(/discipline=/);
		await expect(results.getByRole('link')).toHaveText([listing.title]);
		// Clearing filters resets the form fields, not just the URL.
		await page.getByRole('link', { name: 'Clear filters' }).first().click();
		await expect(page).toHaveURL(`${ORIGIN}/`);
		await expect(page.getByLabel('Title or organizer')).toHaveValue('');
		await expect(page.getByLabel('Country')).toHaveValue('');

		// A filter that excludes it gives an honest empty state.
		await page.goto(`/?q=${base}&discipline=wingsuit`);
		await expect(page.getByText('No listings match')).toBeVisible();

		await page.goto(`/?q=${base}`);
		await page.getByRole('link', { name: listing.title }).click();
		await expect(page.getByRole('heading', { level: 1 })).toHaveText(listing.title);
		await expect(page.getByText('10–14 July 2027 (Europe/Lisbon local dates)')).toBeVisible();
		await expect(page.getByText('C licence or 200 jumps')).toBeVisible();
		await expect(page.getByText('As stated by the source')).toBeVisible();
		await expect(page.getByText('Availability is not tracked here')).toBeVisible();
		await expect(page.getByRole('link', { name: 'Open organizer registration' })).toHaveAttribute(
			'href',
			'https://example.org/register'
		);
		await page.getByRole('link', { name: listing.provider }).click();
		await expect(page.getByRole('heading', { level: 1 })).toHaveText(listing.provider);
		await expect(page.getByRole('link', { name: listing.title })).toBeVisible();
	});

	test('the sign-in sheet closes with Escape and Back, and returns focus', async ({ page }) => {
		const listing = await publishListing(`${token()} Sheet boogie`);
		await page.goto(`/events/${listing.id}`);
		await page.locator('html[data-sign-in-sheet="ready"]').waitFor();
		const trigger = page.getByRole('link', { name: 'Sign in to save this privately' });
		const sheet = page.getByRole('dialog', { name: 'Sign in' });
		await trigger.click();
		await expect(sheet).toBeVisible();
		await expect(sheet.getByLabel('Email', { exact: true })).toBeFocused();
		await page.keyboard.press('Escape');
		await expect(sheet).toBeHidden();
		await expect(trigger).toBeFocused();
		await expect(page).toHaveURL(`${ORIGIN}/events/${listing.id}`);
		await trigger.click();
		await expect(sheet).toBeVisible();
		await page.goBack();
		await expect(sheet).toBeHidden();
		await expect(page).toHaveURL(`${ORIGIN}/events/${listing.id}`);
	});

	test('without JavaScript, sign in to save opens the full sign-in page', async ({ browser }) => {
		const listing = await publishListing(`${token()} Plain boogie`);
		const plain = await browser.newContext({ javaScriptEnabled: false, ignoreHTTPSErrors: true });
		const page = await plain.newPage();
		await page.goto(`${ORIGIN}/events/${listing.id}`);
		await page.getByRole('link', { name: 'Sign in to save this privately' }).click();
		await expect(page).toHaveURL(/\/sign-in\?returnTo=/);
		await expect(page.getByRole('heading', { level: 1, name: 'Sign in' })).toBeVisible();
		await plain.close();
	});

	test('sign in to save returns to the listing and saves only on request', async ({ page }) => {
		const listing = await publishListing(`${token()} Canopy course`);
		const email = await createAccount({ label: 'saver' });

		await page.goto(`/events/${listing.id}`);
		// A tap before the scripts load follows the plain link (the fallback); wait for the sheet.
		await page.locator('html[data-sign-in-sheet="ready"]').waitFor();
		await page.getByRole('link', { name: 'Sign in to save this privately' }).click();
		// The sign-in opens as a sheet over the listing; the address does not change.
		const sheet = page.getByRole('dialog', { name: 'Sign in' });
		await expect(sheet).toBeVisible();
		await expect(page).toHaveURL(`${ORIGIN}/events/${listing.id}`);
		await sheet.getByLabel('Email', { exact: true }).fill(email);
		await sheet.getByLabel('Password', { exact: true }).fill(PASSWORD);
		await sheet.getByRole('button', { name: 'Sign in' }).click();
		await expect(page).toHaveURL(`${ORIGIN}/events/${listing.id}?save=1`);
		await expect(page.getByText('You signed in to save this listing')).toBeVisible();

		await page.getByRole('button', { name: 'Save privately' }).click();
		await expect(page.getByText('Saved privately — you are not registered.')).toBeVisible();
		// Saving again is a no-op from the saved list's point of view.
		await page.reload();
		await expect(page.getByRole('button', { name: 'Remove from saved' })).toBeVisible();

		await page.goto('/saved');
		const saved = page.getByRole('list', { name: 'Saved listings' });
		await expect(saved.getByRole('link', { name: listing.title })).toHaveCount(1);

		// Plan a visit from the saved item, with dates starting from the listing.
		await saved.getByRole('link', { name: 'Plan a visit' }).click();
		await expect(page.getByLabel('Title')).toHaveValue(listing.title);
		await expect(page.getByLabel('First day')).toHaveValue('2027-07-10');
		await page.getByLabel('First day').fill('2027-07-11');
		await page.getByRole('button', { name: 'Save plan' }).click();
		await expect(page.getByText('Plan saved privately.')).toBeVisible();
		const plans = page.getByRole('list', { name: 'Your plans' });
		await expect(plans.getByText('Your dates: 11–14 July 2027')).toBeVisible();
		await expect(plans.getByText("The listing's dates are 10–14 July 2027")).toBeVisible();

		await page.goto('/saved');
		await page.getByRole('button', { name: 'Remove' }).click();
		await expect(page.getByText('Removed from saved.')).toBeVisible();
		await expect(page.getByText('You have not saved any listings')).toBeVisible();
	});

	test('saves are not visible to anyone else', async ({ page, browser }) => {
		const listing = await publishListing(`${token()} Private check`);
		const owner = await createAccount({ label: 'owner' });
		await page.goto('/sign-in?returnTo=%2Fsaved');
		await signInHere(page, owner);
		await page.goto(`/events/${listing.id}`);
		await page.getByRole('button', { name: 'Save privately' }).click();
		await expect(page.getByText('Saved privately')).toBeVisible();

		const other = await browser.newContext({ baseURL: ORIGIN, ignoreHTTPSErrors: true });
		const otherPage = await other.newPage();
		await otherPage.goto('/sign-in?returnTo=%2Fsaved');
		await signInHere(otherPage, await createAccount({ label: 'other' }));
		await expect(otherPage).toHaveURL(`${ORIGIN}/saved`);
		await expect(otherPage.getByText('You have not saved any listings')).toBeVisible();
		await otherPage.goto(`/events/${listing.id}`);
		await expect(otherPage.getByRole('button', { name: 'Save privately' })).toBeVisible();
		await other.close();

		// A guest sees no trace of anyone's save.
		const guest = await browser.newContext({ baseURL: ORIGIN, ignoreHTTPSErrors: true });
		const guestPage = await guest.newPage();
		await guestPage.goto(`/events/${listing.id}`);
		await expect(
			guestPage.getByRole('link', { name: 'Sign in to save this privately' })
		).toBeVisible();
		await expect(guestPage.getByText('Saved privately')).toHaveCount(0);
		await guest.close();
	});

	test('an unconfirmed account is told why it cannot save', async ({ page }) => {
		const listing = await publishListing(`${token()} Unconfirmed`);
		const email = await createAccount({ verified: false, label: 'unconfirmed' });
		await page.goto(`/sign-in?returnTo=${encodeURIComponent(`/events/${listing.id}`)}`);
		await signInHere(page, email);
		await page.getByRole('button', { name: 'Save privately' }).click();
		await expect(page.getByRole('alert')).toHaveText(
			'Confirm your email address before saving privately.'
		);
	});
});
