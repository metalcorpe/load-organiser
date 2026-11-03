import { expect, test, type Page } from '@playwright/test';
import { PASSWORD, createAccount } from './support/accounts.ts';

// Same production-cookie preview as the account tests.
const ORIGIN = 'https://127.0.0.1:4175';
test.use({ baseURL: ORIGIN, ignoreHTTPSErrors: true });

async function signIn(page: Page, email: string, returnTo = '/gear') {
	await page.goto(`/sign-in?returnTo=${encodeURIComponent(returnTo)}`);
	await page.getByLabel('Email', { exact: true }).fill(email);
	await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
	await page.getByRole('button', { name: 'Sign in' }).click();
	await expect(page).toHaveURL(`${ORIGIN}${returnTo}`);
}

async function addReserve(page: Page): Promise<string> {
	await page.goto('/gear/new');
	await page.getByLabel('Type', { exact: true }).selectOption('reserve');
	await page.getByLabel('Label', { exact: true }).fill('PD Optimum 176');
	await page.getByLabel('Serial number (optional, private)').fill('0042-ab/7');
	await page.getByLabel('Manufactured (optional)').fill('2019-04');
	await page.getByRole('button', { name: 'Save component' }).click();
	await expect(page.getByText('Saved privately.')).toBeVisible();
	return page.url().split('/gear/')[1].split('?')[0];
}

test.describe('private gear', () => {
	test('record a reserve, assemble a rig and log a repack', async ({ page }) => {
		await signIn(page, await createAccount({ label: 'gear' }));
		const id = await addReserve(page);
		await expect(page.getByLabel('Serial number (optional, private)')).toHaveValue('0042-ab/7');
		await expect(page.getByText('Stored as month only.')).toBeVisible();
		await expect(page.getByText('entered by you, not verified')).toBeVisible();

		await page.goto('/gear');
		await page.getByLabel('New rig name').fill('Main rig');
		await page.getByRole('button', { name: 'Add rig' }).click();
		await expect(page.getByText('Rig added.')).toBeVisible();

		await page.goto(`/gear/${id}`);
		await page.getByLabel('Move to').selectOption({ label: 'Main rig' });
		await page.getByLabel('From', { exact: true }).fill('2026-03-01');
		await page.getByRole('button', { name: 'Update rig' }).click();
		await expect(page.getByText('Rig updated.')).toBeVisible();
		await expect(page.getByText('In Main rig since 1 March 2026.')).toBeVisible();

		await page.getByLabel('Service', { exact: true }).selectOption('repack');
		await page.getByLabel('Done on', { exact: true }).fill('2026-10-01');
		await page.getByLabel('Next due (optional)').fill('2027-04-01');
		await page.getByRole('button', { name: 'Add service entry' }).click();
		await expect(page.getByText('Service entry saved.')).toBeVisible();
		await expect(page.getByText('Repack on 1 October 2026')).toBeVisible();

		await page.goto('/gear');
		const item = page.getByRole('list', { name: 'Components' }).getByRole('listitem');
		await expect(item).toContainText('PD Optimum 176');
		await expect(item).toContainText('In Main rig since 1 March 2026');
		await expect(item).toContainText('Next due you entered: 1 April 2027');
	});

	test('gear is invisible to other accounts', async ({ page, browser }) => {
		await signIn(page, await createAccount({ label: 'owner' }));
		const id = await addReserve(page);
		const other = await browser.newContext({ baseURL: ORIGIN, ignoreHTTPSErrors: true });
		const otherPage = await other.newPage();
		await signIn(otherPage, await createAccount({ label: 'other' }));
		await expect(otherPage.getByText('No components yet.')).toBeVisible();
		const response = await otherPage.goto(`/gear/${id}`);
		expect(response?.status()).toBe(404);
		await expect(otherPage.getByText('0042-ab/7')).toHaveCount(0);
		await other.close();
	});

	test('an edit from an older tab is refused, not overwritten', async ({ page, context }) => {
		await signIn(page, await createAccount({ label: 'tabs' }));
		const id = await addReserve(page);
		const second = await context.newPage();
		await second.goto(`/gear/${id}`);

		await page.goto(`/gear/${id}`);
		await page.getByLabel('Model (optional)').fill('Optimum');
		await page.getByRole('button', { name: 'Save changes' }).click();
		await expect(page.getByText('Saved privately.')).toBeVisible();

		await second.getByLabel('Model (optional)').fill('Something else');
		await second.getByRole('button', { name: 'Save changes' }).click();
		await expect(second.getByRole('alert')).toContainText('changed since you opened it');
		await page.reload();
		await expect(page.getByLabel('Model (optional)')).toHaveValue('Optimum');
	});
});
