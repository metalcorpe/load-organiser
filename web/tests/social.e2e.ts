import { expect, test, type Browser, type Page } from '@playwright/test';
import { randomBytes } from 'node:crypto';
import { PASSWORD, createAccount } from './support/accounts.ts';

// Same production-cookie preview as the account tests.
const ORIGIN = 'https://127.0.0.1:4175';
test.use({ baseURL: ORIGIN, ignoreHTTPSErrors: true });

async function signIn(page: Page, email: string, password = PASSWORD, returnTo = '/people') {
	await page.goto(`/sign-in?returnTo=${encodeURIComponent(returnTo)}`);
	await page.getByLabel('Email', { exact: true }).fill(email);
	await page.getByLabel('Password', { exact: true }).fill(password);
	await page.getByRole('button', { name: 'Sign in' }).click();
	await expect(page).toHaveURL(`${ORIGIN}${returnTo}`);
}

async function newPerson(browser: Browser, label: string) {
	const context = await browser.newContext({ baseURL: ORIGIN, ignoreHTTPSErrors: true });
	const page = await context.newPage();
	await signIn(page, await createAccount({ label }));
	return { context, page };
}

async function createProfile(page: Page, name: string, discoverable: boolean): Promise<string> {
	const handle = `e${randomBytes(5).toString('hex')}`;
	await page.goto('/profile/public');
	await page.getByLabel('Handle').fill(handle);
	await page.getByLabel('Display name').fill(name);
	await page.getByLabel('Belly / formation').check();
	if (discoverable) await page.getByLabel('Let people find my profile').check();
	await page.getByRole('button', { name: 'Create profile' }).click();
	await expect(page.getByText('Saved.', { exact: true })).toBeVisible();
	return handle;
}

test.describe('profiles and follows', () => {
	test('invite a jump buddy: link, join, create a profile, back to follow', async ({ browser }) => {
		const inviter = await newPerson(browser, 'inviter');
		const handle = await createProfile(inviter.page, 'Invite Sender', true);
		await inviter.page.goto('/people');
		const link = `${ORIGIN}/people/${handle}`;
		await expect(inviter.page.getByRole('link', { name: link })).toBeVisible();
		await expect(inviter.page.getByRole('button', { name: 'Invite jump buddies' })).toBeVisible();

		// A guest opening the link is offered to join, and comes back to this profile.
		const guest = await browser.newContext({ baseURL: ORIGIN, ignoreHTTPSErrors: true });
		const guestPage = await guest.newPage();
		await guestPage.goto(link);
		await expect(guestPage.getByRole('heading', { name: 'Follow Invite Sender' })).toBeVisible();
		await expect(guestPage.getByRole('link', { name: 'Join to follow' })).toHaveAttribute(
			'href',
			`/register?returnTo=${encodeURIComponent(`/people/${handle}`)}`
		);
		await guest.close();

		// A member without a profile creates one and lands back here, ready to follow.
		const friend = await newPerson(browser, 'invitee');
		await friend.page.goto(`/people/${handle}`);
		await friend.page.getByRole('link', { name: 'Create your profile' }).click();
		await friend.page.getByLabel('Handle').fill(`f${randomBytes(5).toString('hex')}`);
		await friend.page.getByLabel('Display name').fill('Invited Friend');
		await friend.page.getByRole('button', { name: 'Create profile' }).click();
		await expect(friend.page).toHaveURL(`${ORIGIN}/people/${handle}`);
		await friend.page.getByRole('button', { name: 'Ask to follow' }).click();
		await expect(friend.page.getByText('Requested; waiting for approval.')).toBeVisible();

		await inviter.context.close();
		await friend.context.close();
	});

	test('a search refusal never moves focus, then or on a later load', async ({ browser }) => {
		const { context, page } = await newPerson(browser, 'searchfocus');
		await page.goto('/people');
		await expect(page.locator('html[data-form-guard="ready"]')).toHaveCount(1);
		await page.getByLabel('Find people by handle or name').fill('a');
		await page.getByRole('button', { name: 'Search' }).click();
		const alert = page.getByRole('alert');
		await expect(alert).toBeVisible();
		await expect(alert).not.toBeFocused();
		// The same refusal is on the page again after a reload: still an ordinary visit.
		await page.reload();
		await expect(page.locator('html[data-form-guard="ready"]')).toHaveCount(1);
		await expect(page.getByRole('alert')).toBeVisible();
		await expect(page.getByRole('alert')).not.toBeFocused();
		await context.close();
	});

	test('a refused field is marked invalid, described by the error and focused', async ({ browser }) => {
		const { context, page } = await newPerson(browser, 'fielderror');
		await page.goto('/profile/public');
		await expect(page.locator('html[data-form-guard="ready"]')).toHaveCount(1);
		await page.getByLabel('Handle').fill('Not valid!');
		await page.getByLabel('Display name').fill('Field Error');
		await page.getByRole('button', { name: 'Create profile' }).click();

		const alert = page.getByRole('alert');
		await expect(alert).toBeVisible();
		const handle = page.getByLabel('Handle');
		await expect(handle).toBeFocused();
		await expect(handle).toHaveAttribute('aria-invalid', 'true');
		const id = await alert.getAttribute('id');
		expect(id).toBeTruthy();
		await expect(handle).toHaveAttribute('aria-describedby', new RegExp(`(^| )${id}( |$)`));
		// The accessible description is the error text itself.
		await expect(handle).toHaveAccessibleDescription((await alert.textContent())!.trim());
		// Typing a new value clears the invalid mark.
		await handle.fill('better_handle');
		await expect(handle).not.toHaveAttribute('aria-invalid', 'true');
		await context.close();
	});

	test('find, ask to follow, approve, then block', async ({ browser }) => {
		const tag = randomBytes(3).toString('hex');
		const alex = await newPerson(browser, 'alex');
		const sam = await newPerson(browser, 'sam');
		const alexHandle = await createProfile(alex.page, `Alex ${tag}`, true);
		const samHandle = await createProfile(sam.page, `Sam ${tag}`, false);

		// Sam finds Alex (discoverable); Alex cannot find Sam (not discoverable).
		await sam.page.goto(`/people?q=${tag}`);
		const results = sam.page.getByRole('list', { name: 'Search results' });
		await expect(results).toContainText(`Alex ${tag}`);
		await expect(results).not.toContainText(`Sam ${tag}`);
		await alex.page.goto(`/people?q=${tag}`);
		await expect(alex.page.getByText('No discoverable profile matches.')).toBeVisible();

		await sam.page.getByRole('link', { name: `Alex ${tag}` }).click();
		await expect(sam.page).toHaveURL(`${ORIGIN}/people/${alexHandle}`);
		await expect(sam.page.getByText('Belly / formation')).toBeVisible();
		await sam.page.getByRole('button', { name: 'Ask to follow' }).click();
		await expect(sam.page.getByText('Requested; waiting for approval.')).toBeVisible();

		await alex.page.goto('/people');
		const requests = alex.page.getByRole('list', { name: 'Follow requests' });
		await expect(requests).toContainText(`@${samHandle}`);
		await requests.getByRole('button', { name: 'Approve' }).click();
		await expect(alex.page.getByRole('list', { name: 'Followers' })).toContainText(`@${samHandle}`);
		await sam.page.reload();
		await expect(sam.page.getByText('Following.', { exact: true })).toBeVisible();

		// Alex blocks Sam from the followers list (Sam's profile is not discoverable).
		const followers = alex.page.getByRole('list', { name: 'Followers' });
		await followers.getByText(`Block @${samHandle}`).first().click();
		await followers.getByLabel(`Block @${samHandle}`).check();
		await followers.getByRole('button', { name: 'Block', exact: true }).click();
		await expect(alex.page).toHaveURL(`${ORIGIN}/people?blocked=1`);
		await expect(alex.page.getByRole('list', { name: 'Blocked' })).toContainText(`@${samHandle}`);
		await expect(alex.page.getByText('No followers yet.')).toBeVisible();

		// Signed in, Sam no longer sees Alex; anyone signed out still does.
		const blocked = await sam.page.goto(`/people/${alexHandle}`);
		expect(blocked?.status()).toBe(404);
		// The same page as for any missing address: nothing says why.
		await expect(sam.page.getByText('This page is unavailable.')).toBeVisible();
		const anonymous = await browser.newContext({ baseURL: ORIGIN, ignoreHTTPSErrors: true });
		const visitor = await anonymous.newPage();
		await visitor.goto(`/people/${alexHandle}`);
		await expect(visitor.getByRole('heading', { name: `Alex ${tag}`, exact: true })).toBeVisible();
		await expect(visitor.locator('#main').getByRole('link', { name: 'Sign in' })).toBeVisible();
		// A profile that is not discoverable is unavailable to visitors.
		expect((await visitor.goto(`/people/${samHandle}`))?.status()).toBe(404);

		await Promise.all([alex.context.close(), sam.context.close(), anonymous.close()]);
	});

	test('a report reaches the reviewer, who can hide the profile', async ({ browser }) => {
		const tag = randomBytes(3).toString('hex');
		const target = await newPerson(browser, 'target');
		const reporter = await newPerson(browser, 'reporter');
		const handle = await createProfile(target.page, `Official ${tag}`, true);
		await createProfile(reporter.page, `Reporter ${tag}`, false);

		await reporter.page.goto(`/people/${handle}`);
		await reporter.page.getByLabel('Report this profile').selectOption('impersonation');
		await reporter.page.getByLabel('What is wrong (optional)').fill('Claims to be the DZ.');
		await reporter.page.getByRole('button', { name: 'Send report' }).click();
		await expect(reporter.page.getByText('Report received.')).toBeVisible();

		const review = await browser.newContext({ baseURL: ORIGIN, ignoreHTTPSErrors: true });
		const reviewer = await review.newPage();
		await signIn(
			reviewer,
			process.env.E2E_REVIEWER_EMAIL ?? '',
			process.env.E2E_REVIEWER_PASSWORD ?? '',
			'/review/social'
		);
		const item = reviewer.getByRole('listitem').filter({ hasText: `@${handle}` });
		await expect(item).toContainText('Claims to be the DZ.');
		await item.getByLabel('Decision').selectOption('hide_profile');
		await item.getByLabel(/Reason \(shown to the profile owner/).fill('Impersonates a dropzone.');
		await item.getByRole('button', { name: 'Record decision' }).click();
		await expect(item).toHaveCount(0);

		expect((await reporter.page.goto(`/people/${handle}`))?.status()).toBe(404);
		await target.page.goto('/profile/public');
		await expect(target.page.getByRole('alert')).toContainText('Impersonates a dropzone.');
		await expect(target.page.getByRole('alert')).not.toContainText('Reporter');

		await Promise.all([target.context.close(), reporter.context.close(), review.close()]);
	});
});
