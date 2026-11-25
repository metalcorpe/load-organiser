import { expect, test, type Page } from '@playwright/test';
import { PASSWORD, createAccount } from './support/accounts.ts';
import { SECURE_ORIGIN } from './support/origins.ts';

// The production-cookie preview: the theme cookie is Secure there, as on the hosted app.
const ORIGIN = SECURE_ORIGIN;
test.use({ baseURL: ORIGIN, ignoreHTTPSErrors: true });

const LIGHT_BG = 'rgb(245, 245, 247)';
const DARK_BG = 'rgb(17, 18, 20)';

const background = (page: Page) => page.evaluate(() => getComputedStyle(document.body).backgroundColor);
const theme = (page: Page) => page.locator('html').getAttribute('data-theme');

async function choose(page: Page, label: string) {
	await page.goto('/profile/preferences');
	await page.getByRole('group', { name: 'Theme' }).getByLabel(label).check();
	await page.getByRole('button', { name: 'Save appearance' }).click();
	await expect(page.getByRole('status').filter({ hasText: 'Appearance saved.' })).toBeVisible();
}

test.describe('appearance setting (theme.ts)', () => {
	test('light on a dark device, kept across pages, then back to the device setting', async ({ page }) => {
		await page.emulateMedia({ colorScheme: 'dark' });
		await page.goto('/sign-in?returnTo=%2Fprofile%2Fpreferences');
		await page.getByLabel('Email', { exact: true }).fill(await createAccount({ label: 'theme' }));
		await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
		await page.getByRole('button', { name: 'Sign in' }).click();
		await expect(page).toHaveURL(`${ORIGIN}/profile/preferences`);
		expect(await background(page)).toBe(DARK_BG);
		await expect(page.getByRole('group', { name: 'Theme' }).getByLabel('Use device setting')).toBeChecked();

		await choose(page, 'Light');
		expect(await theme(page)).toBe('light');
		expect(await background(page)).toBe(LIGHT_BG);
		await expect(page.getByRole('group', { name: 'Theme' }).getByLabel('Light')).toBeChecked();
		// Rendered by the server on every page: no flash, and the colour-scheme follows.
		await page.goto('/jumps');
		expect(await theme(page)).toBe('light');
		expect(await background(page)).toBe(LIGHT_BG);
		await expect(page.locator('meta[name="color-scheme"]')).toHaveAttribute('content', 'light');

		await choose(page, 'Use device setting');
		expect(await theme(page)).toBeNull();
		expect(await background(page)).toBe(DARK_BG);
		await expect(page.locator('meta[name="color-scheme"]')).toHaveAttribute('content', 'light dark');
	});

	test('the cookie works signed out, and an unknown value follows the device', async ({ browser }) => {
		const context = await browser.newContext({ baseURL: ORIGIN, ignoreHTTPSErrors: true, colorScheme: 'light' });
		const page = await context.newPage();
		const host = new URL(ORIGIN).hostname;
		await context.addCookies([{ name: 'theme', value: 'dark', domain: host, path: '/', secure: true }]);
		await page.goto('/');
		expect(await theme(page)).toBe('dark');
		expect(await background(page)).toBe(DARK_BG);

		await context.addCookies([{ name: 'theme', value: '"><script>x</script>', domain: host, path: '/', secure: true }]);
		await page.goto('/');
		expect(await theme(page)).toBeNull();
		expect(await background(page)).toBe(LIGHT_BG);
		await context.close();
	});
});
