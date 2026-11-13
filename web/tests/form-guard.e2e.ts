import { expect, test, type Page } from '@playwright/test';
import { PASSWORD, createAccount } from './support/accounts.ts';

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

const guardReady = (page: Page) =>
	expect(page.locator('html[data-form-guard="ready"]')).toHaveCount(1);

test.describe('form errors after a save', () => {
	test('fields with their own error are not also described by the summary', async ({ page }) => {
		await page.goto('/register');
		await guardReady(page);
		await page.getByRole('button', { name: 'Create account' }).click();
		await expect(page.locator('#register-error')).toBeVisible();

		const email = page.getByLabel('Email');
		await expect(email).toBeFocused();
		await expect(email).toHaveAttribute('aria-describedby', 'email-error');
		await expect(email).toHaveAccessibleDescription('Enter your email address.');

		const password = page.getByLabel('Password', { exact: true });
		await expect(password).toHaveAttribute('aria-describedby', 'password-hint password-error');
		await expect(password).not.toHaveAccessibleDescription(/email/i);

		const repeat = page.getByLabel('Repeat password');
		await expect(repeat).not.toHaveAttribute('aria-describedby', /register-error/);
	});

	test('a form without field errors still links the field to the summary', async ({ page }) => {
		const email = await createAccount({ label: 'guard-summary' });
		await signIn(page, email, '/profile');
		await guardReady(page);

		await page.getByLabel('Current password').fill(PASSWORD);
		await page.getByLabel('New password', { exact: true }).fill('a new long passphrase one');
		await page.getByLabel('Repeat new password').fill('a new long passphrase two');
		await page.getByRole('button', { name: 'Change password' }).click();

		const repeat = page.getByLabel('Repeat new password');
		await expect(repeat).toBeFocused();
		await expect(repeat).toHaveAttribute('aria-invalid', 'true');
		const summary = page.locator('section[aria-labelledby="password-heading"] .form-error');
		const summaryId = await summary.getAttribute('id');
		expect(summaryId).toBeTruthy();
		await expect(repeat).toHaveAttribute('aria-describedby', summaryId!);
	});

	test('a field described only by a hint keeps the hint and gains the summary', async ({ page }) => {
		const email = await createAccount({ label: 'guard-hint' });
		await signIn(page, email, '/profile');
		await guardReady(page);

		await page.getByLabel('Current password').fill(PASSWORD);
		await page.getByLabel('New password', { exact: true }).fill('too short');
		await page.getByLabel('Repeat new password').fill('too short');
		await page.getByRole('button', { name: 'Change password' }).click();

		const next = page.getByLabel('New password', { exact: true });
		await expect(next).toBeFocused();
		const summary = page.locator('section[aria-labelledby="password-heading"] .form-error');
		const summaryId = await summary.getAttribute('id');
		await expect(next).toHaveAttribute('aria-describedby', `new-password-hint ${summaryId}`);
	});
});
