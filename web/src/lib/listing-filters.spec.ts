import { describe, expect, it } from 'vitest';
import { boardHref, hasFilters, parseFilters } from './listing-filters.ts';

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
