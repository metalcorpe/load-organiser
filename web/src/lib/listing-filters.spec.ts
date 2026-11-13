import { describe, expect, it } from 'vitest';
import { boardHref, eventHref, hasFilters, parseFilters, resultsPath } from './listing-filters.ts';
import { safeReturnPath } from './safe-return.ts';

describe('parseFilters', () => {
	it('keeps known values and drops everything else', () => {
		const filters = parseFilters(
			new URLSearchParams(
				'q=  wingsuit camp &category=camp&country=es&discipline=swoop&audience=students&from=2026-12-01&to=2026-02-30'
			)
		);
		expect(filters).toEqual({
			q: 'wingsuit camp',
			category: 'camp',
			country: 'ES',
			discipline: '',
			audience: 'students',
			from: '2026-12-01',
			to: ''
		});
	});

	it('treats an empty query as no filters', () => {
		const filters = parseFilters(new URLSearchParams('category=raffle&country=XX'));
		expect(hasFilters(filters)).toBe(false);
		expect(boardHref(filters)).toBe('/');
	});

	it('builds a stable board URL with a cursor', () => {
		const filters = parseFilters(new URLSearchParams('country=PT&category=boogie'));
		expect(boardHref(filters, 'abc')).toBe('/?category=boogie&country=PT&cursor=abc');
	});
});

describe('resultsPath (Back to results)', () => {
	it('keeps a board search with its filters and page, rebuilt in a stable order', () => {
		expect(resultsPath('/?country=PT&from=2027-07-01&to=2027-07-31')).toBe(
			'/?country=PT&from=2027-07-01&to=2027-07-31'
		);
		expect(resultsPath('/?cursor=abc&category=camp')).toBe('/?category=camp&cursor=abc');
		expect(resultsPath('/?q=wingsuit%20camp')).toBe('/?q=wingsuit+camp');
	});

	it('drops unknown parameters and invalid values', () => {
		expect(resultsPath('/?country=PT&evil=1&category=raffle')).toBe('/?country=PT');
	});

	it.each([
		null,
		'',
		'/',
		'/?category=raffle',
		'/dz?country=PT',
		'/events/1',
		'/profile',
		'//evil.example/?country=PT',
		'/\\evil.example/?country=PT',
		'/.//evil.example/?country=PT',
		'https://evil.example/?country=PT',
		'javascript:alert(1)',
		'?country=PT',
		'/?country=PT\n'
	])('gives no context for %s', (raw) => {
		expect(resultsPath(raw)).toBeNull();
	});
});

describe('eventHref', () => {
	const id = '00000000-0000-4000-8000-000000000001';

	it('links an event plainly without a search context', () => {
		expect(eventHref(id)).toBe(`/events/${id}`);
		expect(eventHref(id, { results: '/' })).toBe(`/events/${id}`);
		expect(eventHref(id, { results: '//evil.example' })).toBe(`/events/${id}`);
	});

	it('carries the search, and the save intent for sign-in', () => {
		const href = eventHref(id, { results: '/?country=PT&cursor=abc', save: true });
		expect(href).toBe(`/events/${id}?save=1&results=%2F%3Fcountry%3DPT%26cursor%3Dabc`);
		const back = new URL(href, 'https://x.invalid').searchParams.get('results');
		expect(resultsPath(back)).toBe('/?country=PT&cursor=abc');
	});

	it('keeps a non-ASCII search on ordinary links, though it is encoded twice', () => {
		const q = 'é'.repeat(80);
		const href = eventHref(id, { results: `/?q=${encodeURIComponent(q)}&country=PT` });
		expect(href.length).toBeGreaterThan(512);
		const back = new URL(href, 'https://x.invalid').searchParams.get('results');
		expect(back).not.toBeNull();
		expect(new URL(back!, 'https://x.invalid').searchParams.get('q')).toBe(q);
		expect(resultsPath(back)).toBe(back);
	});

	it('keeps a long cursor on ordinary links up to the link cap', () => {
		const long = eventHref(id, { results: `/?country=PT&cursor=${'a'.repeat(480)}` });
		expect(long).toContain('results=');
		const huge = eventHref(id, { results: `/?country=PT&cursor=${'a'.repeat(512)}&q=${'é'.repeat(80)}` });
		expect(huge.length).toBeLessThanOrEqual(2048);
	});

	it('drops a too-long search from the sign-in return path only', () => {
		const q = encodeURIComponent('é'.repeat(80));
		const href = eventHref(id, { results: `/?q=${q}`, save: true });
		expect(href).toBe(`/events/${id}?save=1`);
		expect(safeReturnPath(href)).toBe(href);
	});

	it('drops a search too long to survive the sign-in return path, keeping the intent', () => {
		const href = eventHref(id, { results: `/?country=PT&cursor=${'a'.repeat(480)}`, save: true });
		expect(href).toBe(`/events/${id}?save=1`);
		expect(safeReturnPath(href)).toBe(href);
	});
});
