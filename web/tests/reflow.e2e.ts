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

// Reflow with enlarged text (WCAG 1.4.4 and 1.4.10): 320 CSS px wide, text at 200%. The page
// text keeps its words whole (overflow-wrap: break-word, app.css), so the long unbroken strings
// (web addresses, emails, handles) need overflow-wrap: anywhere where they are shown. Here each
// one is as long as allowed or longer, and the page content must still not reach past the
// right edge of the screen.
const ORIGIN = 'https://127.0.0.1:4175';
test.use({ baseURL: ORIGIN, ignoreHTTPSErrors: true, viewport: { width: 320, height: 640 } });

/** Forty letters with no break opportunity, repeated in addresses and messages below. */
const LONG = 'averyveryverylongsegmentwithoutanybreaks';
const URL_LONG = `https://${LONG}.example.org/${LONG}${LONG}?ref=${LONG}`;

async function created(path: string, bearer: string, body: unknown): Promise<Record<string, any>> {
	const response = await apiCall('POST', path, { bearer, body });
	expect(response.status, `${path}: ${await response.clone().text()}`).toBeLessThan(300);
	return (await response.json()) as Record<string, any>;
}

interface World {
	member: string;
	paths: { guest: string[]; member: string[]; reviewer: string[] };
}

/** One of each record that shows an address, email or handle, each as long as allowed or more. */
async function world(): Promise<World> {
	const reviewer = await reviewerSession();
	const tag = randomBytes(4).toString('hex');
	const source = { source_url: URL_LONG, checked_on: '2026-11-01' };
	const venue = await created('/directory/venues', reviewer, {
		name: `Reflow Field ${tag}`,
		locality: 'Reykjavik',
		country: 'IS',
		...source
	});
	const provider = await created('/directory/providers', reviewer, {
		name: `Reflow Club ${tag}`,
		kind: 'organization',
		website_url: `https://www.${LONG}.example.org/`,
		...source,
		publish: true
	});
	const listing = await created('/directory/opportunities', reviewer, {
		title: `Reflow Boogie ${tag}`,
		category: 'boogie',
		provider_id: provider.id,
		venue_id: venue.id,
		country: 'IS',
		starts_on: '2027-07-10',
		ends_on: '2027-07-14',
		time_zone: 'Atlantic/Reykjavik',
		registration_url: `https://register.${LONG}.example.org/${LONG}`,
		...source
	});
	for (const status of ['review', 'published']) {
		await created(`/directory/opportunities/${listing.id}/status`, reviewer, { status });
	}

	// No hyphen in the label: the address has a 36-letter run before its random part.
	const member = await createAccount({ label: 'reflowcheckswithalongaddressnobreaks' });
	const bearer = await apiSession(member);
	// The longest handle allowed (30 characters).
	const handle = `rf${tag}longhandleforreflow`;
	const profile = await apiCall('PUT', '/me/profile', {
		bearer,
		body: { handle, display_name: 'Reflow Jumper', discoverable: true }
	});
	expect(profile.status).toBeLessThan(300);
	const jump = (
		await created('/jumps', bearer, {
			client_key: randomUUID(),
			jumped_on: '2026-10-10',
			jump_type: 'belly',
			venue_id: venue.id,
			notes: `Video at ${URL_LONG}, sent by ${member}.`,
			links: [URL_LONG]
		})
	).jump;
	const post = await created(`/me/jumps/${jump.id}/post`, bearer, {
		jump_version: jump.version,
		audience: 'public',
		shares: ['type', 'venue'],
		caption: `Video at ${URL_LONG}.`,
		link: URL_LONG
	});
	await created('/plans', bearer, {
		title: 'Reflow trip',
		starts_on: '2027-07-10',
		ends_on: '2027-07-12',
		venue_id: venue.id,
		note: `Details at ${URL_LONG}, ask ${member}.`
	});
	await created('/submissions', bearer, {
		client_key: randomUUID(),
		kind: 'suggest_venue',
		message: `Missing dropzone, see ${URL_LONG} or write to ${member}.`,
		source_url: URL_LONG
	});
	const component = (
		await created('/gear/components', bearer, {
			client_key: randomUUID(),
			kind: 'reserve',
			label: 'Reflow reserve'
		})
	).component;
	await created(`/gear/components/${component.id}/service`, bearer, {
		client_key: randomUUID(),
		kind: 'repack',
		done_on: '2026-10-01',
		performed_by: member,
		notes: `Record at ${URL_LONG}.`
	});

	return {
		member,
		paths: {
			guest: [
				'/',
				`/dz/${venue.id}`,
				`/events/${listing.id}`,
				`/organizers/${provider.id}`,
				`/people/${handle}`,
				`/posts/${post.id}`
			],
			member: [
				'/jumps',
				`/jumps/${jump.id}`,
				'/profile',
				'/profile/account',
				'/profile/public',
				'/plans',
				'/submit',
				`/gear/${component.id}`
			],
			reviewer: [
				'/review/submissions',
				`/review/dropzones/${venue.id}`,
				`/review/listings/${listing.id}`,
				`/review/organizers/${provider.id}`
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

interface Reflow {
	/** How far the page content reaches past the right edge of the screen, in CSS px. */
	overflow: number;
	/** The elements reaching furthest past it, to name in a failure. */
	wide: string[];
}

/**
 * Text at 200%, as a browser's text-only zoom: rem sizes and the body's 16px base doubled (no
 * font size in app.css is in px besides that base). Then the page content (main) is measured;
 * the header and tab bar are left to shell.e2e.ts. An element inside its own scroll box does
 * not count: it scrolls there, not the page.
 */
async function at200(page: Page): Promise<Reflow> {
	return page.evaluate(() => {
		document.documentElement.style.fontSize = '200%';
		document.body.style.fontSize = '32px';
		const edge = document.documentElement.clientWidth;
		const main = document.querySelector('main')!;
		const scrolls = (element: Element | null): boolean => {
			for (let at = element; at && at !== main; at = at.parentElement) {
				if (getComputedStyle(at).overflowX !== 'visible') return true;
			}
			return false;
		};
		const past = [...main.querySelectorAll('*')]
			.map((element) => ({ element, right: element.getBoundingClientRect().right }))
			.filter(({ element, right }) => right > edge + 0.5 && !scrolls(element.parentElement))
			.sort((a, b) => b.right - a.right);
		const name = (element: Element) =>
			`${element.tagName.toLowerCase()}${[...element.classList].map((c) => `.${c}`).join('')}`;
		return {
			overflow: past.length ? Math.round(past[0].right - edge) : 0,
			wide: past.slice(0, 3).map(({ element }) => name(element))
		};
	});
}

async function check(page: Page, paths: string[]) {
	for (const path of paths) {
		const response = await page.goto(path);
		expect(response?.status(), path).toBe(200);
		const result = await at200(page);
		// The enlargement took: body text at 32px.
		expect(await page.evaluate(() => getComputedStyle(document.body).fontSize), path).toBe('32px');
		expect.soft(result.overflow, `${path} is wider than the screen: ${result.wide.join(', ')}`).toBe(0);
	}
}

let shared: World;

test.describe('reflow at 320px with 200% text', () => {
	test.beforeEach(({}, info) => {
		// Chromium (chromium-320) and WebKit (iphone-13, narrowed to 320px above).
		test.skip(info.project.name === 'pixel-7', 'chromium-320 covers Chromium');
		test.slow();
	});
	test.beforeAll(async () => {
		shared ??= await world();
	});

	test('public pages', async ({ page }) => {
		await check(page, shared.paths.guest);
	});

	test('member pages', async ({ page }) => {
		await signIn(page, shared.member);
		await check(page, shared.paths.member);
	});

	test('maintenance pages', async ({ page }) => {
		const { email, password } = reviewerCredentials();
		await signIn(page, email, password);
		await check(page, shared.paths.reviewer);
	});
});
