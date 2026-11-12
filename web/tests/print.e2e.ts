import { expect, test, type Page } from '@playwright/test';
import { PASSWORD, apiCall, apiSession, createAccount } from './support/accounts.ts';

// Same production-cookie preview as the account tests.
const ORIGIN = 'https://127.0.0.1:4175';
test.use({ baseURL: ORIGIN, ignoreHTTPSErrors: true });

async function signIn(page: Page, email: string, returnTo: string) {
	await page.goto(`/sign-in?returnTo=${encodeURIComponent(returnTo)}`);
	await page.getByLabel('Email', { exact: true }).fill(email);
	await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
	await page.getByRole('button', { name: 'Sign in' }).click();
	await expect(page).toHaveURL(`${ORIGIN}${returnTo}`);
}

async function ok(response: Promise<Response>): Promise<Record<string, unknown>> {
	const r = await response;
	if (r.status >= 300) throw new Error(`setup failed: ${r.status} ${await r.text()}`);
	return (await r.json()) as Record<string, unknown>;
}

/** 14 jumps in October 2026 (two sheets of 12 and 2), 50 s freefall each, with a note. */
async function seed(email: string) {
	const bearer = await apiSession(email);
	const place = await ok(
		apiCall('POST', '/places', { bearer, body: { name: 'Farm strip', country: 'PT' } })
	);
	for (let n = 1; n <= 14; n++) {
		await ok(
			apiCall('POST', '/jumps', {
				bearer,
				body: {
					client_key: crypto.randomUUID(),
					jumped_on: `2026-10-${String(n).padStart(2, '0')}`,
					jump_type: 'belly',
					place_id: place.id,
					jump_number: n,
					exit_altitude: 4000,
					altitude_unit: 'm',
					freefall_seconds: 50,
					notes: `Private note for jump ${n}`
				}
			})
		);
	}
}

test.describe('printable logbook', () => {
	test('renders the jumps in sheets with page and running totals', async ({ page }) => {
		const email = await createAccount({ label: 'print' });
		await seed(email);
		await signIn(page, email, '/records');
		await page.getByRole('link', { name: /Printable logbook/ }).click();
		await expect(page).toHaveURL(`${ORIGIN}/records/print`);
		await expect(page.getByRole('heading', { name: 'Printable logbook', level: 1 })).toBeVisible();
		await expect(page.getByRole('button', { name: 'Print or save as PDF' })).toBeVisible();

		const first = page.getByRole('table', { name: 'Sheet 1 of 2' });
		await expect(first.getByRole('columnheader', { name: 'Signature' })).toBeVisible();
		await expect(first.getByRole('columnheader', { name: 'Aircraft' })).toBeVisible();
		await expect(first.getByRole('columnheader', { name: 'Notes' })).toHaveCount(0);
		await expect(first.locator('tbody tr')).toHaveCount(12);
		await expect(first.locator('tbody tr').first()).toContainText('1 Oct 2026');
		await expect(first.locator('tbody tr').first()).toContainText('Farm strip');
		await expect(first.locator('tbody tr').first()).toContainText('4,000 m');
		await expect(first.getByRole('row', { name: /This sheet/ })).toContainText('12 jumps · freefall 10 min 0 s');
		await expect(first.getByRole('row', { name: /Total to date/ })).toContainText('12 jumps');

		const second = page.getByRole('table', { name: 'Sheet 2 of 2' });
		await expect(second.locator('tbody tr')).toHaveCount(2);
		await expect(second.getByRole('row', { name: /Brought forward/ })).toContainText('12 jumps · freefall 10 min 0 s');
		await expect(second.getByRole('row', { name: /Total to date/ })).toContainText('14 jumps · freefall 11 min 40 s');
		await expect(page.getByText('Private note for jump')).toHaveCount(0);
	});

	test('a date range with notes carries earlier jumps forward', async ({ page }) => {
		const email = await createAccount({ label: 'printrange' });
		await seed(email);
		await signIn(page, email, '/records/print');
		await page.getByLabel('From', { exact: true }).fill('2026-10-11');
		await page.getByLabel('Until', { exact: true }).fill('2026-10-12');
		await page.getByLabel('Include notes (shortened)').check();
		await page.getByRole('button', { name: 'Show' }).click();
		await expect(page).toHaveURL(/from=2026-10-11&until=2026-10-12&notes=yes/);

		const sheet = page.getByRole('table', { name: 'Sheet 1 of 1' });
		await expect(sheet.locator('tbody tr')).toHaveCount(2);
		await expect(sheet).toContainText('Private note for jump 11');
		await expect(sheet.getByRole('row', { name: /Brought forward/ })).toContainText('10 jumps');
		await expect(sheet.getByRole('row', { name: /Total to date/ })).toContainText('12 jumps');
		await expect(page.getByText('Includes 10 jumps recorded before this range.')).toBeVisible();
	});

	test('dates in the wrong order are explained', async ({ page }) => {
		await signIn(page, await createAccount({ label: 'printbad' }), '/records/print?from=2026-10-12&until=2026-10-01');
		await expect(page.getByRole('alert')).toContainText('The start date must be on or before the end date.');
	});
});
