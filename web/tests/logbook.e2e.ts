import { expect, test, type Page } from '@playwright/test';
import { randomBytes } from 'node:crypto';
import { PASSWORD, apiCall, createAccount, reviewerSession } from './support/accounts.ts';

// Same production-cookie preview as the account tests.
const ORIGIN = 'https://127.0.0.1:4175';
test.use({ baseURL: ORIGIN, ignoreHTTPSErrors: true });

async function signIn(page: Page, email: string, returnTo = '/jumps') {
	await page.goto(`/sign-in?returnTo=${encodeURIComponent(returnTo)}`);
	await page.getByLabel('Email', { exact: true }).fill(email);
	await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
	await page.getByRole('button', { name: 'Sign in' }).click();
	await expect(page).toHaveURL(`${ORIGIN}${returnTo}`);
}

/** Start a jump at a new private place; returns with the jump form open. */
async function startAtNewPlace(page: Page, name = 'Farm strip') {
	await page.goto('/jumps/new');
	await expect(page.getByRole('heading', { name: 'Where did you jump?' })).toBeVisible();
	await page.getByLabel('Place name').fill(name);
	await page.getByLabel('Country', { exact: true }).selectOption('PT');
	await page.getByRole('button', { name: 'Use this place' }).click();
	await expect(page.getByText(name, { exact: true })).toBeVisible();
}

async function logJump(page: Page): Promise<string> {
	await startAtNewPlace(page);
	await page.getByLabel('Date', { exact: true }).fill('2026-10-10');
	await page.getByLabel('Type', { exact: true }).selectOption('freefly');
	await page.getByRole('button', { name: 'Save private jump' }).click();
	await expect(page.getByText('Saved privately.')).toBeVisible();
	return page.url().split('/jumps/')[1].split('?')[0];
}

test.describe('private logbook', () => {
	test('an offline save sends nothing and keeps what was typed', async ({ page, context }) => {
		await signIn(page, await createAccount({ label: 'offline' }));
		await startAtNewPlace(page);
		await page.getByLabel('Date', { exact: true }).fill('2026-10-11');
		await page.getByLabel('Type', { exact: true }).selectOption('belly');
		await page.getByLabel('Notes (optional, private)').fill('Typed with no signal.');
		const form = page.url();

		await context.setOffline(true);
		await page.getByRole('button', { name: 'Save private jump' }).click();
		await expect(page.getByRole('alert')).toContainText('You are offline, so nothing was sent.');
		expect(page.url()).toBe(form);
		await expect(page.getByLabel('Notes (optional, private)')).toHaveValue('Typed with no signal.');
		// A second try while still offline shows the same single notice.
		await page.getByRole('button', { name: 'Save private jump' }).click();
		await expect(page.locator('[data-offline-notice]')).toHaveCount(1);

		await context.setOffline(false);
		await expect(page.locator('[data-offline-notice]')).toHaveCount(0);
		await page.getByRole('button', { name: 'Save private jump' }).click();
		await expect(page.getByText('Saved privately.')).toBeVisible();
		await expect(page.getByLabel('Notes (optional, private)')).toHaveValue('Typed with no signal.');
	});

	test('an unconfirmed account can ask for a new link from any private page', async ({ page }) => {
		const email = await createAccount({ label: 'unconfirmed', verified: false });
		await signIn(page, email);
		const banner = page.getByRole('region', { name: 'Confirm your email' });
		await expect(banner).toContainText(`Use the link we sent to ${email}.`);
		// A long address never squeezes the Preview badge onto two lines.
		const badge = page.locator('header .badge');
		if (await badge.isVisible()) expect((await badge.boundingBox())!.height).toBeLessThan(30);
		await expect(page.locator('header .avatar')).toHaveText('U');

		await banner.getByRole('button', { name: 'Send a new link' }).click();
		await expect(page.getByText('We sent a new confirmation link.')).toBeVisible();
		// Profile has its own resend button, so the banner is not repeated there.
		await expect(page.getByRole('region', { name: 'Confirm your email' })).toHaveCount(0);
	});

	test('log a jump at an unlisted place with a new component, without gear setup', async ({
		page
	}) => {
		await signIn(page, await createAccount({ label: 'logbook' }));
		await expect(page.getByText('No jumps yet.')).toBeVisible();
		// Members get the four tabs and a privacy label on their records.
		const tabs = page.getByRole('navigation', { name: 'Primary' });
		await expect(tabs.getByRole('link')).toHaveText(['Explore', 'Logbook', 'Friends', 'Me']);
		await expect(tabs.getByRole('link', { name: 'Logbook' })).toHaveAttribute('aria-current', 'page');
		await expect(page.getByText('Private logbook — only you can see your jumps')).toBeVisible();
		await startAtNewPlace(page);
		// The date defaults to the jumper's local day and stays editable.
		await expect(page.getByLabel('Date', { exact: true })).not.toHaveValue('');
		await page.getByLabel('Date', { exact: true }).fill('2026-10-10');
		await page.getByLabel('Type', { exact: true }).selectOption('belly');
		await page.getByText('Number, time and altitudes (optional)').click();
		await page.getByLabel('Your jump number').fill('120');
		await page.getByLabel('Exit altitude').fill('4000');
		await page.getByLabel('Metres').check();
		await page.getByText('Add a new component used on this jump').click();
		await page.getByLabel('Component label').fill('Rented Navigator');
		await page.getByLabel('Notes (optional, private)').fill('First jump here.');
		await page.getByRole('button', { name: 'Save private jump' }).click();

		await expect(page.getByText('Saved privately.')).toBeVisible();
		await expect(page.getByText('entered by you, not verified')).toBeVisible();
		await expect(page.getByText('exit 4,000 m (reference not stated)')).toBeVisible();
		await expect(page.getByRole('link', { name: 'Rented Navigator' })).toBeVisible();

		await page.goto('/jumps');
		await expect(page.getByText('1 jump recorded here.', { exact: false })).toBeVisible();
		const item = page.getByRole('list', { name: 'Jumps' }).getByRole('listitem');
		await expect(item).toContainText('10 October 2026 · #120');
		await expect(item).toContainText('Farm strip (private place)');
		await expect(item).not.toContainText('First jump here.');

		// The new component is in private gear and, once used, cannot be deleted.
		await page.goto('/gear');
		await page.getByRole('link', { name: 'Rented Navigator' }).click();
		await page.getByLabel('Delete this item, its service entries and history').check();
		await page.getByRole('button', { name: 'Delete permanently' }).click();
		await expect(page.getByRole('alert')).toContainText('A jump records it as used');
	});

	test('log a jump at a listed dropzone found by search', async ({ page }) => {
		const name = `Lb${randomBytes(5).toString('hex')} Skydive`;
		const created = await apiCall('POST', '/directory/venues', {
			bearer: await reviewerSession(),
			body: { name, country: 'ES', source_url: 'https://example.org/dz', checked_on: '2026-11-01' }
		});
		expect(created.status).toBe(201);
		await signIn(page, await createAccount({ label: 'listed' }));
		await page.goto('/jumps/new');
		await page.getByLabel('Search listed dropzones').fill(name.slice(0, 12));
		await page.getByRole('button', { name: 'Search' }).click();
		await page.getByRole('link', { name }).click();
		await expect(page.getByText(name, { exact: true })).toBeVisible();
		await page.getByLabel('Date', { exact: true }).fill('2026-09-01');
		await page.getByRole('button', { name: 'Save private jump' }).click();
		await expect(page.getByText('Saved privately.')).toBeVisible();
		await page.goto('/jumps');
		await expect(page.getByRole('list', { name: 'Jumps' })).toContainText(
			`Not specified · ${name}`
		);
		// The next jump starts from it: recent places are one tap, and the add-place
		// form is folded away for someone who already has a place.
		await page.goto('/jumps/new');
		await page.getByRole('list', { name: 'Recent places' }).getByRole('link', { name }).click();
		await expect(page.getByText(name, { exact: true })).toBeVisible();
		await expect(page.getByRole('button', { name: 'Save private jump' })).toBeVisible();
		await page.goto('/jumps/new');
		await expect(page.getByLabel('Place name')).toBeHidden();
		// The Logbook home offers the same place as its one-tap main action.
		await page.goto('/jumps');
		await page.getByRole('link', { name: `Log a jump at ${name}` }).click();
		await expect(page.getByText(name, { exact: true })).toBeVisible();
		await expect(page.getByRole('button', { name: 'Save private jump' })).toBeVisible();
	});

	test('a likely duplicate warns, and a distinct jump still saves', async ({ page }) => {
		await signIn(page, await createAccount({ label: 'dupes' }));
		const first = await logJump(page);
		await page.goto('/jumps/new');
		await page.getByRole('link', { name: 'Farm strip' }).click();
		await page.getByLabel('Date', { exact: true }).fill('2026-10-10');
		await page.getByLabel('Type', { exact: true }).selectOption('freefly');
		await page.getByRole('button', { name: 'Save private jump' }).click();
		await expect(page.getByText('This looks like a jump you already logged')).toBeVisible();
		await expect(page.getByRole('link', { name: 'View the earlier entry' })).toHaveAttribute(
			'href',
			`/jumps/${first}`
		);
		await page.getByRole('button', { name: 'Save as a distinct jump' }).click();
		await expect(page.getByText('Saved privately.')).toBeVisible();
		await page.goto('/jumps');
		await expect(page.getByText('2 jumps recorded here.', { exact: false })).toBeVisible();
	});

	test('saved notes are in the page without JavaScript', async ({ page, browser }) => {
		// The server renders the saved text into the field, so a form posted before (or without)
		// hydration keeps it instead of sending an empty field.
		await signIn(page, await createAccount({ label: 'nojs' }));
		const id = await logJump(page);
		await page.getByLabel('Notes (optional, private)').fill('kept without js');
		await page.getByRole('button', { name: 'Save changes' }).click();
		await expect(page.getByRole('list', { name: 'History' })).toContainText('Notes: changed');
		const nojs = await browser.newContext({
			storageState: await page.context().storageState(),
			javaScriptEnabled: false,
			ignoreHTTPSErrors: true
		});
		const plain = await nojs.newPage();
		await plain.goto(`${ORIGIN}/jumps/${id}`);
		await expect(plain.getByLabel('Notes (optional, private)')).toHaveValue('kept without js');
		await nojs.close();
	});

	test('edit keeps a correction history, then delete', async ({ page }) => {
		await signIn(page, await createAccount({ label: 'edits' }));
		const id = await logJump(page);
		await page.getByLabel('Type', { exact: true }).selectOption('wingsuit');
		await page.getByLabel('Notes (optional, private)').fill('secret detail');
		await page.getByRole('button', { name: 'Save changes' }).click();
		await expect(page.getByText('Saved privately.')).toBeVisible();
		const history = page.getByRole('list', { name: 'History' });
		await expect(history).toContainText('Type: freefly → wingsuit');
		await expect(history).toContainText('Notes: changed');
		await expect(history).not.toContainText('secret detail');

		await page.getByLabel('Delete this jump and its history').check();
		await page.getByRole('button', { name: 'Delete jump' }).click();
		await expect(page).toHaveURL(`${ORIGIN}/jumps?deleted=1`);
		await expect(page.getByText('No jumps yet.')).toBeVisible();
		expect((await page.goto(`/jumps/${id}`))?.status()).toBe(404);
	});

	test('an edit from an older tab is refused, and jumps are owner-only', async ({
		page,
		context,
		browser
	}) => {
		await signIn(page, await createAccount({ label: 'jtabs' }));
		const id = await logJump(page);
		const second = await context.newPage();
		await second.goto(`/jumps/${id}`);
		await page.getByLabel('Type', { exact: true }).selectOption('angle');
		await page.getByRole('button', { name: 'Save changes' }).click();
		await expect(page.getByText('Saved privately.')).toBeVisible();
		await second.getByLabel('Type', { exact: true }).selectOption('canopy');
		await second.getByRole('button', { name: 'Save changes' }).click();
		await expect(second.getByRole('alert')).toContainText('changed since you opened it');
		// Sending the re-shown stale form again still conflicts; it never overwrites.
		await expect(second.getByLabel('Type', { exact: true })).toHaveValue('canopy');
		await second.getByRole('button', { name: 'Save changes' }).click();
		await expect(second.getByRole('alert')).toContainText('changed since you opened it');
		await page.reload();
		await expect(page.getByLabel('Type', { exact: true })).toHaveValue('angle');

		const other = await browser.newContext({ baseURL: ORIGIN, ignoreHTTPSErrors: true });
		const otherPage = await other.newPage();
		await signIn(otherPage, await createAccount({ label: 'jother' }));
		expect((await otherPage.goto(`/jumps/${id}`))?.status()).toBe(404);
		await otherPage.goto('/jumps');
		await expect(otherPage.getByText('No jumps yet.')).toBeVisible();
		await other.close();
	});
});
