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

		await page.goto('/profile/account');
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

test.describe('Me and Account and security', () => {
	test('Me is an overview; account and security has its own page; deep links still land', async ({
		page
	}) => {
		const email = await createAccount({ label: 'mesplit' });
		await signIn(page, email);
		await expect(page).toHaveURL(`${ORIGIN}/profile`);
		await expect(page.getByTestId('account-email')).toHaveText(email);
		const links = page.getByRole('navigation', { name: 'Your records and more' });
		for (const name of [
			'Logbook',
			'Statistics',
			'Gear',
			'Saved listings',
			'Visit plans',
			'Private places',
			'Export or restore',
			'Import from a spreadsheet',
			'Suggestions and reports',
			'Your public profile',
			'People and follow requests',
			'Privacy and the beta',
			'Send feedback'
		]) {
			await expect(links.getByRole('link', { name, exact: true })).toBeVisible();
		}
		// Not a reviewer: no reviewer tools.
		await expect(links.getByRole('link', { name: /Maintenance/ })).toHaveCount(0);
		// The password and deletion forms are no longer on Me.
		await expect(page.getByRole('button', { name: 'Change password' })).toHaveCount(0);
		await expect(page.getByRole('region', { name: 'Delete account' })).toHaveCount(0);

		// Old deep links to the licence and the exit weight keep working.
		for (const [hash, name] of [
			['licence-heading', 'Licence'],
			['weight-heading', 'Exit weight']
		]) {
			await page.goto(`/profile#${hash}`);
			await expect(page.getByRole('heading', { level: 2, name, exact: true })).toBeInViewport();
		}

		// Account and security is linked once, from the account card.
		await expect(page.getByRole('link', { name: 'Account and security' })).toHaveCount(1);
		await page.getByRole('link', { name: 'Account and security' }).click();
		await expect(page).toHaveURL(`${ORIGIN}/profile/account`);
		await expect(page.getByTestId('account-email')).toHaveText(email);
		for (const name of ['Change password', 'Sign out everywhere', 'Delete account']) {
			await expect(page.getByRole('region', { name })).toBeVisible();
		}
		// Me is still the current tab.
		await expect(
			page.getByRole('navigation', { name: 'Primary' }).getByRole('link', { name: 'Me' })
		).toHaveAttribute('aria-current', 'page');
	});
});
