import { expect, test, type APIRequestContext, type Page } from '@playwright/test';
import { randomBytes } from 'node:crypto';
import { PASSWORD, createAccount } from './support/accounts.ts';
import { openJumpSections } from './support/jump-form.ts';

// #160 what leaves the server: raw HTML and SvelteKit data payloads of public
// pages, and cross-site writes to JSON routes, on the production-cookie preview.
const ORIGIN = 'https://127.0.0.1:4175';
const COOKIE = '__Host-organiser_session';
test.use({ baseURL: ORIGIN, ignoreHTTPSErrors: true });

async function signIn(page: Page, email: string) {
	await page.goto('/sign-in?returnTo=%2Fjumps');
	await page.getByLabel('Email', { exact: true }).fill(email);
	await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
	await page.getByRole('button', { name: 'Sign in' }).click();
	await expect(page).toHaveURL(`${ORIGIN}/jumps`);
}

/** What a reader receives for a page: its HTML and its client data request, apart. */
async function payload(request: APIRequestContext, path: string) {
	const html = await request.get(path, { maxRedirects: 0 });
	const data = await request.get(`${path.replace(/\/$/, '')}/__data.json`, { maxRedirects: 0 });
	return {
		htmlStatus: html.status(),
		html: await html.text(),
		dataStatus: data.status(),
		data: await data.text()
	};
}

test.describe('payload boundaries', () => {
	test('public pages carry the shared card and nothing private', async ({ page, playwright }) => {
		const tag = randomBytes(4).toString('hex');
		const secrets = [`Secret farm ${tag}`, `secret note ${tag}`, `secret gear ${tag}`];
		const email = await createAccount({ label: 'payload' });
		await signIn(page, email);
		const handle = `b${tag}`;
		await page.goto('/profile/public');
		await page.getByLabel('Handle').fill(handle);
		await page.getByLabel('Display name').fill(`Boundary ${tag}`);
		await page.getByLabel('Let people find my profile').check();
		await page.getByRole('button', { name: 'Create profile' }).click();
		await expect(page.getByText('Saved.', { exact: true })).toBeVisible();

		await page.goto('/jumps/new');
		await page.getByLabel('Place name').fill(secrets[0]);
		await page.getByLabel('Country', { exact: true }).selectOption('PT');
		await page.getByRole('button', { name: 'Use this place' }).click();
		await page.getByLabel('Date', { exact: true }).fill('2026-10-10');
		await page.getByLabel('Type', { exact: true }).selectOption('freefly');
		await openJumpSections(page);
		await page.getByLabel('Your jump number').fill('4321');
		// Field names of private values; the values themselves are checked below.
		const privateKeys = ['"notes"', '"other_gear"', '"jump_number"', '"place_id"', '"links"'];
		await page.getByLabel('Borrowed, rented or other equipment').fill(secrets[2]);
		await page.getByLabel('Notes (optional, private)').fill(secrets[1]);
		await page.getByRole('button', { name: 'Save private jump' }).first().click();
		await expect(page.getByText('Saved privately.')).toBeVisible();
		await page.getByRole('link', { name: 'Share a summary of this jump' }).click();
		await page.getByLabel(/Caption/).fill(`Shared caption ${tag}`);
		await page.getByLabel('Public', { exact: true }).check();
		await page.getByRole('button', { name: 'Preview' }).click();
		await page.getByRole('button', { name: 'Publish' }).click();
		await expect(page.getByText('Published.', { exact: true })).toBeVisible();
		const post = await page
			.getByRole('article')
			.getByRole('link', { name: /^Jump on / })
			.getAttribute('href');

		// Signed out and signed in as someone else: the card, never the source.
		const guest = await playwright.request.newContext({ baseURL: ORIGIN, ignoreHTTPSErrors: true });
		const otherPage = await (
			await page.context().browser()!.newContext({ baseURL: ORIGIN, ignoreHTTPSErrors: true })
		).newPage();
		await signIn(otherPage, await createAccount({ label: 'payload-other' }));
		for (const reader of [guest, otherPage.request]) {
			for (const path of [post!, `/people/${handle}`]) {
				const got = await payload(reader, path);
				// Both parts are real pages carrying the card, so the absence checks count.
				expect([got.htmlStatus, got.dataStatus], path).toEqual([200, 200]);
				expect(got.html, path).toContain(`Shared caption ${tag}`);
				expect(got.data, path).toContain(`Shared caption ${tag}`);
				for (const part of [got.html, got.data]) {
					for (const secret of [...secrets, email]) {
						expect(part, `${path} leaks ${secret}`).not.toContain(secret);
					}
					for (const key of privateKeys) expect(part, `${path} has ${key}`).not.toContain(key);
				}
			}
		}
		// The owner's private jump data: present for the owner (so the path is right),
		// absent without a session.
		const jumpPath = new URL(page.url()).pathname.replace(/\/share$/, '');
		const own = await payload(page.request, jumpPath);
		expect(own.dataStatus).toBe(200);
		for (const secret of secrets) expect(own.data).toContain(secret);
		const anonymous = await payload(guest, jumpPath);
		expect(anonymous.htmlStatus).toBe(303);
		for (const secret of secrets) {
			expect(anonymous.html).not.toContain(secret);
			expect(anonymous.data).not.toContain(secret);
		}

		await guest.dispose();
		await otherPage.context().close();
	});

	test('a cross-site POST to a JSON route is refused even with a session', async ({
		page,
		context,
		playwright
	}) => {
		await signIn(page, await createAccount({ label: 'csrf-json' }));
		const secret = (await context.cookies(ORIGIN)).find((c) => c.name === COOKIE)!.value;
		const request = await playwright.request.newContext({ ignoreHTTPSErrors: true });
		const response = await request.post(`${ORIGIN}/profile/data/export`, {
			headers: {
				origin: 'https://evil.example',
				cookie: `${COOKIE}=${secret}`,
				'content-type': 'application/x-www-form-urlencoded'
			},
			data: `password=${encodeURIComponent(PASSWORD)}`,
			maxRedirects: 0
		});
		expect(response.status()).toBe(403);
		expect(response.headers()['content-disposition']).toBeUndefined();
		await request.dispose();
	});
});
