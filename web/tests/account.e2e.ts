import { expect, test, type Page } from '@playwright/test';
import { randomBytes } from 'node:crypto';
import { PASSWORD, createAccount } from './support/accounts.ts';
import { SECURE_ORIGIN } from './support/origins.ts';

// Account deletion on the production-cookie preview.
const ORIGIN = SECURE_ORIGIN;
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
	test('Me leads with where things are; the settings are summaries; old deep links still land', async ({
		page
	}) => {
		const email = await createAccount({ label: 'mesplit' });
		await signIn(page, email);
		await expect(page).toHaveURL(`${ORIGIN}/profile`);
		await expect(page.getByRole('heading', { level: 1 })).toHaveText('Me');
		await expect(page.getByTestId('account-email')).toHaveText(email);
		const rows = page.getByRole('navigation', { name: 'Your things and settings' });
		for (const name of [
			'Plans and saved events',
			'Gear',
			'Edit Licence',
			'Edit Exit weight',
			'Edit Public profile',
			'Account and security',
			'Import a logbook',
			'Export or restore',
			'Printable logbook',
			'Private places',
			'Suggestions and reports',
			'Send feedback',
			'Privacy and the beta'
		]) {
			await expect(rows.getByRole('link', { name: new RegExp(`^${name}`) })).toBeVisible();
		}
		// Each setting is a summary with its value, not a form.
		await expect(rows.getByRole('link', { name: /^Edit Licence/ })).toContainText('No licence');
		await expect(page.getByRole('button', { name: 'Save licence' })).toHaveCount(0);
		// On a phone the places come right after who you are, not below forms.
		await page.setViewportSize({ width: 390, height: 844 });
		await expect(rows.getByRole('link', { name: /^Plans and saved events/ })).toBeInViewport();
		// Not a reviewer: no reviewer tools.
		await expect(rows.getByRole('link', { name: /Maintenance/ })).toHaveCount(0);
		// The password and deletion forms are not on Me.
		await expect(page.getByRole('button', { name: 'Change password' })).toHaveCount(0);
		await expect(page.getByRole('region', { name: 'Delete account' })).toHaveCount(0);

		// The licence and exit weight are edited on Jump preferences, reached from their rows.
		await rows.getByRole('link', { name: /^Edit Exit weight/ }).click();
		await expect(page).toHaveURL(`${ORIGIN}/profile/preferences#weight-heading`);
		await expect(page.getByRole('heading', { level: 2, name: 'Exit weight' })).toBeInViewport();
		await page.getByLabel('Exit weight (optional)', { exact: true }).fill('80');
		await page.getByRole('button', { name: 'Save exit weight' }).click();
		await expect(page.getByText('Exit weight saved.', { exact: true })).toBeVisible();
		await page.goto('/profile');
		await expect(rows.getByRole('link', { name: /^Edit Exit weight/ })).toContainText('80 kg');

		// Old deep links to the settings on Me go on to the settings themselves.
		for (const [hash, name] of [
			['licence-heading', 'Licence'],
			['weight-heading', 'Exit weight']
		]) {
			await page.goto(`/profile#${hash}`);
			await expect(page).toHaveURL(`${ORIGIN}/profile/preferences#${hash}`);
			await expect(page.getByRole('heading', { level: 2, name, exact: true })).toBeInViewport();
		}

		await page.goto('/profile');
		await rows.getByRole('link', { name: /^Account and security/ }).click();
		await expect(page).toHaveURL(`${ORIGIN}/profile/account`);
		await expect(page.getByTestId('account-email')).toHaveText(email);
		for (const name of ['Change password', 'Sign out everywhere', 'Delete account']) {
			await expect(page.getByRole('region', { name })).toBeVisible();
		}
		// Me is still the current tab, on its pages and on Jump preferences.
		const me = page.getByRole('navigation', { name: 'Primary' }).getByRole('link', { name: 'Me' });
		await expect(me).toHaveAttribute('aria-current', 'page');
		await page.goto('/profile/preferences');
		await expect(me).toHaveAttribute('aria-current', 'page');
	});

	test('without a destination, signing in lands on the Logbook; a destination is kept', async ({
		page
	}) => {
		const email = await createAccount({ label: 'landing' });
		await page.goto('/sign-in');
		await page.getByLabel('Email', { exact: true }).fill(email);
		await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
		await page.getByRole('button', { name: 'Sign in' }).click();
		await expect(page).toHaveURL(`${ORIGIN}/jumps`);
		// Signed in, /sign-in and /register lead there too, or to the destination they name.
		await page.goto('/sign-in');
		await expect(page).toHaveURL(`${ORIGIN}/jumps`);
		await page.goto('/register?returnTo=%2Fstats');
		await expect(page).toHaveURL(`${ORIGIN}/stats`);
		// Explore stays a page of its own for members.
		await page.goto('/');
		await expect(page).toHaveURL(`${ORIGIN}/`);
		await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
	});
});
