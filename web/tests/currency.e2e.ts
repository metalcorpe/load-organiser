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

const pad = (n: number) => String(n).padStart(2, '0');
/** The local calendar day `offset` days from today, as YYYY-MM-DD (browser and test share a clock). */
function day(offset: number): string {
	const d = new Date();
	d.setDate(d.getDate() + offset);
	return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}
const long = (iso: string) =>
	new Intl.DateTimeFormat('en-GB', { dateStyle: 'long', timeZone: 'UTC' }).format(
		new Date(`${iso}T00:00:00Z`)
	);

async function logJump(email: string, on: string) {
	const bearer = await apiSession(email);
	const place = await apiCall('POST', '/places', { bearer, body: { name: 'Farm strip', country: 'PT' } });
	const { id } = (await place.json()) as { id: string };
	const made = await apiCall('POST', '/jumps', {
		bearer,
		body: { client_key: crypto.randomUUID(), jumped_on: on, jump_type: 'belly', place_id: id }
	});
	expect(made.status).toBe(201);
}

async function setLicence(page: Page, label: string) {
	await page.goto('/profile');
	await page.getByRole('combobox', { name: 'Licence' }).selectOption({ label });
	await page.getByRole('button', { name: 'Save licence' }).click();
	await expect(page.getByText('Licence saved.')).toBeVisible();
}

test.describe('jump currency', () => {
	test('without a licence the logbook asks for one; with one it shows the guidance', async ({ page }) => {
		const email = await createAccount({ label: 'currency' });
		await signIn(page, email, '/jumps');
		// An empty logbook leads with logging and importing; currency waits for a first jump.
		await expect(page.getByRole('link', { name: 'Log your first jump' })).toBeVisible();
		await expect(page.getByRole('region', { name: 'Jump currency' })).toHaveCount(0);
		await page.goto('/history');
		const box = page.getByRole('region', { name: 'Jump currency' });
		await expect(box).toContainText('Set your licence to see your jump currency.');
		await expect(box).toContainText('not a verified status (USPA SIM 5-2)');

		await setLicence(page, 'B licence');
		await page.goto('/history');
		await expect(page.getByRole('region', { name: 'Jump currency' })).toContainText(
			'No jumps recorded yet, so there is no currency to show.'
		);
		// The details come with a computed status, not before.
		await expect(page.getByRole('region', { name: 'Jump currency' })).not.toContainText(
			'Every jump type counts'
		);

		await logJump(email, day(-10));
		await page.goto('/jumps');
		await expect(page.getByTestId('currency-status')).toHaveText(
			`Current until ${long(day(80))} (USPA guidance for a B licence: 90 days).`
		);
		await page.goto('/history');
		await expect(page.getByTestId('currency-status')).toContainText(`Current until ${long(day(80))}`);
		await expect(page.getByRole('region', { name: 'Jump currency' })).toContainText(
			'the logbook does not record whether you were the instructor or the passenger'
		);
	});

	test('a jump longer ago than the licence allows is not current', async ({ page }) => {
		const email = await createAccount({ label: 'lapsed' });
		await logJump(email, day(-61));
		await signIn(page, email, '/profile');
		await setLicence(page, 'A licence');
		await page.goto('/jumps');
		await expect(page.getByTestId('currency-status')).toHaveText(
			`Not current since ${long(day(0))}: USPA recommends a supervised jump before your next solo jump. Your dropzone may require more.`
		);

		// Day 60 is still current.
		const email2 = await createAccount({ label: 'day60' });
		await logJump(email2, day(-60));
		await page.context().clearCookies();
		await signIn(page, email2, '/profile');
		await setLicence(page, 'A licence');
		await page.goto('/history');
		await expect(page.getByTestId('currency-status')).toHaveText(
			`Current until ${long(day(0))} (USPA guidance for an A licence: 60 days).`
		);
	});

	test('saving a form lower on the page brings its confirmation into view', async ({ page }) => {
		const email = await createAccount({ label: 'save-view' });
		await signIn(page, email, '/profile');
		await page.setViewportSize({ width: 320, height: 640 });
		await page.waitForFunction(() => document.documentElement.dataset.formGuard === 'ready');

		await page.getByRole('combobox', { name: 'Licence' }).selectOption({ label: 'A licence' });
		await page.getByRole('button', { name: 'Save licence' }).click();
		const licence = page.getByRole('status').filter({ hasText: 'Licence saved.' });
		await expect(licence).toBeInViewport();
		await expect(licence).toBeFocused();

		await page.locator('#exit_weight').fill('82');
		await page.getByRole('button', { name: 'Save exit weight' }).click();
		const weight = page.getByRole('status').filter({ hasText: 'Exit weight saved.' });
		await expect(weight).toBeInViewport();
		await expect(weight).toBeFocused();
	});
});
