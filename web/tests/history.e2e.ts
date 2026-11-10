import { expect, test, type Page } from '@playwright/test';
import { PASSWORD, createAccount } from './support/accounts.ts';

// Same production-cookie preview as the account tests.
const ORIGIN = 'https://127.0.0.1:4175';
test.use({ baseURL: ORIGIN, ignoreHTTPSErrors: true });

async function signIn(page: Page, email: string, returnTo = '/history') {
	await page.goto(`/sign-in?returnTo=${encodeURIComponent(returnTo)}`);
	await page.getByLabel('Email', { exact: true }).fill(email);
	await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
	await page.getByRole('button', { name: 'Sign in' }).click();
	await expect(page).toHaveURL(`${ORIGIN}${returnTo}`);
}

/** Log a jump on this date; the first call adds the private place "Farm strip". */
async function logJump(page: Page, on: string, gear?: string) {
	await page.goto('/jumps/new');
	const known = page.getByRole('link', { name: 'Farm strip' });
	if (await known.count()) {
		await known.click();
	} else {
		await page.getByLabel('Place name').fill('Farm strip');
		await page.getByLabel('Country', { exact: true }).selectOption('PT');
		await page.getByRole('button', { name: 'Use this place' }).click();
	}
	await page.getByLabel('Date', { exact: true }).fill(on);
	if (gear) {
		await page.getByText('Add a new component used on this jump').click();
		await page.getByLabel('Component label').fill(gear);
	}
	await page.getByRole('button', { name: 'Save private jump' }).click();
	await expect(page.getByText('Saved privately.')).toBeVisible();
}

async function declare(page: Page, prior: string, on: string) {
	await page.goto('/history/baseline');
	await page.getByLabel('Jumps completed before the date').fill(prior);
	await page.getByLabel('Date', { exact: true }).fill(on);
	await page.getByRole('button', { name: 'Preview' }).click();
}

test.describe('personal history', () => {
	test('a prior jump count adds only entries from its date on', async ({ page }) => {
		await signIn(page, await createAccount({ label: 'history' }));
		await expect(page.getByText('0 jumps recorded here.')).toBeVisible();
		await expect(page.getByText('No jumps recorded yet.')).toBeVisible();

		await logJump(page, '2026-10-10', 'Navigator 260');
		await declare(page, '200', '2026-06-01');
		const preview = page.getByRole('table', { name: 'Preview: nothing is saved yet' });
		await expect(preview).toContainText('1 jump recorded (no prior count)');
		await expect(preview).toContainText('201 jumps');
		await page.getByRole('button', { name: 'Save prior jump count' }).click();

		await expect(page).toHaveURL(`${ORIGIN}/history?saved=1`);
		await expect(page.getByText('Reported total: 201 jumps')).toBeVisible();

		// A detailed entry before the date is already within the declared count.
		await logJump(page, '2026-05-01');
		await page.goto('/history');
		await expect(page.getByText('Reported total: 201 jumps')).toBeVisible();
		await expect(page.getByText('already within your declared count')).toBeVisible();
		// The Records hub shows the same total and the latest jump date.
		await page.goto('/records');
		const summary = page.getByRole('region', { name: 'Summary' });
		await expect(summary).toContainText('201 jumps');
		await expect(summary).toContainText('(200 declared + 1 recorded)');
		await expect(summary).toContainText('Last jump 10 October 2026');
		await page.goto('/history');
		await expect(
			page.getByRole('table', { name: 'Recorded jumps in the last 12 months' })
		).toContainText('Oct 2026');
		// Gear use comes only from the jump that recorded it.
		const gear = page.getByRole('list', { name: 'Equipment used' });
		await expect(gear).toContainText('Navigator 260');
		await expect(gear).toContainText('1 jump · last 10 October 2026');

		await page.goto('/history/baseline');
		await expect(page.getByRole('list', { name: 'Changes' })).toContainText(
			'Declared 200 jumps before 1 June 2026'
		);
	});

	test('more entries before the date than declared are flagged, not rejected', async ({ page }) => {
		await signIn(page, await createAccount({ label: 'flagged' }));
		await declare(page, '0', '2026-06-01');
		await page.getByRole('button', { name: 'Save prior jump count' }).click();
		await expect(page).toHaveURL(`${ORIGIN}/history?saved=1`);
		await logJump(page, '2026-01-15');
		await page.goto('/history');
		await expect(page.getByRole('alert')).toContainText('You recorded 1 jump before 1 June 2026');
		await expect(page.getByText('Reported total')).toHaveCount(0);

		// The preview shows the correction's effect before saving.
		await declare(page, '30', '2026-06-01');
		await expect(page.getByRole('table', { name: 'Preview: nothing is saved yet' })).toContainText(
			'30 jumps'
		);
		await page.getByRole('button', { name: 'Save prior jump count' }).click();
		await expect(page.getByText('Reported total: 30 jumps')).toBeVisible();
	});

	test('a preview from an older tab cannot overwrite a newer count', async ({ page, context }) => {
		await signIn(page, await createAccount({ label: 'btabs' }));
		await declare(page, '10', '2026-01-01');
		await page.getByRole('button', { name: 'Save prior jump count' }).click();
		await expect(page.getByText('Reported total: 10 jumps')).toBeVisible();

		const older = await context.newPage();
		await declare(older, '11', '2026-01-01');
		await declare(page, '12', '2026-01-01');
		await page.getByRole('button', { name: 'Save prior jump count' }).click();
		await expect(page.getByText('Reported total: 12 jumps')).toBeVisible();

		await older.getByRole('button', { name: 'Save prior jump count' }).click();
		await expect(older.getByRole('alert')).toContainText('changed since you opened this page');
		// Sending the stale preview again still conflicts; it never overwrites.
		await older.getByRole('button', { name: 'Save prior jump count' }).click();
		await expect(older.getByRole('alert')).toContainText('changed since you opened this page');
		await page.reload();
		await expect(page.getByText('Reported total: 12 jumps')).toBeVisible();

		// Removing keeps recorded jumps and returns to recorded-only totals.
		await page.goto('/history/baseline');
		await page.getByLabel('Remove my prior jump count').check();
		await page.getByRole('button', { name: 'Remove', exact: true }).click();
		await expect(page).toHaveURL(`${ORIGIN}/history?removed=1`);
		await expect(page.getByText('0 jumps recorded here.')).toBeVisible();
	});
});
