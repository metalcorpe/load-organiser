import { randomBytes } from 'node:crypto';
import { expect, test, type Page } from '@playwright/test';
import {
	PASSWORD,
	apiCall,
	createAccount,
	reviewerCredentials,
	reviewerSession
} from './support/accounts.ts';
import { SECURE_ORIGIN } from './support/origins.ts';

// Same production-cookie preview as the account tests.
const ORIGIN = SECURE_ORIGIN;
test.use({ baseURL: ORIGIN, ignoreHTTPSErrors: true });

const SOURCE = { source_url: 'https://example.org/dz-source', checked_on: '2026-11-01' };
const token = () => `Zq${randomBytes(5).toString('hex')}`;

interface CreatedVenue {
	id: string;
	name: string;
}

async function createVenue(
	reviewer: string,
	body: Record<string, unknown>
): Promise<CreatedVenue> {
	const response = await apiCall('POST', '/directory/venues', {
		bearer: reviewer,
		body: { country: 'ES', ...SOURCE, ...body }
	});
	expect(response.status).toBe(201);
	return (await response.json()) as CreatedVenue;
}

async function signIn(page: Page, email: string) {
	await page.goto('/sign-in');
	await page.getByLabel('Email', { exact: true }).fill(email);
	await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
	await page.getByRole('button', { name: 'Sign in' }).click();
	await expect(page.getByTestId('current-account')).toHaveText(email);
}

test.describe('public dropzone directory', () => {
	test('search by alias without accents and open a sourced listing', async ({ page }) => {
		const reviewer = await reviewerSession();
		const base = token();
		const venue = await createVenue(reviewer, {
			name: `${base} Ampuriabrava`,
			locality: 'Empuriabrava'
		});
		await apiCall('POST', `/directory/venues/${venue.id}/aliases`, {
			bearer: reviewer,
			body: { name: `${base} Empúriabrava` }
		});

		await page.goto('/dz');
		await page.getByLabel('Name, alias or former name').fill(`${base} empuriabrava`);
		await page.getByRole('button', { name: 'Search' }).click();
		await expect(page).toHaveURL(new RegExp(`/dz\\?q=${base}`));
		await page.getByRole('link', { name: `${base} Ampuriabrava` }).click();

		await expect(page.getByRole('heading', { level: 1 })).toHaveText(`${base} Ampuriabrava`);
		await expect(page.getByText('Empuriabrava, Spain')).toBeVisible();
		await expect(page.getByRole('heading', { name: 'Planning a visit?' })).toBeVisible();
		await expect(page.getByRole('link', { name: 'Suggest a correction' })).toBeVisible();

		// Where the listing came from is secondary: folded under "Listing details", opened from
		// the keyboard, and the date is labelled as a check against the source, nothing more.
		const source = page.getByRole('link', { name: 'example.org' });
		await expect(source).toBeHidden();
		const summary = page.locator('summary', { hasText: 'Listing details' });
		await summary.focus();
		await page.keyboard.press('Enter');
		await expect(source).toBeVisible();
		await expect(source).toHaveAttribute('href', SOURCE.source_url);
		const details = page.locator('details.listing-details');
		await expect(details).toContainText('Last checked against the source');
		await expect(details).toContainText('1 November 2026');
		await expect(page.getByRole('main')).not.toContainText(/verified|confirmed|official/i);
		await page.keyboard.press('Enter');
		await expect(source).toBeHidden();
	});

	test("a reviewer's internal note never reaches the public page", async ({ page, browser }) => {
		const reviewer = await reviewerSession();
		const marker = `dev-data:${token()} Unreviewed candidate, local development only.`;
		const venue = await createVenue(reviewer, {
			name: `${token()} Noted field`,
			internal_note: marker
		});
		await page.goto(`/dz/${venue.id}`);
		await page.locator('summary', { hasText: 'Listing details' }).click();
		const html = await page.content();
		expect(html).not.toContain('dev-data');
		expect(html).not.toContain('Unreviewed candidate');
		expect(html).not.toContain('internal_note');

		// The reviewer still has it, in the reviewer tools.
		const signedIn = await browser.newContext({ ignoreHTTPSErrors: true, baseURL: ORIGIN });
		const reviewerPage = await signedIn.newPage();
		const { email, password } = reviewerCredentials();
		await reviewerPage.goto('/sign-in');
		await reviewerPage.getByLabel('Email', { exact: true }).fill(email);
		await reviewerPage.getByLabel('Password', { exact: true }).fill(password);
		await reviewerPage.getByRole('button', { name: 'Sign in' }).click();
		await expect(reviewerPage.getByTestId('current-account')).toBeVisible();
		await reviewerPage.goto(`/review/dropzones/${venue.id}`);
		await expect(reviewerPage.getByLabel(/Internal note/)).toHaveValue(marker);
		await signedIn.close();
	});

	test('a merged listing redirects to the surviving one', async ({ page, request }) => {
		const reviewer = await reviewerSession();
		const keep = await createVenue(reviewer, { name: `${token()} Keep` });
		const dupe = await createVenue(reviewer, { name: `${token()} Duplicate` });
		const merged = await apiCall('POST', `/directory/venues/${dupe.id}/merge`, {
			bearer: reviewer,
			body: { into: keep.id }
		});
		expect(merged.status).toBe(200);

		const response = await request.get(`/dz/${dupe.id}`, { maxRedirects: 0 });
		expect(response.status()).toBe(301);
		expect(response.headers()['location']).toBe(`/dz/${keep.id}`);
		await page.goto(`/dz/${dupe.id}`);
		await expect(page).toHaveURL(`${ORIGIN}/dz/${keep.id}`);
		await expect(page.getByText(dupe.name)).toBeVisible(); // kept as a merged name
	});

	test('closed listings stay visible, drafts and unknown ids do not', async ({ page, request }) => {
		const reviewer = await reviewerSession();
		const closed = await createVenue(reviewer, { name: `${token()} Old field` });
		await apiCall('POST', `/directory/venues/${closed.id}/status`, {
			bearer: reviewer,
			body: { status: 'closed' }
		});
		await page.goto(`/dz/${closed.id}`);
		await expect(page.getByRole('heading', { name: 'Closed' })).toBeVisible();

		const draft = await createVenue(reviewer, { name: token(), listed: false });
		for (const path of [`/dz/${draft.id}`, `/dz/${crypto.randomUUID()}`, '/dz/not-a-uuid']) {
			expect((await request.get(path)).status(), path).toBe(404);
		}
	});

	test('who runs it, its season and aircraft, as the source states; a reviewer edits them', async ({
		page
	}) => {
		const reviewer = await reviewerSession();
		const venue = await createVenue(reviewer, {
			name: `${token()} Operator field`,
			operators: [
				{ name: 'Skydive Example', url: 'https://skydive.example/' },
				{ name: 'Paraclub Example' }
			],
			season: 'April–October, weekends',
			aircraft: 'Pilatus PC-6'
		});
		await page.goto(`/dz/${venue.id}`);
		// One operator website: one "Visit website" action, the name itself plain text.
		const website = page.getByRole('link', { name: 'Visit website' });
		await expect(website).toHaveAttribute('href', 'https://skydive.example/');
		await expect(website).toHaveAttribute('rel', /nofollow/);
		await expect(page.getByRole('link', { name: 'Skydive Example' })).toHaveCount(0);
		await expect(page.getByText('Skydive Example, Paraclub Example')).toBeVisible();
		await expect(page.getByText('April–October, weekends')).toBeVisible();
		await expect(page.getByText('Pilatus PC-6')).toBeVisible();

		const { email, password } = reviewerCredentials();
		await page.goto('/sign-in');
		await page.getByLabel('Email', { exact: true }).fill(email);
		await page.getByLabel('Password', { exact: true }).fill(password);
		await page.getByRole('button', { name: 'Sign in' }).click();
		await expect(page.getByTestId('current-account')).toBeVisible();
		await page.goto(`/review/dropzones/${venue.id}`);
		await page.getByLabel('Operator 1 name').fill('New Operator');
		await page.getByLabel('Operator 1 website').fill('');
		await page.getByLabel('Operator 2 name').fill('');
		await page.getByRole('button', { name: 'Save', exact: true }).click();
		await expect(page.getByRole('status').filter({ hasText: 'Saved.' })).toBeVisible();

		await page.goto(`/dz/${venue.id}`);
		await expect(page.getByText('New Operator')).toBeVisible();
		await expect(page.getByRole('link', { name: 'Visit website' })).toHaveCount(0);
		await expect(page.getByText('Paraclub Example')).toHaveCount(0);
	});
});

test.describe('private provisional places', () => {
	test('add a place without a listing, link it, and keep it private', async ({ page, browser }) => {
		const reviewer = await reviewerSession();
		const listed = await createVenue(reviewer, { name: `${token()} Listed DZ` });
		const owner = await createAccount({ label: 'places' });
		const placeName = `${token()} farm strip`;

		await signIn(page, owner);
		await page.goto('/places');
		await page.getByLabel('Name', { exact: true }).fill(placeName);
		await page.getByLabel('Country', { exact: true }).selectOption('NZ');
		await page.getByRole('button', { name: 'Save place' }).click();
		await expect(page.getByText('Place saved.')).toBeVisible();
		const card = page.getByTestId('place').filter({ hasText: placeName });
		await expect(card).toContainText('New Zealand');
		await expect(card).toContainText('not linked to a listed dropzone');

		// Link it to a listed dropzone found by search.
		await card.getByRole('link', { name: 'Link to a listed dropzone' }).click();
		await page.getByLabel('Search listed dropzones').fill(listed.name);
		await page.getByRole('button', { name: 'Search' }).click();
		await page.getByRole('button', { name: `Link to ${listed.name}, Spain` }).click();
		await expect(page.getByTestId('place').filter({ hasText: placeName })).toContainText(
			`linked to ${listed.name}`
		);

		// Not public, and not visible to another account.
		const publicSearch = await apiCall('GET', `/venues?q=${encodeURIComponent(placeName)}`);
		expect(((await publicSearch.json()) as { items: unknown[] }).items).toEqual([]);
		const listing = await page.request.get(`/dz/${listed.id}`);
		expect(await listing.text()).not.toContain(placeName);
		const other = await browser.newContext({ baseURL: ORIGIN, ignoreHTTPSErrors: true });
		const otherPage = await other.newPage();
		await signIn(otherPage, await createAccount({ label: 'other' }));
		await otherPage.goto('/places');
		await expect(otherPage.getByText(placeName)).toHaveCount(0);
		await other.close();

		// Remove it.
		await page
			.getByTestId('place')
			.filter({ hasText: placeName })
			.getByRole('button', { name: 'Remove' })
			.click();
		await expect(page.getByText(placeName)).toHaveCount(0);
	});

	test('an unconfirmed account is told why it cannot save', async ({ page }) => {
		const owner = await createAccount({ verified: false, label: 'unconfirmed' });
		await signIn(page, owner);
		await page.goto('/places');
		await page.getByLabel('Name', { exact: true }).fill('Somewhere');
		await page.getByLabel('Country', { exact: true }).selectOption('ES');
		await page.getByRole('button', { name: 'Save place' }).click();
		await expect(page.getByRole('alert')).toContainText('Confirm your email address');
	});
});
