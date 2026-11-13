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
		// Type, discipline and audience are folded inside the panel until asked for.
		await expect(page.getByLabel('Discipline')).toBeHidden();
		await page.locator('summary', { hasText: 'Type, discipline and audience' }).click();
		await page.getByLabel('Discipline').selectOption('freefly');
		await page.getByRole('button', { name: 'Show listings' }).click();
		await expect(page).toHaveURL(new RegExp(`q=${base}.*country=PT`));
		const results = page.getByRole('list', { name: 'Listings' });
		await expect(results.getByRole('link')).toHaveText([listing.title]);
		// Active filters show as chips; each removes only itself.
		await expect(page.locator('summary', { hasText: 'Filters (2)' })).toBeVisible();
		// An active discipline opens its group on the results page.
		await page.locator('summary', { hasText: 'Filters (2)' }).click();
		await expect(page.getByLabel('Discipline')).toBeVisible();
		await expect(page.getByLabel('Discipline')).toHaveValue('freefly');
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

	test('header Sign in opens the sheet for this page; Close closes it; members never get it', async ({
		page
	}) => {
		await page.goto('/dz');
		await page.locator('html[data-sign-in-sheet="ready"]').waitFor();
		const trigger = page.getByRole('banner').getByRole('link', { name: 'Sign in' });
		await expect(trigger).toHaveAttribute('href', '/sign-in?returnTo=%2Fdz');
		await trigger.click();
		const sheet = page.getByRole('dialog', { name: 'Sign in' });
		await expect(sheet).toBeVisible();
		await sheet.getByRole('button', { name: 'Close' }).click();
		await expect(sheet).toBeHidden();
		await expect(trigger).toBeFocused();
		await expect(page).toHaveURL(`${ORIGIN}/dz`);

		// Signed in from the sheet, the member is back on /dz with no sheet and no Sign in.
		await trigger.click();
		await sheet.getByLabel('Email', { exact: true }).fill(await createAccount({ label: 'sheet' }));
		await sheet.getByLabel('Password', { exact: true }).fill(PASSWORD);
		await sheet.getByRole('button', { name: 'Sign in' }).click();
		await expect(page).toHaveURL(`${ORIGIN}/dz`);
		await expect(page.getByRole('navigation', { name: 'Primary' })).toBeVisible();
		await expect(page.getByRole('dialog')).toHaveCount(0);
		await expect(page.locator('html[data-sign-in-sheet]')).toHaveCount(0);
		// The enhanced sign-in sets the same production cookie as the plain post.
		const cookie = (await page.context().cookies(ORIGIN)).find(
			(c) => c.name === '__Host-organiser_session'
		);
		expect(cookie).toMatchObject({ httpOnly: true, secure: true, sameSite: 'Lax', path: '/' });
		expect(cookie?.domain).toBe('127.0.0.1');
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

/** The UTC calendar day `offset` days from today, as YYYY-MM-DD. */
function daysFromToday(offset: number): string {
	return new Date(Date.now() + offset * 86_400_000).toISOString().slice(0, 10);
}

test.describe('search context and the filter panel', () => {
	test('filtered results → event → back to results; All events resets', async ({ page }) => {
		const base = token();
		const listing = await publishListing(`${base} Return boogie`);
		const search = `/?q=${base}&country=PT&from=2027-07-01`;
		await page.goto(search);
		await page.getByRole('link', { name: listing.title }).click();
		await expect(page.getByRole('heading', { level: 1 })).toHaveText(listing.title);
		await expect(page).toHaveURL(/[?&]results=/);
		const back = page.getByRole('link', { name: 'Back to results' });
		await expect(back).toHaveAttribute('href', search);
		await back.click();
		await expect(page).toHaveURL(`${ORIGIN}${search}`);
		// The search form shows the same search again.
		await expect(page.getByLabel('Title or organizer')).toHaveValue(base);
		await expect(page.getByLabel('Country')).toHaveValue('PT');
		await expect(page.getByLabel('From', { exact: true })).toHaveValue('2027-07-01');

		// "All events" is the explicit reset.
		await page.getByRole('link', { name: listing.title }).click();
		await page.getByRole('link', { name: 'All events' }).click();
		await expect(page).toHaveURL(`${ORIGIN}/`);
	});

	test('a direct or forged link offers only All events', async ({ page }) => {
		const listing = await publishListing(`${token()} Direct boogie`);
		for (const query of [
			'',
			'?results=%2F%2Fevil.example%2F%3Fcountry%3DPT',
			'?results=https%3A%2F%2Fevil.example%2F',
			'?results=%2F%5Cevil.example',
			'?results=%2Fprofile',
			'?results=%2F',
			// A context id with no matching cookie (forged, or expired) gives no context either.
			'?ctx=AAAAAAAAAAAAAAAA',
			'?save=1&ctx=not-a-valid-id'
		]) {
			await page.goto(`/events/${listing.id}${query}`);
			await expect(page.getByRole('heading', { level: 1 })).toHaveText(listing.title);
			await expect(page.getByRole('link', { name: 'Back to results' }), query).toHaveCount(0);
			await expect(page.getByRole('link', { name: 'All events' })).toHaveAttribute('href', '/');
		}
		// With or without a search context, one canonical address.
		for (const query of ['', `?results=${encodeURIComponent('/?country=PT')}`]) {
			await page.goto(`/events/${listing.id}${query}`);
			await expect(page.locator('link[rel="canonical"]')).toHaveAttribute(
				'href',
				`${ORIGIN}/events/${listing.id}`
			);
		}
	});

	test('the search context survives signing in from the sheet and saving', async ({ page }) => {
		const base = token();
		const listing = await publishListing(`${base} Context boogie`);
		const search = `/?q=${base}&country=PT`;
		await page.goto(search);
		await page.getByRole('link', { name: listing.title }).click();
		await page.locator('html[data-sign-in-sheet="ready"]').waitFor();
		await page.getByRole('link', { name: 'Sign in to save this privately' }).click();
		const sheet = page.getByRole('dialog', { name: 'Sign in' });
		await signInHere(page, await createAccount({ label: 'context' }));
		await expect(sheet).toHaveCount(0);
		await expect(page).toHaveURL(/\?save=1&results=/);
		await page.getByRole('button', { name: 'Save privately' }).click();
		await expect(page.getByText('Saved privately — you are not registered.')).toBeVisible();
		await page.getByRole('link', { name: 'Back to results' }).click();
		await expect(page).toHaveURL(`${ORIGIN}${search}`);
	});

	test('a long search on its second page survives sign-in and saving', async ({ page, browser }) => {
		test.setTimeout(120_000);
		const base = token();
		// Accented text is encoded twice inside the sign-in return path: well past its limit.
		const phrase = `${base} ${'é'.repeat(60)}`;
		// One more than a page (20), one at a time: reviewer sessions are not shared.
		for (let i = 0; i < 21; i++) await publishListing(`${phrase} ${i}`);
		await page.goto(`/?q=${encodeURIComponent(phrase)}&country=PT&from=2027-07-01`);
		await page.getByRole('link', { name: 'More listings' }).click();
		await expect(page).toHaveURL(/[?&]cursor=/);
		const second = new URL(page.url());
		const results = `${second.pathname}${second.search}`;

		await page.getByRole('link', { name: new RegExp(base) }).first().click();
		await expect(page.getByRole('link', { name: 'Back to results' })).toHaveAttribute('href', results);
		// Too long for the return path: the page carries it by a short id instead.
		const signIn = page.getByRole('link', { name: 'Sign in to save this privately' });
		const returnTo = new URL((await signIn.getAttribute('href'))!, ORIGIN).searchParams.get('returnTo')!;
		expect(returnTo).toMatch(/^\/events\/[0-9a-f-]+\?save=1&ctx=[A-Za-z0-9_-]{16}$/);
		expect(returnTo).not.toContain('results=');

		const email = await createAccount({ label: 'long-context' });
		await page.locator('html[data-sign-in-sheet="ready"]').waitFor();
		await signIn.click();
		await signInHere(page, email);
		await expect(page).toHaveURL(/\?save=1&ctx=/);
		await page.getByRole('button', { name: 'Save privately' }).click();
		await expect(page.getByText('Saved privately — you are not registered.')).toBeVisible();
		await page.getByRole('link', { name: 'Back to results' }).click();
		await expect(page).toHaveURL(`${ORIGIN}${results}`);
		await expect(page.getByLabel('Title or organizer')).toHaveValue(phrase);
		await expect(page.getByLabel('Country')).toHaveValue('PT');
		await expect(page.getByLabel('From', { exact: true })).toHaveValue('2027-07-01');

		// The same without JavaScript: the full sign-in page, then back with the search.
		const plain = await browser.newContext({
			javaScriptEnabled: false,
			ignoreHTTPSErrors: true,
			baseURL: ORIGIN
		});
		const nojs = await plain.newPage();
		await nojs.goto(results);
		await nojs.getByRole('link', { name: new RegExp(base) }).first().click();
		await nojs.getByRole('link', { name: 'Sign in to save this privately' }).click();
		await expect(nojs.getByRole('heading', { level: 1, name: 'Sign in' })).toBeVisible();
		await signInHere(nojs, email);
		await expect(nojs).toHaveURL(/\?save=1&ctx=/);
		await expect(nojs.getByRole('link', { name: 'Back to results' })).toHaveAttribute('href', results);
		await plain.close();
	});

	test('country and dates come first; type, discipline and audience fold away', async ({ page }) => {
		await page.goto('/');
		await page.locator('summary', { hasText: 'Filters' }).click();
		const when = page.getByRole('group', { name: 'When are you available?' });
		await expect(page.getByLabel('Country')).toBeVisible();
		await expect(when.getByLabel('From', { exact: true })).toBeVisible();
		await expect(when.getByLabel('To', { exact: true })).toBeVisible();
		await expect(when.getByText('overlaps these dates')).toBeVisible();
		await expect(page.getByLabel('Type', { exact: true })).toBeHidden();
		await expect(page.getByLabel('Intended for')).toBeHidden();

		// The apply button stays on screen with everything open, without covering the dates.
		await page.locator('summary', { hasText: 'Type, discipline and audience' }).click();
		await page.evaluate(() => window.scrollTo(0, 0));
		const apply = page.getByRole('button', { name: 'Show listings' });
		await expect(apply).toBeInViewport();
		// A field reached by keyboard scrolls clear of it.
		await when.getByLabel('To', { exact: true }).focus();
		const button = (await apply.boundingBox())!;
		const to = (await when.getByLabel('To', { exact: true }).boundingBox())!;
		expect(to.y + to.height <= button.y || to.y >= button.y + button.height).toBe(true);

		// Any of the three in use opens the group by itself.
		await page.goto('/?audience=students');
		await page.locator('summary', { hasText: 'Filters (1)' }).click();
		await expect(page.getByLabel('Intended for')).toHaveValue('students');
	});

	test('the highlight is an upcoming boogie or camp, dated in full and not listed twice', async ({
		page
	}) => {
		// The earliest multi-day boogie on the board: listings elsewhere in the suite start later.
		const listing = await publishListing(`${token()} Soon boogie`, {
			starts_on: daysFromToday(2),
			ends_on: daysFromToday(5)
		});
		await page.goto('/');
		const featured = page.getByRole('region', { name: /^Highlighted: upcoming (boogie|camp)$/ });
		await expect(featured).toBeVisible();
		await expect(featured).toContainText(/Upcoming (boogie|camp)/);
		await expect(featured).not.toContainText(/big/i);
		// A readable range with the year, as on the listing itself.
		await expect(featured.locator('.dates')).toHaveText(/\d{1,2}.* \d{4}$/);
		const title = (await featured.getByRole('link').textContent())!.trim();
		expect(title).toContain('Soon boogie');
		await expect(page.getByRole('heading', { name: 'Other events, by date' })).toBeVisible();
		await expect(
			page.getByRole('list', { name: 'Listings' }).getByRole('link', { name: title })
		).toHaveCount(0);
		// In a search, it is an ordinary result.
		await page.goto(`/?q=${encodeURIComponent(listing.title)}`);
		await expect(page.getByRole('region', { name: /^Highlighted/ })).toHaveCount(0);
		await expect(page.getByRole('link', { name: listing.title })).toHaveCount(1);
	});

	test('dates across a month and across a year read in full', async ({ page }) => {
		const base = token();
		const months = await publishListing(`${base} Month boogie`, {
			starts_on: '2027-06-28',
			ends_on: '2027-07-03'
		});
		const years = await publishListing(`${base} Year boogie`, {
			starts_on: '2027-12-30',
			ends_on: '2028-01-02'
		});
		for (const [listing, text] of [
			[months, '28 June – 3 July 2027'],
			[years, '30 December 2027 – 2 January 2028']
		] as const) {
			await page.goto(`/events/${listing.id}`);
			await expect(page.getByRole('region', { name: listing.title }).getByText(text)).toBeVisible();
			await expect(page.getByText(`${text} (Europe/Lisbon local dates)`)).toBeVisible();
		}
	});
});

test.describe('signing in from the sheet', () => {
	test('empty, malformed and refused sign-ins stay in the sheet', async ({ page }) => {
		const listing = await publishListing(`${token()} Errors boogie`);
		const email = await createAccount({ label: 'sheeterr' });
		const url = `${ORIGIN}/events/${listing.id}`;
		await page.goto(url);
		await page.locator('html[data-sign-in-sheet="ready"]').waitFor();
		const trigger = page.getByRole('link', { name: 'Sign in to save this privately' });
		await trigger.click();
		const sheet = page.getByRole('dialog', { name: 'Sign in' });
		const emailField = sheet.getByLabel('Email', { exact: true });
		const passwordField = sheet.getByLabel('Password', { exact: true });

		// Nothing typed: each field says what it needs; the first one has focus. Field problems
		// are announced through the focused field only, not also by an alert.
		await sheet.getByRole('button', { name: 'Sign in' }).click();
		await expect(page).toHaveURL(url);
		await expect(emailField).toBeFocused();
		await expect(sheet.getByRole('alert')).toHaveCount(0);
		await expect(emailField).toHaveAttribute('aria-invalid', 'true');
		await expect(emailField).toHaveAttribute('aria-describedby', 'sheet-email-error');
		await expect(sheet.locator('#sheet-email-error')).toHaveText('Enter your email address.');
		await expect(passwordField).toHaveAttribute('aria-invalid', 'true');

		// Not an address.
		await emailField.fill('jumper');
		await passwordField.fill(PASSWORD);
		await sheet.getByRole('button', { name: 'Sign in' }).click();
		await expect(sheet.locator('#sheet-email-error')).toHaveText(
			'Enter an email address in the form name@example.com.'
		);
		await expect(emailField).toBeFocused();
		await expect(passwordField).not.toHaveAttribute('aria-invalid', 'true');

		// Refused by the server: the message is an alert in the sheet (announced by its role, so
		// focus is not moved to it), the email stays, the password goes.
		await emailField.fill(email);
		await passwordField.fill('not the right password at all');
		await sheet.getByRole('button', { name: 'Sign in' }).click();
		await expect(sheet.getByRole('alert')).toHaveText('Email or password is incorrect.');
		await expect(sheet.getByRole('alert')).not.toBeFocused();
		await expect(emailField).toHaveAttribute('aria-describedby', 'sheet-error');
		await expect(page).toHaveURL(url);
		await expect(emailField).toHaveValue(email);
		await expect(passwordField).toHaveValue('');

		// Closing returns focus to what opened the sheet.
		await page.keyboard.press('Escape');
		await expect(sheet).toBeHidden();
		await expect(trigger).toBeFocused();
		await expect(page).toHaveURL(url);

		// And it still signs in after a refusal.
		await trigger.click();
		await signInHere(page, email);
		await expect(page).toHaveURL(`${url}?save=1`);
		await expect(page.getByText('You signed in to save this listing')).toBeVisible();
	});

	test('the password can be shown and hidden without changing autocomplete', async ({ page }) => {
		await page.goto('/dz');
		await page.locator('html[data-sign-in-sheet="ready"]').waitFor();
		await page.getByRole('banner').getByRole('link', { name: 'Sign in' }).click();
		const sheet = page.getByRole('dialog', { name: 'Sign in' });
		const field = sheet.getByLabel('Password', { exact: true });
		await field.fill('a passphrase to look at');
		await sheet.getByRole('button', { name: 'Show password' }).click();
		await expect(field).toHaveAttribute('type', 'text');
		await expect(field).toHaveAttribute('autocomplete', 'current-password');
		await sheet.getByRole('button', { name: 'Hide password' }).click();
		await expect(field).toHaveAttribute('type', 'password');
		await expect(field).toHaveValue('a passphrase to look at');
		// Leaving the page hides it again, so the browser never stores it as plain text.
		await sheet.getByRole('button', { name: 'Show password' }).click();
		await expect(field).toHaveAttribute('type', 'text');
		const typeAfterPagehide = await field.evaluate((input: HTMLInputElement) => {
			window.dispatchEvent(new PageTransitionEvent('pagehide', { persisted: false }));
			return input.type; // read synchronously: unloading does not wait for a re-render
		});
		expect(typeAfterPagehide).toBe('password');
	});

	/** Opens the sheet over a listing; returns the sheet and its fields. */
	async function openSheet(page: Page) {
		const listing = await publishListing(`${token()} Sheet net boogie`);
		const url = `${ORIGIN}/events/${listing.id}`;
		await page.goto(url);
		await page.locator('html[data-sign-in-sheet="ready"]').waitFor();
		await page.getByRole('link', { name: 'Sign in to save this privately' }).click();
		const sheet = page.getByRole('dialog', { name: 'Sign in' });
		await expect(sheet).toBeVisible();
		return {
			url,
			sheet,
			email: sheet.getByLabel('Email', { exact: true }),
			password: sheet.getByLabel('Password', { exact: true })
		};
	}

	test('closing the sheet abandons a sign-in still in flight', async ({ page }) => {
		const { url, sheet, email, password } = await openSheet(page);
		let held = false;
		await page.route(/\/sign-in\?/, async (route) => {
			if (route.request().method() !== 'POST') return route.fallback();
			held = true;
			await new Promise((resolve) => setTimeout(resolve, 2_000));
			// The browser has dropped the request by now; continuing may fail, which is fine.
			await route.continue().catch(() => {});
		});
		await email.fill(await createAccount({ label: 'abandon' }));
		await password.fill(PASSWORD);
		await sheet.getByRole('button', { name: 'Sign in' }).click();
		await expect.poll(() => held).toBe(true);
		await page.keyboard.press('Escape');
		await expect(sheet).toBeHidden();
		await page.waitForTimeout(3_000);
		await expect(page).toHaveURL(url);
		await expect(page.getByRole('link', { name: 'Sign in to save this privately' })).toBeVisible();
		await expect(page.getByRole('navigation', { name: 'Primary' })).toHaveCount(0);
	});

	test('offline, nothing is sent and what was typed stays', async ({ page, context }) => {
		const { url, sheet, email, password } = await openSheet(page);
		await email.fill('offline@example.com');
		await password.fill(PASSWORD);
		await context.setOffline(true);
		await sheet.getByRole('button', { name: 'Sign in' }).click();
		await expect(sheet.getByRole('alert')).toHaveText(/You are offline, so nothing was sent/);
		await expect(email).toHaveValue('offline@example.com');
		await expect(password).toHaveValue(PASSWORD);
		await expect(email).not.toHaveAttribute('aria-invalid', 'true');
		await context.setOffline(false);
		await expect(page).toHaveURL(url);
	});

	test('a request that gets no answer keeps the password', async ({ page }) => {
		const { sheet, email, password } = await openSheet(page);
		await page.route(/\/sign-in\?/, (route) =>
			route.request().method() === 'POST' ? route.abort('connectionfailed') : route.fallback()
		);
		await email.fill('noanswer@example.com');
		await password.fill(PASSWORD);
		await sheet.getByRole('button', { name: 'Sign in' }).click();
		await expect(sheet.getByRole('alert')).toHaveText(
			'The service is unavailable right now. Try again later.'
		);
		await expect(password).toHaveValue(PASSWORD);
	});

	test('throttling is explained inside the sheet (answer mocked)', async ({ page }) => {
		// Triggering the real limit would throttle the shared test address for the whole run, so
		// the action's answer is replaced with the shape the server sends for too_many_attempts.
		const { url, sheet, email, password } = await openSheet(page);
		await page.route(/\/sign-in\?/, (route) =>
			route.request().method() === 'POST'
				? route.fulfill({
						status: 200,
						contentType: 'application/json',
						body: JSON.stringify({
							type: 'failure',
							status: 429,
							data: JSON.stringify([{ error: 1, fields: 2 }, 'too_many_attempts', {}])
						})
					})
				: route.fallback()
		);
		await email.fill('throttled@example.com');
		await password.fill(PASSWORD);
		await sheet.getByRole('button', { name: 'Sign in' }).click();
		await expect(sheet.getByRole('alert')).toHaveText(
			'Too many attempts. Wait a while, then try again.'
		);
		await expect(email).toHaveValue('throttled@example.com');
		await expect(email).not.toHaveAttribute('aria-invalid', 'true');
		await expect(page).toHaveURL(url);
	});
});

test('a cross-site enhanced sign-in POST is refused', async ({ playwright }) => {
	const request = await playwright.request.newContext({ ignoreHTTPSErrors: true });
	const response = await request.post(`${ORIGIN}/sign-in?returnTo=%2Fdz`, {
		headers: {
			origin: 'https://evil.example',
			'x-sveltekit-action': 'true',
			accept: 'application/json',
			'content-type': 'application/x-www-form-urlencoded'
		},
		data: 'email=a%40example.com&password=x',
		maxRedirects: 0
	});
	expect(response.status()).toBe(403);
	await request.dispose();
});

test('for a member, the sticky apply button sits above the tab bar', async ({ page }) => {
	await page.goto('/sign-in');
	await signInHere(page, await createAccount({ label: 'sticky' }));
	await expect(page.getByRole('navigation', { name: 'Primary' })).toBeVisible();
	await page.goto('/');
	await page.locator('summary', { hasText: 'Filters' }).click();
	await page.locator('summary', { hasText: 'Type, discipline and audience' }).click();
	await page.evaluate(() => window.scrollTo(0, 0));
	const apply = page.getByRole('button', { name: 'Show listings' });
	await expect(apply).toBeInViewport();
	const button = (await apply.boundingBox())!;
	const nav = (await page.getByRole('navigation', { name: 'Primary' }).boundingBox())!;
	expect(button.y + button.height).toBeLessThanOrEqual(nav.y + 1);
});

test.describe('without JavaScript', () => {
	test('filters, results and Back to results are plain links and GET forms', async ({ browser }) => {
		const base = token();
		const listing = await publishListing(`${base} Nojs boogie`);
		const plain = await browser.newContext({
			javaScriptEnabled: false,
			ignoreHTTPSErrors: true,
			baseURL: ORIGIN
		});
		const page = await plain.newPage();
		await page.goto('/');
		await page.getByLabel('Title or organizer').fill(base);
		await page.locator('summary', { hasText: 'Filters' }).click();
		await page.getByLabel('Country').selectOption('PT');
		await page.getByLabel('From', { exact: true }).fill('2027-07-01');
		await page.getByLabel('To', { exact: true }).fill('2027-07-31');
		await page.locator('summary', { hasText: 'Type, discipline and audience' }).click();
		await page.getByLabel('Type', { exact: true }).selectOption('boogie');
		await page.getByLabel('Discipline').selectOption('freefly');
		await page.getByLabel('Intended for').selectOption('licensed');
		await page.getByRole('button', { name: 'Show listings' }).click();
		// The form's own GET: parameters in the panel's order (country and dates first). Names,
		// values and meaning are as before; only their order in the URL changed.
		await expect(page).toHaveURL(
			`${ORIGIN}/?q=${base}&country=PT&from=2027-07-01&to=2027-07-31&category=boogie&discipline=freefly&audience=licensed`
		);
		await page.getByRole('link', { name: listing.title }).click();
		await page.getByRole('link', { name: 'Back to results' }).click();
		await expect(page).toHaveURL(
			`${ORIGIN}/?q=${base}&category=boogie&country=PT&discipline=freefly&audience=licensed&from=2027-07-01&to=2027-07-31`
		);
		await plain.close();
	});
});
