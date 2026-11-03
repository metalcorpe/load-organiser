import { expect, test, type Browser, type BrowserContext, type Page } from '@playwright/test';
import {
	NEW_PASSWORD,
	PASSWORD,
	createAccount,
	mailedToken,
	sessionStatus,
	uniqueEmail
} from './support/accounts.ts';

// Production cookie path: HTTPS workerd preview with the __Host- Secure cookie.
const ORIGIN = 'https://127.0.0.1:4175';
const COOKIE = '__Host-organiser_session';
test.use({ baseURL: ORIGIN, ignoreHTTPSErrors: true });

async function signIn(page: Page, email: string, password = PASSWORD) {
	await page.getByLabel('Email', { exact: true }).fill(email);
	await page.getByLabel('Password', { exact: true }).fill(password);
	await page.getByRole('button', { name: 'Sign in' }).click();
}

async function sessionCookie(context: BrowserContext) {
	return (await context.cookies(ORIGIN)).find((cookie) => cookie.name === COOKIE);
}

async function newContext(browser: Browser) {
	return browser.newContext({ baseURL: ORIGIN, ignoreHTTPSErrors: true });
}

test.describe('registration and verification', () => {
	test('register, confirm by POST, sign in with a production session cookie', async ({ page, context }) => {
		const email = uniqueEmail('register');
		await page.goto('/register');
		await page.getByLabel('Email').fill(email);
		await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
		await page.getByLabel('Repeat password').fill(PASSWORD);
		await page.getByRole('button', { name: 'Create account' }).click();
		await expect(page.getByRole('heading', { name: 'Check your email' })).toBeVisible();

		// Opening the link (GET) does not confirm; the visitor confirms with a POST.
		const token = await mailedToken(email, 'verify-email');
		await page.goto(`/verify-email?token=${token}`);
		await expect(page.getByRole('button', { name: 'Confirm email' })).toBeVisible();
		await page.getByRole('button', { name: 'Confirm email' }).click();
		await expect(page.getByRole('heading', { name: 'Email confirmed' })).toBeVisible();

		await page.getByRole('link', { name: 'Sign in' }).last().click();
		await signIn(page, email);
		await expect(page).toHaveURL(`${ORIGIN}/`);
		await expect(page.getByTestId('current-account')).toHaveText(email);

		const cookie = await sessionCookie(context);
		expect(cookie).toMatchObject({ httpOnly: true, secure: true, sameSite: 'Lax', path: '/' });
		expect(cookie?.domain).toBe('127.0.0.1'); // host-only: no Domain attribute

		await page.goto('/profile');
		await expect(page.getByTestId('email-status')).toHaveText('Confirmed');
		// The secret is never rendered or serialised into page data.
		expect(await page.content()).not.toContain(cookie!.value);
		const data = await page.request.get('/profile/__data.json');
		expect(await data.text()).not.toContain(cookie!.value);
	});

	test('duplicate registration gives the same answer', async ({ page }) => {
		const email = await createAccount();
		await page.goto('/register');
		await page.getByLabel('Email').fill(email);
		await page.getByLabel('Password', { exact: true }).fill(NEW_PASSWORD);
		await page.getByLabel('Repeat password').fill(NEW_PASSWORD);
		await page.getByRole('button', { name: 'Create account' }).click();
		await expect(page.getByRole('heading', { name: 'Check your email' })).toBeVisible();
	});

	test('short passwords are refused with a specific message', async ({ page }) => {
		await page.goto('/register');
		await page.getByLabel('Email').fill(uniqueEmail());
		await page.getByLabel('Password', { exact: true }).fill('fourteen chars');
		await page.getByLabel('Repeat password').fill('fourteen chars');
		await page.getByRole('button', { name: 'Create account' }).click();
		await expect(page.getByRole('alert')).toHaveText('Use at least 15 characters.');
	});
});

test.describe('sessions', () => {
	test('wrong password and unknown account show the same message', async ({ page }) => {
		const email = await createAccount();
		await page.goto('/sign-in');
		await signIn(page, email, NEW_PASSWORD);
		await expect(page.getByRole('alert')).toBeVisible();
		// The server-rendered form keeps the email, never the password.
		await expect(page.getByLabel('Email')).toHaveValue(email);
		await expect(page.getByLabel('Password', { exact: true })).toHaveValue('');
		const wrong = await page.getByRole('alert').textContent();
		await signIn(page, uniqueEmail(), PASSWORD);
		await expect(page.getByRole('alert')).toHaveText(wrong!);
	});

	test('sign-in returns to the saved deep link', async ({ page }) => {
		const email = await createAccount();
		await page.goto('/records');
		await expect(page).toHaveURL(`${ORIGIN}/sign-in?returnTo=%2Frecords`);
		await signIn(page, email);
		await expect(page).toHaveURL(`${ORIGIN}/records`);
		await expect(page.getByRole('heading', { level: 1, name: 'Records' })).toBeVisible();
	});

	test('unconfirmed accounts see why private writes are blocked', async ({ page }) => {
		const email = await createAccount({ verified: false });
		await page.goto('/sign-in?returnTo=%2Frecords');
		await signIn(page, email);
		await expect(page.getByRole('heading', { name: 'Confirm your email' })).toBeVisible();
	});

	test('sign-out revokes the session server-side and private back navigation re-checks', async ({
		page,
		context
	}) => {
		const email = await createAccount();
		await page.goto('/sign-in?returnTo=%2Fprofile');
		await signIn(page, email);
		await expect(page.getByTestId('account-email')).toHaveText(email);
		const secret = (await sessionCookie(context))!.value;

		const signOutResponse = page.waitForResponse(
			(response) => response.url() === `${ORIGIN}/sign-out` && response.request().method() === 'POST'
		);
		await page.getByRole('button', { name: 'Sign out', exact: true }).click();
		expect((await (await signOutResponse).allHeaders())['clear-site-data']).toBe('"cache"');
		await expect(page).toHaveURL(`${ORIGIN}/sign-in?notice=signed-out`);
		expect(await sessionCookie(context)).toBeUndefined();
		expect(await sessionStatus(secret)).toBe(401);

		await page.goBack();
		await expect(page.getByTestId('account-email')).toHaveCount(0);
		await expect(page.getByText(email)).toHaveCount(0);
	});

	test('switching accounts in one browser never shows the previous account', async ({ page }) => {
		const first = await createAccount({ label: 'first' });
		const second = await createAccount({ label: 'second' });

		await page.goto('/sign-in?returnTo=%2Fprofile');
		await signIn(page, first);
		await expect(page.getByTestId('account-email')).toHaveText(first);
		await page.getByRole('button', { name: 'Sign out', exact: true }).click();

		await signIn(page, second);
		await page.goto('/profile');
		await expect(page.getByTestId('account-email')).toHaveText(second);
		expect(await page.content()).not.toContain(first);
	});

	test('two signed-in browsers keep request-local identities', async ({ browser }) => {
		const alice = await createAccount({ label: 'alice' });
		const bob = await createAccount({ label: 'bob' });
		const [a, b] = await Promise.all([newContext(browser), newContext(browser)]);
		const [pageA, pageB] = await Promise.all([a.newPage(), b.newPage()]);
		await pageA.goto('/sign-in?returnTo=%2Fprofile');
		await pageB.goto('/sign-in?returnTo=%2Fprofile');
		await signIn(pageA, alice);
		await signIn(pageB, bob);
		await Promise.all([pageA.reload(), pageB.reload()]);
		await expect(pageA.getByTestId('account-email')).toHaveText(alice);
		await expect(pageB.getByTestId('account-email')).toHaveText(bob);
		await Promise.all([a.close(), b.close()]);
	});

	test('a forged or stale cookie is treated as signed out and cleared', async ({ page, context }) => {
		await context.addCookies([
			{
				name: COOKIE,
				value: 'x'.repeat(43),
				url: ORIGIN,
				secure: true,
				httpOnly: true,
				sameSite: 'Lax'
			}
		]);
		await page.goto('/profile');
		await expect(page).toHaveURL(`${ORIGIN}/sign-in?returnTo=%2Fprofile`);
		expect(await sessionCookie(context)).toBeUndefined();
	});
});

test.describe('recovery and revocation', () => {
	test('forgot-password answers identically for known and unknown emails', async ({ page }) => {
		const known = await createAccount();
		const texts: string[] = [];
		for (const email of [known, uniqueEmail()]) {
			await page.goto('/forgot-password');
			await page.getByLabel('Email').fill(email);
			await page.getByRole('button', { name: 'Send reset link' }).click();
			texts.push((await page.getByRole('main').textContent()) ?? '');
		}
		expect(texts[0]).toBe(texts[1]);
	});

	test('password reset revokes sessions in other browsers', async ({ browser, page }) => {
		const email = await createAccount();
		const other = await newContext(browser);
		const otherPage = await other.newPage();
		await otherPage.goto('/sign-in?returnTo=%2Fprofile');
		await signIn(otherPage, email);
		await expect(otherPage.getByTestId('account-email')).toHaveText(email);

		await page.goto('/forgot-password');
		await page.getByLabel('Email').fill(email);
		await page.getByRole('button', { name: 'Send reset link' }).click();
		const token = await mailedToken(email, 'reset-password');
		await page.goto(`/reset-password?token=${token}`);
		await page.getByLabel('New password', { exact: true }).fill(NEW_PASSWORD);
		await page.getByLabel('Repeat new password').fill(NEW_PASSWORD);
		await page.getByRole('button', { name: 'Change password' }).click();
		await expect(page).toHaveURL(`${ORIGIN}/sign-in?notice=reset`);

		await otherPage.reload();
		await expect(otherPage).toHaveURL(`${ORIGIN}/sign-in?returnTo=%2Fprofile`);

		// The link is single-use.
		await page.goto(`/reset-password?token=${token}`);
		await page.getByLabel('New password', { exact: true }).fill(PASSWORD);
		await page.getByLabel('Repeat new password').fill(PASSWORD);
		await page.getByRole('button', { name: 'Change password' }).click();
		await expect(page.getByRole('alert')).toContainText('invalid, expired or already used');

		await page.goto('/sign-in');
		await signIn(page, email, NEW_PASSWORD);
		await expect(page.getByTestId('current-account')).toHaveText(email);
		await other.close();
	});

	test('sign out everywhere needs the password and ends every session', async ({ browser, page }) => {
		const email = await createAccount();
		const other = await newContext(browser);
		const otherPage = await other.newPage();
		await otherPage.goto('/sign-in?returnTo=%2Fprofile');
		await signIn(otherPage, email);

		await page.goto('/sign-in?returnTo=%2Fprofile');
		await signIn(page, email);
		const everywhere = page.getByRole('region', { name: 'Sign out everywhere' });
		await everywhere.getByLabel('Password').fill(NEW_PASSWORD);
		await everywhere.getByRole('button', { name: 'Sign out everywhere' }).click();
		await expect(page.getByRole('alert')).toHaveText('That password is incorrect.');

		await page
			.getByRole('region', { name: 'Sign out everywhere' })
			.getByLabel('Password')
			.fill(PASSWORD);
		await page.getByRole('button', { name: 'Sign out everywhere' }).click();
		await expect(page).toHaveURL(`${ORIGIN}/sign-in?notice=signed-out-everywhere`);
		await otherPage.goto('/profile');
		await expect(otherPage).toHaveURL(`${ORIGIN}/sign-in?returnTo=%2Fprofile`);
		await other.close();
	});
});

test.describe('origin enforcement on the production build', () => {
	for (const [label, headers] of [
		['cross-site', { origin: 'https://evil.example' }],
		['null', { origin: 'null' }],
		['absent', {}]
	] as const) {
		test(`sign-in POST with ${label} Origin is refused`, async ({ playwright }) => {
			const request = await playwright.request.newContext({ ignoreHTTPSErrors: true });
			const response = await request.post(`${ORIGIN}/sign-in`, {
				headers: { ...headers, 'content-type': 'application/x-www-form-urlencoded' },
				data: 'email=a%40example.com&password=x',
				maxRedirects: 0
			});
			expect(response.status()).toBe(403);
			await request.dispose();
		});
	}

	test('sign-out POST from another site does not end the session', async ({ page, context, playwright }) => {
		const email = await createAccount();
		await page.goto('/sign-in');
		await signIn(page, email);
		const secret = (await sessionCookie(context))!.value;
		const request = await playwright.request.newContext({ ignoreHTTPSErrors: true });
		const response = await request.post(`${ORIGIN}/sign-out`, {
			headers: {
				origin: 'https://evil.example',
				cookie: `${COOKIE}=${secret}`,
				'content-type': 'application/x-www-form-urlencoded'
			},
			data: '',
			maxRedirects: 0
		});
		expect(response.status()).toBe(403);
		expect(await sessionStatus(secret)).toBe(200);
		await request.dispose();
	});
});
