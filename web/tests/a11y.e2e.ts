import AxeBuilder from '@axe-core/playwright';
import { randomBytes, randomUUID } from 'node:crypto';
import { expect, test, type Page } from '@playwright/test';
import {
	PASSWORD,
	apiCall,
	apiSession,
	createAccount,
	reviewerCredentials,
	reviewerSession
} from './support/accounts.ts';

// Automated WCAG 2.2 A/AA checks with axe on every page, in light and dark.
// axe finds roughly a third to a half of accessibility problems; it does not replace
// the screen-reader and keyboard checks recorded in docs/product/beta-evidence.md.
const ORIGIN = 'https://127.0.0.1:4175';
test.use({ baseURL: ORIGIN, ignoreHTTPSErrors: true });

const TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];
const SOURCE = { source_url: 'https://example.org/a11y', checked_on: '2026-11-01' };

async function created(path: string, bearer: string, body: unknown): Promise<Record<string, any>> {
	const response = await apiCall('POST', path, { bearer, body });
	expect(response.status, `${path}: ${await response.clone().text()}`).toBeLessThan(300);
	return (await response.json()) as Record<string, any>;
}

/** The UTC calendar day `offset` days from today, as YYYY-MM-DD. */
function daysFromToday(offset: number): string {
	return new Date(Date.now() + offset * 86_400_000).toISOString().slice(0, 10);
}

interface World {
	member: string;
	paths: { guest: string[]; member: string[]; reviewer: string[] };
}

/** One member with one of each record, a public post, and a published listing. */
async function world(): Promise<World> {
	const reviewer = await reviewerSession();
	const tag = randomBytes(4).toString('hex');
	const venue = await created('/directory/venues', reviewer, {
		name: `Axe Field ${tag}`,
		country: 'PT',
		...SOURCE
	});
	const provider = await created('/directory/providers', reviewer, {
		name: `Axe Org ${tag}`,
		kind: 'organization',
		...SOURCE,
		publish: true
	});
	const listing = await created('/directory/opportunities', reviewer, {
		title: `Axe Boogie ${tag}`,
		category: 'boogie',
		provider_id: provider.id,
		venue_id: venue.id,
		country: 'PT',
		starts_on: '2027-07-10',
		ends_on: '2027-07-14',
		time_zone: 'Europe/Lisbon',
		registration_url: 'https://example.org/register',
		...SOURCE
	});
	for (const status of ['review', 'published']) {
		await created(`/directory/opportunities/${listing.id}/status`, reviewer, { status });
	}

	const member = await createAccount({ label: 'axe' });
	const bearer = await apiSession(member);
	const handle = `axe${tag}`;
	const profile = await apiCall('PUT', '/me/profile', {
		bearer,
		body: { handle, display_name: 'Axe Jumper', discoverable: true }
	});
	expect(profile.status).toBeLessThan(300);
	const component = (
		await created('/gear/components', bearer, {
			client_key: randomUUID(),
			kind: 'reserve',
			label: 'Axe reserve',
			// A jump-count limit: its line in the due lists and its fields on the form.
			jump_limit: 100,
			jump_limit_label: 'Axe check'
		})
	).component;
	// A repack 175 days ago: the "due soon" states of Logbook, Gear and the component.
	await created(`/gear/components/${component.id}/service`, bearer, {
		client_key: randomUUID(),
		kind: 'repack',
		done_on: daysFromToday(-175)
	});
	const jump = (
		await created('/jumps', bearer, {
			client_key: randomUUID(),
			jumped_on: '2026-10-10',
			jump_type: 'belly',
			venue_id: venue.id,
			aircraft: 'Axe Caravan'
		})
	).jump;
	// A change of many jumps: the Logbook's "Undo this change" card.
	const batch = await created('/jumps/batch', bearer, {
		jumps: [{ id: jump.id, version: jump.version }],
		changes: { aircraft: 'Axe Otter' }
	});
	expect(batch.changed).toEqual([jump.id]);
	const post = await created(`/me/jumps/${jump.id}/post`, bearer, {
		jump_version: jump.version + 1,
		audience: 'public',
		shares: ['type', 'venue']
	});
	await created('/plans', bearer, {
		title: 'Axe trip',
		starts_on: '2027-07-10',
		ends_on: '2027-07-12',
		venue_id: venue.id
	});
	await apiCall('PUT', `/saved/${listing.id}`, { bearer });
	// A plan next week: the "Coming up" list on the Logbook.
	await created('/plans', bearer, {
		title: 'Axe weekend',
		starts_on: daysFromToday(7),
		ends_on: daysFromToday(8),
		venue_id: venue.id
	});
	// A stated licence: currency, the next-licence line (Logbook) and section (History).
	await apiCall('PUT', '/me/licence', { bearer, body: { licence: 'b' } });
	// An exit weight and a sized main on a jump: wing loading on the jump, the Logbook
	// row, History's chart and the jump form's sizes; the first jump stays unknown.
	await apiCall('PUT', '/me/exit-weight', { bearer, body: { value: 82, unit: 'kg' } });
	const main = (
		await created('/gear/components', bearer, {
			client_key: randomUUID(),
			kind: 'main',
			label: 'Axe main',
			canopy_size_sqft: 170
		})
	).component;
	await created('/jumps', bearer, {
		client_key: randomUUID(),
		jumped_on: '2026-10-11',
		jump_type: 'freefly',
		venue_id: venue.id,
		component_ids: [main.id]
	});
	// A prior jump count: History's milestones include ones "before you kept this logbook".
	await apiCall('PUT', '/history/baseline', {
		bearer,
		body: { prior_jumps: 30, before_on: '2026-01-01' }
	});

	return {
		member,
		paths: {
			guest: [
				'/',
				'/dz',
				`/dz/${venue.id}`,
				`/events/${listing.id}`,
				`/organizers/${provider.id}`,
				`/people/${handle}`,
				`/posts/${post.id}`,
				'/privacy',
				'/support',
				'/status',
				'/sign-in',
				'/register',
				'/forgot-password'
			],
			member: [
				'/jumps',
				'/jumps?type=belly&from=2026-01-01',
				'/jumps?type=wingsuit',
				// Select mode: ticks on the rows and what to change.
				'/jumps?select=1',
				'/jumps?select=1&type=belly',
				'/jumps/new',
				// The form at a place with a recorded aircraft: prefilled, with its hint.
				`/jumps/new?venue=${venue.id}`,
				`/dz/${venue.id}`,
				`/jumps/${jump.id}`,
				`/jumps/${jump.id}/share`,
				'/history',
				'/history/baseline',
				'/activity',
				'/people',
				'/profile',
				'/profile/public',
				'/profile/data',
				'/records',
				'/records/import',
				'/records/print',
				// With the optional wing loading column.
				'/records/print?loading=yes',
				// The spreadsheet download refused (dates out of order), with its message.
				'/records?spreadsheet=date_range_invalid&from=2026-10-02&until=2026-10-01',
				'/gear',
				`/gear/${component.id}`,
				'/places',
				'/plans',
				'/saved',
				'/submit'
			],
			reviewer: [
				'/review',
				'/review/submissions',
				'/review/social',
				`/review/listings/${listing.id}`,
				`/review/organizers/${provider.id}`,
				`/review/dropzones/${venue.id}`
			]
		}
	};
}

async function signIn(page: Page, email: string, password = PASSWORD) {
	await page.goto('/sign-in');
	await page.getByLabel('Email', { exact: true }).fill(email);
	await page.getByLabel('Password', { exact: true }).fill(password);
	await page.getByRole('button', { name: 'Sign in' }).click();
	await expect(page.getByTestId('current-account')).toBeVisible();
}

/** Axe violations on the current page, one readable line per rule and element. */
async function violations(page: Page): Promise<string[]> {
	const result = await new AxeBuilder({ page }).withTags(TAGS).analyze();
	return result.violations.flatMap((v) =>
		v.nodes.map((n) => `${v.id} (${v.impact}): ${n.target.join(' ')} — ${v.help}`)
	);
}

async function scan(page: Page, paths: string[]) {
	for (const path of paths) {
		const response = await page.goto(path);
		expect(response?.status(), path).toBe(200);
		expect.soft(await violations(page), path).toEqual([]);
	}
}

let shared: World;

test('axe reports a planted violation, so the checks below can fail', async ({ page }) => {
	await page.setContent('<html lang="en"><title>Control</title><main><img src="x.png"></main></html>');
	expect((await violations(page)).join('\n')).toContain('image-alt');
});

test.describe('accessibility (axe, WCAG 2.2 A/AA)', () => {
	// The page set is the same on every device; two engines cover layout differences.
	test.beforeEach(({}, info) => {
		test.skip(info.project.name === 'pixel-7', 'chromium-320 covers Chromium');
		// Each test scans about twenty pages; WebKit needs more than the default 30 s.
		test.slow();
	});
	test.beforeAll(async () => {
		shared ??= await world();
	});

	for (const scheme of ['light', 'dark'] as const) {
		test.describe(scheme, () => {
			test.use({ colorScheme: scheme });

			test('public pages, signed out, and the sign-in sheet', async ({ page }) => {
				await scan(page, shared.paths.guest);
				await page.goto('/');
				await expect(page.locator('html[data-sign-in-sheet="ready"]')).toHaveCount(1);
				await page.locator('header a[data-sign-in]').click();
				await expect(page.getByRole('dialog')).toBeVisible();
				expect.soft(await violations(page), 'sign-in sheet').toEqual([]);
			});

			test('member pages', async ({ page }) => {
				await signIn(page, shared.member);
				await scan(page, shared.paths.member);
			});

			test('maintenance pages', async ({ page }) => {
				const { email, password } = reviewerCredentials();
				await signIn(page, email, password);
				await scan(page, shared.paths.reviewer);
			});
		});
	}
});
