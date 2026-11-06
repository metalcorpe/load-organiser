import { expect, test, type Browser, type Page } from '@playwright/test';
import { randomBytes } from 'node:crypto';
import { PASSWORD, createAccount } from './support/accounts.ts';

// Same production-cookie preview as the account tests.
const ORIGIN = 'https://127.0.0.1:4175';
test.use({ baseURL: ORIGIN, ignoreHTTPSErrors: true });

async function newPerson(browser: Browser, label: string) {
	const context = await browser.newContext({ baseURL: ORIGIN, ignoreHTTPSErrors: true });
	const page = await context.newPage();
	await page.goto('/sign-in?returnTo=%2Fjumps');
	await page.getByLabel('Email', { exact: true }).fill(await createAccount({ label }));
	await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
	await page.getByRole('button', { name: 'Sign in' }).click();
	await expect(page).toHaveURL(`${ORIGIN}/jumps`);
	return { context, page };
}

async function createProfile(page: Page, name: string): Promise<string> {
	const handle = `p${randomBytes(5).toString('hex')}`;
	await page.goto('/profile/public');
	await page.getByLabel('Handle').fill(handle);
	await page.getByLabel('Display name').fill(name);
	await page.getByLabel('Let people find my profile').check();
	await page.getByRole('button', { name: 'Create profile' }).click();
	await expect(page.getByText('Saved.', { exact: true })).toBeVisible();
	return handle;
}

/** A private jump at a new private place with a private note; returns its id. */
async function logJump(page: Page): Promise<string> {
	await page.goto('/jumps/new');
	await page.getByLabel('Place name').fill('Farm strip');
	await page.getByLabel('Country', { exact: true }).selectOption('PT');
	await page.getByRole('button', { name: 'Use this place' }).click();
	await page.getByLabel('Date', { exact: true }).fill('2026-10-10');
	await page.getByLabel('Type', { exact: true }).selectOption('freefly');
	await page.getByLabel('Notes (optional, private)').fill('secret detail');
	await page.getByRole('button', { name: 'Save private jump' }).click();
	await expect(page.getByText('Saved privately.')).toBeVisible();
	return page.url().split('/jumps/')[1].split('?')[0];
}

test.describe('shared jump summaries', () => {
	test('preview, publish to followers, widen to public, withdraw on edit', async ({ browser }) => {
		const tag = randomBytes(3).toString('hex');
		const alex = await newPerson(browser, 'poster');
		const sam = await newPerson(browser, 'reader');
		const alexHandle = await createProfile(alex.page, `Alex ${tag}`);
		await createProfile(sam.page, `Sam ${tag}`);
		const visitor = await (
			await browser.newContext({ baseURL: ORIGIN, ignoreHTTPSErrors: true })
		).newPage();

		const jumpId = await logJump(alex.page);
		await expect(alex.page.getByText('Private: not shared with anyone.')).toBeVisible();
		await alex.page.getByRole('link', { name: 'Share a summary of this jump' }).click();
		// A private place is never shared.
		await expect(alex.page.getByLabel(/Dropzone \(only a listed dropzone/)).toBeDisabled();
		await alex.page.getByLabel(/Caption/).fill(`Sunset load ${tag}`);
		await alex.page.getByLabel('Approved followers, including people you approve later').check();
		await alex.page.getByRole('button', { name: 'Preview' }).click();
		const preview = alex.page.getByRole('article');
		await expect(preview).toContainText('Freefly');
		await expect(preview).toContainText('not published yet');
		await expect(preview).not.toContainText('secret detail');
		await alex.page.getByRole('button', { name: 'Publish' }).click();
		await expect(alex.page.getByText('Published.', { exact: true })).toBeVisible();
		const postHref = await alex.page
			.getByRole('article')
			.getByRole('link', { name: /^Jump on / })
			.getAttribute('href');
		expect(postHref).toMatch(/^\/posts\//);

		// Follower-only: a signed-out visitor sees neither the list entry nor the post.
		await visitor.goto(`/people/${alexHandle}`);
		await expect(visitor.getByText('Nothing shared that you can see.')).toBeVisible();
		expect((await visitor.goto(postHref!))?.status()).toBe(404);

		// Sam is approved and then sees the post shared before the approval.
		await sam.page.goto(`/people/${alexHandle}`);
		await sam.page.getByRole('button', { name: 'Ask to follow' }).click();
		await alex.page.goto('/people');
		await alex.page
			.getByRole('list', { name: 'Follow requests' })
			.getByRole('button', { name: 'Approve' })
			.click();
		await sam.page.goto(`/people/${alexHandle}`);
		await expect(sam.page.getByRole('list', { name: 'Shared jumps' })).toContainText(
			`Sunset load ${tag}`
		);

		// Widened to public: the visitor can read it, never the private note.
		await alex.page.goto(`/jumps/${jumpId}/share`);
		await alex.page.getByLabel('Public', { exact: true }).check();
		await alex.page.getByRole('button', { name: 'Change audience' }).click();
		await expect(alex.page.getByText('Audience changed.')).toBeVisible();
		await visitor.goto(postHref!);
		await expect(visitor.getByText(`Sunset load ${tag}`)).toBeVisible();
		await expect(visitor.locator('#main')).not.toContainText('secret detail');
		await expect(visitor.locator('#main')).not.toContainText('Farm strip');

		// Editing a private note leaves it; editing the shared type withdraws it.
		await alex.page.goto(`/jumps/${jumpId}`);
		await alex.page.getByLabel('Notes (optional, private)').fill('another secret');
		await alex.page.getByRole('button', { name: 'Save changes' }).click();
		await expect(alex.page.getByText('Saved privately.')).toBeVisible();
		expect((await visitor.goto(postHref!))?.status()).toBe(200);
		await alex.page.getByLabel('Type', { exact: true }).selectOption('angle');
		await alex.page.getByRole('button', { name: 'Save changes' }).click();
		await expect(alex.page.getByRole('list', { name: 'History' })).toContainText(
			'Post withdrawn: you changed a value it shared'
		);
		await expect(alex.page.getByText('Private: not shared with anyone.')).toBeVisible();
		expect((await visitor.goto(postHref!))?.status()).toBe(404);
		await expect(visitor.getByText('This page is unavailable.')).toBeVisible();

		await Promise.all([alex.context.close(), sam.context.close(), visitor.context().close()]);
	});
});
