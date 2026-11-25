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
const toggle = (page: Page) => page.getByRole('banner').getByRole('button', { name: /^Theme:/ });

test.describe('theme button (theme.ts), one control for guests and members', () => {
	test('a guest cycles device, light, dark and back, staying on the same page', async ({ page }) => {
		await page.emulateMedia({ colorScheme: 'dark' });
		await page.goto('/dz?q=a');
		expect(await background(page)).toBe(DARK_BG);
		await expect(toggle(page)).toHaveAccessibleName('Theme: Use device setting. Change to Light');

		await toggle(page).click();
		await expect(page).toHaveURL(`${ORIGIN}/dz?q=a`);
		expect(await theme(page)).toBe('light');
		expect(await background(page)).toBe(LIGHT_BG);
		await expect(page.locator('meta[name="color-scheme"]')).toHaveAttribute('content', 'light');
		await expect(toggle(page)).toHaveAccessibleName('Theme: Light. Change to Dark');

		// Rendered by the server on every page: no flash.
		await page.goto('/');
		expect(await theme(page)).toBe('light');

		await toggle(page).click();
		expect(await theme(page)).toBe('dark');
		expect(await background(page)).toBe(DARK_BG);

		await toggle(page).click();
		expect(await theme(page)).toBeNull();
		await expect(page.locator('meta[name="color-scheme"]')).toHaveAttribute('content', 'light dark');
		await expect(toggle(page)).toHaveAccessibleName('Theme: Use device setting. Change to Light');
	});

	test('a member has the same button, and the choice carries over from signed out', async ({ page }) => {
		await page.emulateMedia({ colorScheme: 'light' });
		await page.goto('/');
		await toggle(page).click();
		await toggle(page).click();
		expect(await theme(page)).toBe('dark');
		await page.goto('/sign-in?returnTo=%2Fjumps');
		await page.getByLabel('Email', { exact: true }).fill(await createAccount({ label: 'theme' }));
		await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
		await page.getByRole('button', { name: 'Sign in' }).click();
		await expect(page).toHaveURL(`${ORIGIN}/jumps`);
		expect(await theme(page)).toBe('dark');
		await expect(toggle(page)).toHaveAccessibleName('Theme: Dark. Change to Use device setting');
		// Not a second control on Preferences.
		await page.goto('/profile/preferences');
		await expect(page.getByRole('heading', { name: 'Appearance' })).toHaveCount(0);
	});

	test('the return address stays on this site, and an unknown cookie value follows the device', async ({
		page,
		context
	}) => {
		const response = await page.request.post('/appearance', {
			form: { theme: 'dark', returnTo: '//evil.example/x' },
			headers: { origin: ORIGIN },
			maxRedirects: 0
		});
		expect(response.status()).toBe(303);
		expect(response.headers()['location']).toBe('/');

		// That post saved a theme in this context; start the next check from no cookie.
		await context.clearCookies();
		const host = new URL(ORIGIN).hostname;
		await context.addCookies([{ name: 'theme', value: '"><script>x</script>', domain: host, path: '/', secure: true }]);
		await page.emulateMedia({ colorScheme: 'light' });
		await page.goto('/');
		expect(await theme(page)).toBeNull();
		expect(await background(page)).toBe(LIGHT_BG);
	});
});
