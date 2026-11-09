import { randomBytes } from 'node:crypto';
import { expect, test, type Page } from '@playwright/test';
import { PASSWORD, createAccount } from './support/accounts.ts';

// Privacy page and beta feedback (#162) on the production-cookie preview.
const ORIGIN = 'https://127.0.0.1:4175';
test.use({ baseURL: ORIGIN, ignoreHTTPSErrors: true });

async function signIn(page: Page, email: string, password: string, returnTo: string) {
	await page.goto(`/sign-in?returnTo=${encodeURIComponent(returnTo)}`);
	await page.getByLabel('Email', { exact: true }).fill(email);
	await page.getByLabel('Password', { exact: true }).fill(password);
	await page.getByRole('button', { name: 'Sign in' }).click();
	await expect(page).toHaveURL(`${ORIGIN}${returnTo}`);
}

test.describe('privacy and feedback', () => {
	test('a visitor reaches the privacy page from the footer and is asked to sign in for feedback', async ({
		page
	}) => {
		await page.goto('/');
		await page.getByRole('contentinfo').getByRole('link', { name: 'Privacy and the beta' }).click();
		await expect(page).toHaveURL(`${ORIGIN}/privacy`);
		await expect(
			page.getByRole('heading', { level: 1, name: 'Privacy and the beta' })
		).toBeVisible();
		for (const section of ['Private by default', 'Deleting your account', 'Backups and recovery']) {
			await expect(page.getByRole('heading', { level: 2, name: section })).toBeVisible();
		}
		await page.getByRole('link', { name: 'send feedback about the beta' }).click();
		await expect(page).toHaveURL(`${ORIGIN}/sign-in?returnTo=%2Fsubmit%3Fkind%3Dfeedback`);
	});

	test('a member sends feedback and a reviewer sees it without the sender', async ({
		page,
		browser
	}) => {
		const note = `Feedback ${randomBytes(4).toString('hex')}: the save button is hard to find.`;
		const email = await createAccount({ label: 'feedback' });
		await signIn(page, email, PASSWORD, '/profile');
		await page.getByRole('link', { name: 'Send feedback' }).click();
		await expect(page).toHaveURL(`${ORIGIN}/submit?kind=feedback`);
		await expect(page.getByLabel('Feedback about the beta')).toBeChecked();
		await page.getByLabel('Details').fill(note);
		await page.getByRole('button', { name: 'Send' }).click();
		await expect(page.getByText('Sent. You can follow its status below.')).toBeVisible();
		const mine = page
			.getByRole('list', { name: 'Your submissions' })
			.getByRole('listitem')
			.filter({ hasText: note });
		await expect(mine).toContainText('Feedback about the beta');
		await expect(mine).toContainText('Waiting for review');

		const reviewer = await (
			await browser.newContext({ baseURL: ORIGIN, ignoreHTTPSErrors: true })
		).newPage();
		const reviewerEmail = process.env.E2E_REVIEWER_EMAIL;
		const reviewerPassword = process.env.E2E_REVIEWER_PASSWORD;
		if (!reviewerEmail || !reviewerPassword)
			throw new Error('E2E_REVIEWER_EMAIL/PASSWORD must be set');
		await signIn(reviewer, reviewerEmail, reviewerPassword, '/review/submissions');
		const item = reviewer.getByRole('listitem').filter({ hasText: note });
		await expect(item).toContainText('Beta feedback');
		await expect(item).not.toContainText(email);
		await reviewer.context().close();
	});
});

test('a visitor reaches the support page from the footer; it shows costs and the outside link', async ({
	page
}) => {
	await page.goto('/');
	await page.getByRole('contentinfo').getByRole('link', { name: 'Support the beta' }).click();
	await expect(page).toHaveURL(`${ORIGIN}/support`);
	await expect(page.getByRole('heading', { level: 1, name: 'Support the beta' })).toBeVisible();
	await expect(page.getByRole('heading', { level: 2, name: 'Running costs' })).toBeVisible();
	await expect(page.getByTestId('no-costs')).toContainText('Nothing is paid for yet');
	const link = page.getByRole('link', { name: 'support Load Organiser on Ko-fi' });
	await expect(link).toHaveAttribute('href', 'https://ko-fi.com/tavaninja');
	await expect(link).toHaveAttribute('rel', /noopener/);
});
