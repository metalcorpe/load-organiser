import { expect, test, type Page } from '@playwright/test';
import { readFile } from 'node:fs/promises';
import { PASSWORD, createAccount } from './support/accounts.ts';
import { openJumpSections } from './support/jump-form.ts';

// Same production-cookie preview as the account tests.
const ORIGIN = 'https://127.0.0.1:4175';
test.use({ baseURL: ORIGIN, ignoreHTTPSErrors: true });

async function signIn(page: Page, email: string, returnTo = '/profile/data') {
	await page.goto(`/sign-in?returnTo=${encodeURIComponent(returnTo)}`);
	await page.getByLabel('Email', { exact: true }).fill(email);
	await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
	await page.getByRole('button', { name: 'Sign in' }).click();
	await expect(page).toHaveURL(`${ORIGIN}${returnTo}`);
}

async function logJump(page: Page) {
	await page.goto('/jumps/new');
	await page.getByLabel('Place name').fill('Farm strip');
	await page.getByLabel('Country', { exact: true }).selectOption('PT');
	await page.getByRole('button', { name: 'Use this place' }).click();
	await page.getByLabel('Date', { exact: true }).fill('2026-10-10');
	await page.getByLabel('Type', { exact: true }).selectOption('wingsuit');
	await openJumpSections(page);
	await page.getByLabel('Notes (optional, private)').fill('Exported note.');
	await page.getByRole('button', { name: 'Save private jump' }).first().click();
	await expect(page.getByText('Saved privately.')).toBeVisible();
}

async function download(page: Page): Promise<{ path: string; name: string; text: string }> {
	await page.goto('/profile/data');
	const pending = page.waitForEvent('download');
	await page.getByRole('button', { name: 'Download export' }).click();
	const file = await pending;
	const path = await file.path();
	return { path, name: file.suggestedFilename(), text: await readFile(path, 'utf8') };
}

test.describe('your data', () => {
	test('export, check and restore into an empty account; a repeat changes nothing', async ({
		page,
		browser
	}) => {
		await signIn(page, await createAccount({ label: 'export' }), '/jumps');
		await logJump(page);
		const exported = await download(page);
		expect(exported.name).toMatch(/^load-organiser-records-\d{4}-\d{2}-\d{2}\.json$/);
		const archive = JSON.parse(exported.text);
		expect(archive.format).toBe('load-organiser.personal-records');
		expect(archive.records.jumps[0].notes).toBe('Exported note.');
		expect(exported.text).not.toContain('@example');

		// A different, empty account restores it.
		const other = await browser.newContext({ baseURL: ORIGIN, ignoreHTTPSErrors: true });
		const target = await other.newPage();
		await signIn(target, await createAccount({ label: 'restore' }));
		await expect(target.getByText('You hold: no records.')).toBeVisible();
		await target.getByLabel('Export file to check').setInputFiles(exported.path);
		await target.getByRole('button', { name: 'Check file' }).click();
		await expect(target.getByRole('heading', { name: 'Ready to restore' })).toBeVisible();
		await expect(target.getByText('1 jump, 1 private place')).toBeVisible();

		await target.getByLabel('Export file to restore').setInputFiles(exported.path);
		await target.getByLabel('Password', { exact: true }).fill(PASSWORD);
		await target.getByRole('button', { name: 'Restore into empty records' }).click();
		await expect(target.getByRole('heading', { name: 'Restored' })).toBeVisible();
		await expect(target.getByText('Restored 1 jump, 1 private place.')).toBeVisible();

		await target.goto('/jumps');
		await expect(target.getByText('1 jump recorded here.', { exact: false })).toBeVisible();
		await target.getByRole('list', { name: 'Jumps' }).getByRole('link').first().click();
		await expect(target.getByText('restored from your export, not verified')).toBeVisible();

		// The exact same file again: already restored, nothing applied twice.
		await target.goto('/profile/data');
		await target.getByLabel('Export file to restore').setInputFiles(exported.path);
		await target.getByLabel('Password', { exact: true }).fill(PASSWORD);
		await target.getByRole('button', { name: 'Restore into empty records' }).click();
		await expect(target.getByRole('heading', { name: 'Already restored' })).toBeVisible();
		await target.goto('/jumps');
		await expect(target.getByText('1 jump recorded here.', { exact: false })).toBeVisible();
		await other.close();

		// The source account is not empty: its own file is refused, nothing changes.
		await page.goto('/profile/data');
		await page.getByLabel('Export file to restore').setInputFiles(exported.path);
		await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
		await page.getByRole('button', { name: 'Restore into empty records' }).click();
		await expect(page.getByRole('alert')).toContainText('Restore only works into empty records');
		await expect(page.getByRole('alert')).not.toContainText('delete');
	});

	test('a file that is not an export is refused without changes', async ({ page }) => {
		await signIn(page, await createAccount({ label: 'badfile' }));
		await page.getByLabel('Export file to check').setInputFiles({
			name: 'notes.json',
			mimeType: 'application/json',
			buffer: Buffer.from('hello')
		});
		await page.getByRole('button', { name: 'Check file' }).click();
		await expect(page.getByRole('alert')).toContainText('not a Load Organiser export');
		await page.getByLabel('Export file to restore').setInputFiles({
			name: 'edited.json',
			mimeType: 'application/json',
			buffer: Buffer.from(
				JSON.stringify({
					format: 'load-organiser.personal-records',
					version: 1,
					exported_at: '2026-11-01T10:00:00Z',
					records: { roles: ['reviewer'] },
					references: { venues: [], listings: [] }
				})
			)
		});
		await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
		await page.getByRole('button', { name: 'Restore into empty records' }).click();
		await expect(page.getByRole('alert')).toContainText('does not pass the checks');
		await expect(page.getByText('You hold: no records.')).toBeVisible();
	});
});
