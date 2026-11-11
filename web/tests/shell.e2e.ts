import { expect, test, type Page } from '@playwright/test';

const PRIVATE_PATHS = [
	'/activity',
	'/jumps',
	'/jumps/new',
	'/jumps/01900000-0000-7000-8000-000000000000/share',
	'/history',
	'/history/baseline',
	'/profile/data',
	'/profile/public',
	'/people',
	'/review/social',
	'/records',
	'/profile',
	'/places',
	'/gear',
	'/gear/new',
	'/saved',
	'/plans'
];
const API_HOST = new URL(process.env.E2E_API_ORIGIN ?? 'http://127.0.0.1:8144').host;

function trackConsoleErrors(page: Page): string[] {
	const errors: string[] = [];
	page.on('console', (message) => {
		if (message.type() === 'error') errors.push(message.text());
	});
	page.on('pageerror', (error) => errors.push(error.message));
	return errors;
}

test.describe('public shell', () => {
	test('Discover deep link renders SSR with headers and no fabricated listings', async ({ page }) => {
		const errors = trackConsoleErrors(page);
		const response = await page.goto('/');
		expect(response?.status()).toBe(200);
		const headers = response!.headers();
		expect(headers['cache-control']).toBe('no-store');
		expect(headers['content-security-policy']).toContain("frame-ancestors 'none'");
		expect(headers['x-content-type-options']).toBe('nosniff');

		await expect(page.getByRole('heading', { level: 1, name: 'Events' })).toBeVisible();
		// Either reviewed listings or the honest empty state; never placeholder activity.
		await expect(
			page
				.getByRole('list', { name: 'Listings' })
				.or(page.getByText('No listings published yet'))
		).toBeVisible();

		// Guests browse the public area without the members' tab bar.
		await expect(page.getByRole('navigation', { name: 'Primary' })).toHaveCount(0);
		await expect(page.getByRole('banner').getByRole('link', { name: 'Sign in' })).toBeVisible();
		await expect(page.getByRole('banner').getByRole('link', { name: 'Join' })).toBeVisible();
		const explore = page.getByRole('navigation', { name: 'Explore' });
		await expect(explore.getByRole('link', { name: 'Events' })).toHaveAttribute('aria-current', 'page');
		expect(errors).toEqual([]);
	});

	test('navigation fits small screens with 44px targets and no horizontal scroll', async ({ page }) => {
		await page.goto('/');
		const overflow = await page.evaluate(
			() => document.documentElement.scrollWidth - document.documentElement.clientWidth
		);
		expect(overflow).toBeLessThanOrEqual(0);
		for (const link of await page.getByRole('navigation', { name: 'Primary' }).getByRole('link').all()) {
			const box = await link.boundingBox();
			expect(box!.height).toBeGreaterThanOrEqual(44);
			expect(box!.width).toBeGreaterThanOrEqual(44);
			await expect(link).toBeInViewport();
		}
	});

	test('skip link is first in tab order and moves focus to main content', async ({
		page,
		browserName
	}) => {
		await page.goto('/');
		// WebKit, like Safari on macOS, moves between links with Option+Tab; Tab alone
		// reaches form controls only unless the user changes that setting.
		await page.keyboard.press(browserName === 'webkit' ? 'Alt+Tab' : 'Tab');
		const skip = page.getByRole('link', { name: 'Skip to content' });
		await expect(skip).toBeFocused();
		await page.keyboard.press('Enter');
		await expect(page.locator('main')).toBeFocused();
	});

	test('unknown routes return a 404 page', async ({ page }) => {
		const response = await page.goto('/no-such-page');
		expect(response?.status()).toBe(404);
		expect(response?.headers()['cache-control']).toBe('no-store');
		await expect(page.getByRole('heading', { level: 1, name: 'Page not found' })).toBeVisible();
	});
});

test.describe('real API flow (isolated FastAPI + PostgreSQL)', () => {
	test('status deep link shows the live health result', async ({ page }) => {
		const errors = trackConsoleErrors(page);
		const response = await page.goto('/status');
		expect(response?.status()).toBe(200);
		expect(response?.headers()['cache-control']).toBe('no-store');
		await expect(page.getByTestId('health')).toHaveAttribute('data-state', 'operational');
		await expect(page.getByRole('heading', { name: 'Operational' })).toBeVisible();
		await expect(page.locator('time')).toHaveAttribute('datetime', /^\d{4}-\d\d-\d\dT.*Z$/);
		expect(errors).toEqual([]);
	});

	test('client navigation shows a loading state, then the result', async ({ page }) => {
		await page.goto('/');
		let release!: () => void;
		const gate = new Promise<void>((resolve) => (release = resolve));
		await page.route('**/status/__data.json**', async (route) => {
			await gate;
			await route.continue();
		});

		await page.getByRole('contentinfo').getByRole('link', { name: 'Service status' }).click();
		await expect(page.getByTestId('navigation-loading')).toBeVisible();
		await expect(page.getByRole('status').filter({ hasText: 'Loading…' })).toBeVisible();
		release();

		await expect(page).toHaveURL('/status');
		await expect(page.getByTestId('health')).toHaveAttribute('data-state', 'operational');
		await expect(page.getByTestId('navigation-loading')).toHaveCount(0);

		const firstCheck = await page.locator('time').getAttribute('datetime');
		await page.getByRole('button', { name: 'Check again' }).click();
		await expect(page.locator('time')).not.toHaveAttribute('datetime', firstCheck!);
	});

	test('API configuration never reaches the browser', async ({ page, request }) => {
		const scripts: string[] = [];
		page.on('response', async (response) => {
			if (response.url().endsWith('.js')) scripts.push(await response.text());
		});
		await page.goto('/status');
		await expect(page.getByTestId('health')).toHaveAttribute('data-state', 'operational');
		expect(await page.content()).not.toContain(API_HOST);
		expect(scripts.length).toBeGreaterThan(0);
		for (const source of scripts) expect(source).not.toContain(API_HOST);

		const data = await request.get('/status/__data.json');
		expect(data.headers()['cache-control']).toBe('no-store');
		expect(await data.text()).not.toContain(API_HOST);
	});
});

test.describe('private routes deny anonymous access', () => {
	for (const path of PRIVATE_PATHS) {
		test(`${path} redirects to sign-in without rendering private HTML`, async ({ request }) => {
			const response = await request.get(path, { maxRedirects: 0 });
			expect(response.status()).toBe(303);
			expect(response.headers()['location']).toBe(
				`/sign-in?returnTo=${encodeURIComponent(path)}`
			);
			expect(response.headers()['cache-control']).toBe('no-store');
			expect(await response.text()).toBe('');
		});
	}

	test('private data requests return a redirect instead of page data', async ({ request }) => {
		const response = await request.get('/records/__data.json', { maxRedirects: 0 });
		expect(response.headers()['cache-control']).toBe('no-store');
		const body = await response.json();
		expect(body).toMatchObject({ type: 'redirect', location: '/sign-in?returnTo=%2Frecords' });
		expect(JSON.stringify(body)).not.toContain('Not available yet');
	});

	test('direct navigation lands on the sign-in form', async ({ page }) => {
		await page.goto('/records');
		await expect(page).toHaveURL('/sign-in?returnTo=%2Frecords');
		await expect(page.getByRole('heading', { level: 1, name: 'Sign in' })).toBeVisible();
		await expect(page.getByText('Sign in to continue to the page you asked for.')).toBeVisible();
		await expect(page.getByRole('heading', { name: 'Records' })).toHaveCount(0);
	});

	test('the Explore switch moves between the public views, client-side', async ({ page }) => {
		await page.goto('/');
		await page.getByRole('navigation', { name: 'Explore' }).getByRole('link', { name: 'Dropzones' }).click();
		await expect(page).toHaveURL('/dz');
		await expect(page.getByRole('heading', { level: 1, name: 'Dropzones' })).toBeVisible();
		await expect(
			page.getByRole('navigation', { name: 'Explore' }).getByRole('link', { name: 'Dropzones' })
		).toHaveAttribute('aria-current', 'page');
	});

	test('a private section opened as a guest asks to sign in', async ({ page }) => {
		await page.goto('/jumps');
		await expect(page).toHaveURL('/sign-in?returnTo=%2Fjumps');
		await expect(page.getByRole('heading', { level: 1, name: 'Sign in' })).toBeVisible();
	});
});

test.describe('upstream failure (API origin points at a closed port)', () => {
	test.use({ baseURL: 'http://127.0.0.1:4174' });

	test('status page reports the API as unreachable', async ({ page }) => {
		const response = await page.goto('/status');
		expect(response?.status()).toBe(200);
		await expect(page.getByTestId('health')).toHaveAttribute('data-state', 'unreachable');
		await expect(page.getByRole('heading', { name: 'API unreachable' })).toBeVisible();
	});

	test('a session the API cannot confirm can still be signed out', async ({ request }) => {
		const cookie = `__Host-organiser_session=${'a'.repeat(43)}`;
		// Not bounced to /sign-in: the unconfirmed cookie is kept, so it must be clearable.
		const form = await request.get('/sign-out', { headers: { cookie }, maxRedirects: 0 });
		expect(form.status()).toBe(200);

		const signOut = await request.post('/sign-out', {
			headers: {
				cookie,
				accept: 'text/html',
				origin: 'http://127.0.0.1:4174',
				'content-type': 'application/x-www-form-urlencoded'
			},
			data: '',
			maxRedirects: 0
		});
		expect(signOut.status()).toBe(303);
		expect(signOut.headers()['location']).toBe('/sign-in?notice=signed-out-unconfirmed');
		expect(signOut.headers()['set-cookie']).toMatch(/__Host-organiser_session=;.*Max-Age=0/i);
	});
});
