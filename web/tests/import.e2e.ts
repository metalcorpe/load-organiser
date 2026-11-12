import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import { randomBytes, randomUUID } from 'node:crypto';
import {
	PASSWORD,
	apiCall,
	apiSession,
	createAccount,
	reviewerSession
} from './support/accounts.ts';

// Same production-cookie preview as the account tests.
const ORIGIN = 'https://127.0.0.1:4175';
test.use({ baseURL: ORIGIN, ignoreHTTPSErrors: true });

async function signIn(page: Page, email: string, returnTo = '/jumps') {
	await page.goto(`/sign-in?returnTo=${encodeURIComponent(returnTo)}`);
	await page.getByLabel('Email', { exact: true }).fill(email);
	await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
	await page.getByRole('button', { name: 'Sign in' }).click();
	await expect(page).toHaveURL(`${ORIGIN}${returnTo}`);
}

test('import a spreadsheet, see the jumps in the logbook, then undo it', async ({ page }) => {
	const venue = `Im${randomBytes(5).toString('hex')} Skydive`;
	const created = await apiCall('POST', '/directory/venues', {
		bearer: await reviewerSession(),
		body: {
			name: venue,
			country: 'ES',
			source_url: 'https://example.org/dz',
			checked_on: '2026-11-01'
		}
	});
	expect(created.status).toBe(201);
	const email = await createAccount({ label: 'import' });
	await signIn(page, email);

	// An empty logbook points to the import.
	await page.getByRole('link', { name: 'Import a spreadsheet' }).click();
	await expect(page).toHaveURL(`${ORIGIN}/records/import`);
	await expect(page.getByRole('heading', { name: 'Import from a spreadsheet' })).toBeVisible();

	// Jump 7 is already in the logbook, so its row is a likely duplicate.
	const logged = await apiCall('POST', '/jumps', {
		bearer: await apiSession(email),
		body: {
			client_key: randomUUID(),
			jumped_on: '2024-03-01',
			jump_type: 'belly',
			venue_id: (await created.json()).id,
			jump_number: 7
		}
	});
	expect(logged.status).toBe(201);

	const file = {
		name: 'logbook.csv',
		mimeType: 'text/csv',
		buffer: Buffer.from(
			[
				'Date;Jump #;Dropzone;Type;Altitude;Notes',
				`12/03/2024;5;${venue.toLowerCase()};FS;13500;Listed row`,
				'13/03/2024;6;Olive grove;freefly;;New place row',
				'31/02/2024;8;Olive grove;;;Problem row',
				`14/03/2024;7;${venue};;;Duplicate row`
			].join('\r\n')
		)
	};
	await page.getByLabel('Spreadsheet file (CSV)').setInputFiles(file);
	await page.getByLabel('Country for places not in the directory').selectOption('PT');
	await page.getByRole('button', { name: 'Check file' }).click();

	await expect(page.getByRole('heading', { name: 'Ready to import' })).toBeVisible();
	await expect(page.getByRole('status').filter({ hasText: 'rows read' })).toContainText(
		'4 rows read: 2 jumps to import, 2 skipped.'
	);
	await expect(page.getByText('Olive grove', { exact: true })).toBeVisible();
	const first = page.getByRole('list', { name: 'First rows to import' });
	await expect(first).toContainText(`Belly / formation · ${venue} (listed dropzone)`);
	await expect(first).toContainText('Freefly · Olive grove (new private place)');
	const skipped = page.getByRole('list', { name: 'Skipped rows' });
	await expect(skipped).toContainText('Row 3: the date is not a real date in the chosen order.');
	await expect(skipped).toContainText('Row 4: it looks like a jump already in your logbook.');
	await expect(page.getByLabel('Dropzone or place')).toHaveValue('2');

	// The preview passes the same automated accessibility checks as every page.
	const axe = await new AxeBuilder({ page })
		.withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
		.analyze();
	expect(axe.violations.map((v) => v.id)).toEqual([]);

	await page.getByLabel('Choose the same file again').setInputFiles(file);
	await page.getByRole('button', { name: 'Import 2 jumps' }).click();
	await expect(page.getByRole('heading', { name: 'Imported', exact: true })).toBeVisible();
	await expect(
		page.getByText('Imported 2 jumps, 1 new private place, 2 rows skipped.')
	).toBeVisible();

	await page.getByRole('link', { name: 'Open your logbook' }).click();
	await expect(page.getByText('3 jumps recorded here.', { exact: false })).toBeVisible();
	const jumps = page.getByRole('list', { name: 'Jumps' });
	await expect(jumps).toContainText('Freefly · Olive grove (private place)');
	await jumps.getByRole('link', { name: /#5/ }).click();
	await expect(page.getByText('imported by you, not verified')).toBeVisible();

	// Undo removes the imported jumps and the place nothing else uses.
	await page.goto('/records/import');
	const imports = page.getByRole('list', { name: 'Your imports' });
	await imports.getByRole('button', { name: /^Undo the import of .* UTC$/ }).click();
	await expect(imports.getByRole('alert')).toContainText('Tick the box to confirm');
	await page.getByLabel(/^Delete the 2 jumps from the import of .* UTC$/).check();
	await page.getByRole('button', { name: /^Undo the import of .* UTC$/ }).click();
	await expect(page.getByRole('heading', { name: 'Import undone' })).toBeVisible();
	await expect(page.getByText('Removed 2 jumps and 1 private place.', { exact: true })).toBeVisible();
	await expect(page.getByRole('list', { name: 'Your imports' })).toContainText('Undone on');

	await page.goto('/jumps');
	await expect(page.getByText('1 jump recorded here.', { exact: false })).toBeVisible();
	await expect(page.getByRole('list', { name: 'Jumps' })).not.toContainText('Olive grove');
});
