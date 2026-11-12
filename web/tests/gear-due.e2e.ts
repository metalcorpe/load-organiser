import { randomUUID } from 'node:crypto';
import { expect, test, type Page } from '@playwright/test';
import { PASSWORD, apiCall, apiSession, createAccount } from './support/accounts.ts';

// Same production-cookie preview as the account tests.
const ORIGIN = 'https://127.0.0.1:4175';
test.use({ baseURL: ORIGIN, ignoreHTTPSErrors: true });

async function signIn(page: Page, email: string, returnTo: string) {
	await page.goto(`/sign-in?returnTo=${encodeURIComponent(returnTo)}`);
	await page.getByLabel('Email', { exact: true }).fill(email);
	await page.getByLabel('Password', { exact: true }).fill(PASSWORD);
	await page.getByRole('button', { name: 'Sign in' }).click();
	await expect(page).toHaveURL(`${ORIGIN}${returnTo}`);
}

const pad = (n: number) => String(n).padStart(2, '0');
/** The local calendar day `offset` days from today, as YYYY-MM-DD (browser and test share a clock). */
function day(offset: number): string {
	const d = new Date();
	d.setDate(d.getDate() + offset);
	return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

async function component(bearer: string, kind: string, label: string): Promise<string> {
	const made = await apiCall('POST', '/gear/components', {
		bearer,
		body: { client_key: randomUUID(), kind, label }
	});
	expect(made.status).toBe(201);
	return ((await made.json()) as { component: { id: string } }).component.id;
}

async function service(bearer: string, id: string, body: Record<string, unknown>) {
	const made = await apiCall('POST', `/gear/components/${id}/service`, {
		bearer,
		body: { client_key: randomUUID(), ...body }
	});
	expect(made.status).toBe(201);
}

test.describe('gear due dates', () => {
	test('a reserve repacked 175 days ago is due in 5 days, on the logbook and on Gear', async ({
		page
	}) => {
		const email = await createAccount({ label: 'due' });
		const bearer = await apiSession(email);
		const reserve = await component(bearer, 'reserve', 'PD 160 reserve');
		await service(bearer, reserve, { kind: 'repack', done_on: day(-175) });

		await signIn(page, email, '/jumps');
		const due = page.getByRole('list', { name: 'Due soon' });
		await expect(due).toContainText('Reserve repack due in 5 days');
		await due.getByRole('link', { name: 'PD 160 reserve' }).click();
		await expect(page).toHaveURL(`${ORIGIN}/gear/${reserve}`);
		await expect(page.getByRole('list', { name: 'Due dates' })).toContainText(
			"180 days (USPA / FAA 14 CFR 105.43; your country's rule may differ)"
		);

		// A filtered logbook shows none of the home cards.
		await page.goto('/jumps?type=belly');
		await expect(page.getByRole('list', { name: 'Due soon' })).toHaveCount(0);

		// The owner's own interval replaces the default.
		await page.goto(`/gear/${reserve}`);
		await page.getByLabel('Repack interval in days (optional)').fill('200');
		await page.getByRole('button', { name: 'Save changes' }).click();
		await expect(page.getByText('Saved privately.')).toBeVisible();
		await page.goto('/gear');
		const all = page.getByRole('list', { name: 'Due dates' });
		await expect(all).toContainText('Reserve repack due in 25 days');
		await expect(all).toContainText('Your interval of 200 days after your last recorded repack.');
	});

	test('an entered AAD date that has passed says overdue plainly; later dates stay off the logbook', async ({
		page
	}) => {
		const email = await createAccount({ label: 'overdue' });
		const bearer = await apiSession(email);
		const aad = await component(bearer, 'aad', 'Cypres 2');
		await service(bearer, aad, { kind: 'aad_service', done_on: day(-400), due_on: day(-2) });
		const spare = await component(bearer, 'reserve', 'Spare reserve');
		await service(bearer, spare, { kind: 'repack', done_on: day(-10) });

		await signIn(page, email, '/jumps');
		const due = page.getByRole('list', { name: 'Due soon' });
		const since = new Intl.DateTimeFormat('en-GB', {
			day: 'numeric',
			month: 'long',
			timeZone: 'UTC'
		}).format(new Date(`${day(-1)}T00:00:00Z`));
		await expect(due).toContainText(`AAD maintenance overdue since ${since}`);
		await expect(due).not.toContainText('Spare reserve');

		await page.goto('/gear');
		await expect(page.getByRole('list', { name: 'Due dates' })).toContainText(
			'Reserve repack due in 170 days'
		);
	});
});
