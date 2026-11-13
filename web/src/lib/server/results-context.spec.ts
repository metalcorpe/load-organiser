import type { Cookies } from '@sveltejs/kit';
import { describe, expect, it } from 'vitest';
import { RESULTS_LIMIT, resultsPath } from '#lib/listing-filters.ts';
import { safeReturnPath } from '#lib/safe-return.ts';
import { recallResults, signInReturns } from './results-context.ts';

const id = '00000000-0000-4000-8000-000000000001';

/** A cookie jar that records options, enough for set/get. */
function jar() {
	const values = new Map<string, string>();
	const options = new Map<string, Record<string, unknown>>();
	const cookies = {
		get: (name: string) => values.get(name),
		set: (name: string, value: string, opts: Record<string, unknown>) => {
			values.set(name, value);
			options.set(name, opts);
		}
	} as unknown as Cookies;
	return { cookies, values, options };
}

const at = (path: string) => new URL(path, 'https://app.invalid');

/** Every filter, 80 three-byte characters (the most the 80-unit search cap allows) of text and the longest cursor kept. */
const longest = `/?q=${encodeURIComponent('€'.repeat(80))}&category=camp&country=PT&discipline=freefly&audience=licensed&from=2026-12-01&to=2027-01-31&cursor=${'a'.repeat(512)}`;

describe('resultsPath bound', () => {
	it('accepts the longest supported search, rebuilt', () => {
		expect(longest.length).toBeGreaterThan(512);
		expect(longest.length).toBeLessThanOrEqual(RESULTS_LIMIT);
		const kept = resultsPath(longest);
		expect(kept).not.toBeNull();
		expect(at(kept!).searchParams.get('q')).toBe('€'.repeat(80));
		expect(at(kept!).searchParams.get('cursor')).toBe('a'.repeat(512));
	});

	it('refuses anything past the bound', () => {
		expect(resultsPath(`/?country=PT&cursor=${'a'.repeat(RESULTS_LIMIT)}`)).toBeNull();
	});
});

describe('signInReturns', () => {
	it('keeps a short search in the URL and sets no cookie', () => {
		const { cookies, values } = jar();
		const returns = signInReturns(cookies, id, '/?country=PT', true);
		expect(returns.save).toBe(`/events/${id}?save=1&results=%2F%3Fcountry%3DPT`);
		expect(returns.plain).toBe(`/events/${id}?results=%2F%3Fcountry%3DPT`);
		expect(values.size).toBe(0);
	});

	it('needs nothing for a direct link', () => {
		const { cookies, values } = jar();
		expect(signInReturns(cookies, id, null, true)).toEqual({
			save: `/events/${id}?save=1`,
			plain: `/events/${id}`
		});
		expect(values.size).toBe(0);
	});

	it('keeps a long search in a cookie for this event, and recalls it after sign-in', () => {
		const { cookies, options } = jar();
		const results = resultsPath(longest)!;
		const returns = signInReturns(cookies, id, results, true);

		expect(returns.save).toMatch(new RegExp(`^/events/${id}\\?save=1&ctx=[A-Za-z0-9_-]{16}$`));
		// The return path itself stays within what sign-in accepts.
		expect(safeReturnPath(returns.save)).toBe(returns.save);
		expect(safeReturnPath(returns.plain)).toBe(returns.plain);
		expect(options.get('board_context')).toMatchObject({
			path: `/events/${id}`,
			httpOnly: true,
			secure: true,
			sameSite: 'lax',
			maxAge: 1800
		});

		expect(recallResults(cookies, at(returns.save))).toBe(results);
		expect(recallResults(cookies, at(returns.plain))).toBe(results);
	});

	it('ignores a wrong, malformed or expired cookie id', () => {
		const { cookies, values } = jar();
		const returns = signInReturns(cookies, id, resultsPath(longest)!, false);
		expect(recallResults(cookies, at(`/events/${id}?save=1&ctx=${'b'.repeat(16)}`))).toBeNull();
		expect(recallResults(cookies, at(`/events/${id}?ctx=short`))).toBeNull();
		values.clear(); // expired
		expect(recallResults(cookies, at(returns.save))).toBeNull();
	});

	it('validates a stored value again: a tampered cookie gives no context', () => {
		const { cookies, values } = jar();
		const returns = signInReturns(cookies, id, resultsPath(longest)!, true);
		const ctx = at(returns.save).searchParams.get('ctx');
		for (const bad of ['//evil.example', '/profile', 'https://evil.example/', '/\\evil']) {
			values.set('board_context', `${ctx}~${bad}`);
			expect(recallResults(cookies, at(returns.save))).toBeNull();
		}
		values.set('board_context', 'no-separator');
		expect(recallResults(cookies, at(returns.save))).toBeNull();
	});

	it('prefers a valid results parameter, and refuses an unsafe one', () => {
		const { cookies } = jar();
		expect(recallResults(cookies, at(`/events/${id}?results=${encodeURIComponent('/?country=ES')}`))).toBe(
			'/?country=ES'
		);
		expect(recallResults(cookies, at(`/events/${id}?results=${encodeURIComponent('//evil.example')}`))).toBeNull();
	});
});
