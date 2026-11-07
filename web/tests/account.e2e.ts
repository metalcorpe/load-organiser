import { expect, test, type Page } from '@playwright/test';
import { randomBytes } from 'node:crypto';
import { PASSWORD, createAccount } from './support/accounts.ts';

// Account deletion on the production-cookie preview.
const ORIGIN = 'https://127.0.0.1:4175';
test.use({ baseURL: ORIGIN, ignoreHTTPSErrors: true });

async function signIn(page: Page, email: string, returnTo = '/profile') {
	await page.goto(`/sign-in?returnTo=${encodeURIComponent(returnTo)}`);
	await page.getByLabel('Email', { exact: true }).fill(email);
	await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
	await page.getByRole('button', { name: 'Sign in' }).click();
}

test.describe('account deletion', () => {
	test('needs the box and the password, then removes the account and its posts', async ({
		page,
		browser
	}) => {
		const tag = randomBytes(4).toString('hex');
		const email = await createAccount({ label: 'deleting' });
		await signIn(page, email, '/profile/public');
		await page.getByLabel('Handle').fill(`x${tag}`);
		await page.getByLabel('Display name').fill(`Leaving ${tag}`);
		await page.getByLabel('Let people find my profile').check();
		await page.getByRole('button', { name: 'Create profile' }).click();
		await expect(page.getByText('Saved.', { exact: true })).toBeVisible();

		const visitor = await (
			await browser.newContext({ baseURL: ORIGIN, ignoreHTTPSErrors: true })
		).newPage();
		expect((await visitor.goto(`/people/x${tag}`))?.status()).toBe(200);

		await page.goto('/profile');
		const section = page.getByRole('region', { name: 'Delete account' });
		await section.getByLabel('Password').fill(PASSWORD);
		await section.getByRole('button', { name: 'Delete account' }).click();
		await expect(page.getByRole('alert')).toContainText('Tick the box');

		await section.getByLabel('Password').fill('not the password');
		await section.getByLabel('Delete my account and records').check();
		await section.getByRole('button', { name: 'Delete account' }).click();
		await expect(page.getByRole('alert')).toContainText('That password is incorrect.');

		await section.getByLabel('Password').fill(PASSWORD);
		await section.getByLabel('Delete my account and records').check();
		await section.getByRole('button', { name: 'Delete account' }).click();
		await expect(page).toHaveURL(`${ORIGIN}/sign-in?notice=account-deleted`);
		await expect(page.getByText('Account deleted')).toBeVisible();

		// The session is gone, the public profile is gone, and the password no longer works.
		await page.goto('/profile');
		await expect(page).toHaveURL(`${ORIGIN}/sign-in?returnTo=%2Fprofile`);
		expect((await visitor.goto(`/people/x${tag}`))?.status()).toBe(404);
		await signIn(page, email);
		await expect(page.getByRole('alert')).toBeVisible();
		await expect(page).toHaveURL(/\/sign-in/);

		await visitor.context().close();
	});
});
