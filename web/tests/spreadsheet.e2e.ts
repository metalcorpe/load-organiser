import { randomUUID } from 'node:crypto';
import { readFile } from 'node:fs/promises';
import { expect, test, type Page } from '@playwright/test';
import { PASSWORD, apiCall, apiSession, createAccount } from './support/accounts.ts';

// Same production-cookie preview as the account tests.
const ORIGIN = 'https://127.0.0.1:4175';
test.use({ baseURL: ORIGIN, ignoreHTTPSErrors: true });

async function signIn(page: Page, email: string, returnTo = '/records') {
	await page.goto(`/sign-in?returnTo=${encodeURIComponent(returnTo)}`);
	await page.getByLabel('Email', { exact: true }).fill(email);
	await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
	await page.getByRole('button', { name: 'Sign in' }).click();
	await expect(page).toHaveURL(`${ORIGIN}${returnTo}`);
}

test.describe('logbook as a spreadsheet', () => {
	test('the download holds the heading row and the jump, with a byte-order mark', async ({ page }) => {
		const email = await createAccount({ label: 'sheet' });
		const bearer = await apiSession(email);
		const place = await apiCall('POST', '/places', { bearer, body: { name: 'Sheet strip', country: 'PT' } });
		expect(place.status).toBe(201);
		const made = await apiCall('POST', '/jumps', {
			bearer,
			body: {
				client_key: randomUUID(),
				place_id: ((await place.json()) as { id: string }).id,
				jumped_on: '2026-10-10',
				jump_type: 'wingsuit',
				jump_number: 42,
				aircraft: 'Cessna 208',
				notes: '=not a formula, really'
			}
		});
		expect(made.status).toBe(201);

		await signIn(page, email);
		const pending = page.waitForEvent('download');
		await page.getByRole('button', { name: 'Download as spreadsheet (CSV)' }).click();
		const file = await pending;
		expect(file.suggestedFilename()).toMatch(/^load-organiser-logbook-\d{4}-\d{2}-\d{2}\.csv$/);
		const bytes = await readFile(await file.path());
		expect([...bytes.subarray(0, 3)]).toEqual([0xef, 0xbb, 0xbf]);
		const [heading, row] = bytes.toString('utf8').slice(1).split('\r\n');
		expect(heading).toBe(
			'Date,Jump number,Place,Country,Type,Aircraft,Exit altitude,Altitude unit,Deployment altitude,Freefall seconds,Notes,Gear'
		);
		expect(row).toBe(`2026-10-10,42,Sheet strip,PT,Wingsuit,Cessna 208,,,,,"'=not a formula, really",`);

		// A reversed range is explained on the page, keeping the dates.
		await page.goto('/records');
		await page.getByLabel('From (optional)').fill('2026-10-02');
		await page.getByLabel('Until (optional)').fill('2026-10-01');
		await page.getByRole('button', { name: 'Download as spreadsheet (CSV)' }).click();
		await expect(page.getByRole('alert')).toHaveText(
			'The "from" date must be on or before the "until" date.'
		);
		await expect(page.getByLabel('From (optional)')).toHaveValue('2026-10-02');
	});
});
