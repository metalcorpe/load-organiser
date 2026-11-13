import { expect, test, type Page } from '@playwright/test';
import { randomBytes } from 'node:crypto';
import { PASSWORD, apiCall, createAccount, reviewerSession } from './support/accounts.ts';
import { openJumpSections } from './support/jump-form.ts';

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
	await page.getByRole('button', { name: 'Save private jump' }).first().click();
	await expect(page.getByText('Saved privately.')).toBeVisible();
	return page.url().split('/jumps/')[1].split('?')[0];
}

test.describe('private logbook', () => {
	test('log the next jump of the day in one step, with or without jump numbers', async ({ page }) => {
		await signIn(page, await createAccount({ label: 'nextjump' }));
		await startAtNewPlace(page, 'Next strip');
		await page.getByLabel('Date', { exact: true }).fill('2026-10-12');
		await page.getByLabel('Type', { exact: true }).selectOption('freefly');
		await openJumpSections(page);
		await page.getByLabel('Your jump number').fill('120');
		await page.getByLabel('Exit altitude').fill('4000');
		await page.getByLabel('Metres').check();
		await page.getByLabel('Notes (optional, private)').fill('Only about the first load.');
		await page.getByRole('button', { name: 'Save private jump' }).first().click();
		await expect(page.getByText('Saved privately.')).toBeVisible();

		// Same place, day, type and altitude; the next number; nothing jump-specific.
		await page.getByRole('link', { name: 'Log the next jump' }).click();
		await expect(page.getByText('Next strip', { exact: true })).toBeVisible();
		await expect(page.getByLabel('Date', { exact: true })).toHaveValue('2026-10-12');
		await expect(page.getByLabel('Type', { exact: true })).toHaveValue('freefly');
		await openJumpSections(page);
		await expect(page.getByLabel('Your jump number')).toHaveValue('121');
		await expect(page.getByLabel('Exit altitude')).toHaveValue('4000');
		await expect(page.getByLabel('Notes (optional, private)')).toHaveValue('');
		await page.getByRole('button', { name: 'Save private jump' }).first().click();
		await expect(page.getByText('Saved privately.')).toBeVisible();
		await expect(page.getByText('#121', { exact: true })).toBeVisible();

		// Without numbers the next load matches the duplicate check exactly; choosing
		// "Log the next jump" already says it is another jump.
		await page.goto('/jumps/new');
		await page.getByText('Not listed? Add a private place').click();
		await page.getByLabel('Place name').fill('Plain strip');
		await page.getByLabel('Country', { exact: true }).selectOption('PT');
		await page.getByRole('button', { name: 'Use this place' }).click();
		await expect(page.getByText('Plain strip', { exact: true })).toBeVisible();
		await page.getByLabel('Date', { exact: true }).fill('2026-10-13');
		await page.getByLabel('Type', { exact: true }).selectOption('belly');
		await page.getByRole('button', { name: 'Save private jump' }).first().click();
		await expect(page.getByText('Saved privately.')).toBeVisible();
		await page.getByRole('link', { name: 'Log the next jump' }).click();
		await page.getByRole('button', { name: 'Save private jump' }).first().click();
		await expect(page.getByText('Saved privately.')).toBeVisible();
		await page.goto('/jumps');
		await expect(page.getByText('4 jumps recorded here.', { exact: false })).toBeVisible();
	});

	test('quick entry: save after the essentials; folded sections still send and reopen', async ({
		page
	}) => {
		await signIn(page, await createAccount({ label: 'quick' }));
		await startAtNewPlace(page);
		const sections = page.locator('form details.section');
		await expect(sections).toHaveCount(3);
		for (const section of await sections.all()) await expect(section).not.toHaveAttribute('open');
		// A refusal about a field in a folded section opens that section and focuses the field;
		// what was typed elsewhere, folded or not, is kept.
		await openJumpSections(page);
		await page.getByLabel('Notes (optional, private)').fill('Typed, then folded.');
		await page.getByLabel('Exit weight on this jump in kg (optional)').fill('999');
		const open = page.locator('form details.section[open] > summary');
		while ((await open.count()) > 0) await open.first().click();
		await page.getByLabel('Date', { exact: true }).fill('2026-10-10');
		await page.getByRole('button', { name: 'Save private jump' }).first().click();
		const weight = page.getByLabel('Exit weight on this jump in kg (optional)');
		await expect(weight).toBeFocused();
		await expect(weight).toHaveAttribute('aria-invalid', 'true');
		await expect(weight).toHaveValue('999');
		await expect(sections.filter({ hasText: 'Notes and links' })).not.toHaveAttribute('open');
		await expect(sections.filter({ hasText: 'Notes and links' })).toContainText('Filled in: notes');

		// The early button sends the folded notes too.
		await weight.fill('');
		await page.getByRole('button', { name: 'Save private jump' }).first().click();
		await expect(page.getByText('Saved privately.')).toBeVisible();
		// Editing: the section with a value is open, the empty ones folded.
		await expect(page.getByLabel('Notes (optional, private)')).toHaveValue('Typed, then folded.');
		await expect(sections.filter({ hasText: 'Notes and links' })).toHaveAttribute('open');
		await expect(sections.filter({ hasText: 'Equipment and exit weight' })).not.toHaveAttribute(
			'open'
		);
	});

	test('an empty logbook leads with logging and import; filters and a prior count are told apart', async ({
		page
	}) => {
		await signIn(page, await createAccount({ label: 'empty' }));
		const start = page.getByRole('region', { name: 'Start your logbook' });
		await expect(start).toContainText('No jumps yet.');
		await expect(start.getByRole('link', { name: 'Log your first jump' })).toHaveAttribute(
			'href',
			'/jumps/new'
		);
		await expect(start.getByRole('link', { name: 'Import existing logbook' })).toHaveAttribute(
			'href',
			'/records/import'
		);
		// Nothing to search yet, and no currency box to explain.
		await expect(page.getByRole('search')).toHaveCount(0);
		await expect(page.getByRole('region', { name: 'Jump currency' })).toHaveCount(0);

		// A search with no result keeps the controls and a way out.
		await page.goto('/jumps?q=nothing-here');
		await expect(page.getByRole('search')).toBeVisible();
		await expect(page.getByLabel('Place, aircraft or notes')).toHaveValue('nothing-here');
		const none = page.getByRole('region', { name: 'No jumps match' });
		await expect(none.getByRole('link', { name: 'Clear filters' })).toHaveAttribute('href', '/jumps');
		await expect(page.getByRole('region', { name: 'Start your logbook' })).toHaveCount(0);

		// A declared prior count with no entries is acknowledged; logging and import still lead.
		await page.goto('/history/baseline');
		await page.getByLabel('Jumps completed before the date').fill('150');
		await page.getByLabel('Date', { exact: true }).fill('2026-01-01');
		await page.getByRole('button', { name: 'Preview' }).click();
		await page.getByRole('button', { name: 'Save prior jump count' }).click();
		await page.goto('/jumps');
		await expect(start).toContainText('You declared 150 prior jumps before 1 January 2026');
		await expect(start.getByRole('link', { name: 'Log your first jump' })).toBeVisible();
		await expect(start.getByRole('link', { name: 'Import existing logbook' })).toBeVisible();
	});

	test('an offline save sends nothing and keeps what was typed', async ({ page, context }) => {
		await signIn(page, await createAccount({ label: 'offline' }));
		await startAtNewPlace(page);
		await page.getByLabel('Date', { exact: true }).fill('2026-10-11');
		await page.getByLabel('Type', { exact: true }).selectOption('belly');
		await openJumpSections(page);
		await page.getByLabel('Notes (optional, private)').fill('Typed with no signal.');
		const form = page.url();

		await context.setOffline(true);
		await page.getByRole('button', { name: 'Save private jump' }).first().click();
		await expect(page.getByRole('alert')).toContainText('You are offline, so nothing was sent.');
		expect(page.url()).toBe(form);
		await expect(page.getByLabel('Notes (optional, private)')).toHaveValue('Typed with no signal.');
		// A second try while still offline shows the same single notice.
		await page.getByRole('button', { name: 'Save private jump' }).first().click();
		await expect(page.locator('[data-offline-notice]')).toHaveCount(1);

		await context.setOffline(false);
		await expect(page.locator('[data-offline-notice]')).toHaveCount(0);
		await page.getByRole('button', { name: 'Save private jump' }).first().click();
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
		await openJumpSections(page);
		await page.getByLabel('Your jump number').fill('120');
		await page.getByLabel('Exit altitude').fill('4000');
		await page.getByLabel('Metres').check();
		await page.getByText('Add a new component used on this jump').click();
		await page.getByLabel('Component label').fill('Rented Navigator');
		await page.getByLabel('Notes (optional, private)').fill('First jump here.');
		await page.getByRole('button', { name: 'Save private jump' }).first().click();

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
		await page.getByRole('button', { name: 'Save private jump' }).first().click();
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
		await expect(page.getByRole('button', { name: 'Save private jump' }).first()).toBeVisible();
		await page.goto('/jumps/new');
		await expect(page.getByLabel('Place name')).toBeHidden();
		// The Logbook home continues from the newest jump as its one-tap main action:
		// same place and type, but the date is the jumper's own today, not the old day.
		await page.goto('/jumps');
		await page.getByRole('link', { name: `Log the next jump at ${name}` }).click();
		await expect(page.getByText(name, { exact: true })).toBeVisible();
		await expect(page.getByLabel('Type', { exact: true })).toHaveValue('unspecified');
		const today = await page.evaluate(() => {
			const d = new Date();
			return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
		});
		await expect(page.getByLabel('Date', { exact: true })).toHaveValue(today);
		await expect(page.getByRole('button', { name: 'Save private jump' }).first()).toBeVisible();
	});

	test('a likely duplicate warns, and a distinct jump still saves', async ({ page }) => {
		await signIn(page, await createAccount({ label: 'dupes' }));
		const first = await logJump(page);
		await page.goto('/jumps/new');
		await page.getByRole('link', { name: 'Farm strip' }).click();
		await page.getByLabel('Date', { exact: true }).fill('2026-10-10');
		await page.getByLabel('Type', { exact: true }).selectOption('freefly');
		await page.getByRole('button', { name: 'Save private jump' }).first().click();
		await expect(page.getByText('This looks like a jump you already logged')).toBeVisible();
		await expect(page.getByRole('link', { name: 'View the earlier entry' })).toHaveAttribute(
			'href',
			`/jumps/${first}`
		);
		await page.getByRole('button', { name: 'Save as a distinct jump' }).first().click();
		await expect(page.getByText('Saved privately.')).toBeVisible();
		await page.goto('/jumps');
		await expect(page.getByText('2 jumps recorded here.', { exact: false })).toBeVisible();
	});

	test('saved notes are in the page without JavaScript', async ({ page, browser }) => {
		// The server renders the saved text into the field, so a form posted before (or without)
		// hydration keeps it instead of sending an empty field.
		await signIn(page, await createAccount({ label: 'nojs' }));
		const id = await logJump(page);
		await openJumpSections(page);
		await page.getByLabel('Notes (optional, private)').fill('kept without js');
		await page.getByRole('button', { name: 'Save changes' }).first().click();
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
		await openJumpSections(page);
		await page.getByLabel('Notes (optional, private)').fill('secret detail');
		await page.getByRole('button', { name: 'Save changes' }).first().click();
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
		await page.getByRole('button', { name: 'Save changes' }).first().click();
		await expect(page.getByText('Saved privately.')).toBeVisible();
		await second.getByLabel('Type', { exact: true }).selectOption('canopy');
		await second.getByRole('button', { name: 'Save changes' }).first().click();
		await expect(second.getByRole('alert')).toContainText('changed since you opened it');
		// Sending the re-shown stale form again still conflicts; it never overwrites.
		await expect(second.getByLabel('Type', { exact: true })).toHaveValue('canopy');
		await second.getByRole('button', { name: 'Save changes' }).first().click();
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
