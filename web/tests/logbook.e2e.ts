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
	test('log a jump at an unlisted place with a new component, without gear setup', async ({
		page
	}) => {
		await signIn(page, await createAccount({ label: 'logbook' }));
		await expect(page.getByText('No jumps yet.')).toBeVisible();
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
