import { describe, expect, it } from 'vitest';
import {
	NO_FILTERS,
	formatDuration,
	freefallText,
	hasJumpFilters,
	jumpsHref,
	jumpsQuery,
	parseJumpFilters
} from './jump-filters.ts';

const ID = '0190b4f2-1c2d-7e3f-8a4b-5c6d7e8f9a0b';

describe('parseJumpFilters', () => {
	it('keeps well-formed values', () => {
		const filters = parseJumpFilters(
			new URLSearchParams(
				`q=+sunset+&type=belly&at=venue:${ID}&from=2026-01-01&to=2026-02-01&from_number=010&to_number=200`
			)
		);
		expect(filters).toEqual({
			q: 'sunset',
			type: 'belly',
			at: `venue:${ID}`,
			from: '2026-01-01',
			to: '2026-02-01',
			from_number: '10',
			to_number: '200'
		});
		expect(hasJumpFilters(filters)).toBe(true);
	});

	it('drops anything else', () => {
		const filters = parseJumpFilters(
			new URLSearchParams(
				'type=skysurf&at=person:x&from=2026-02-30&to=yesterday&from_number=0&to_number=9999999&cursor=abc'
			)
		);
		expect(filters).toEqual(NO_FILTERS);
		expect(hasJumpFilters(filters)).toBe(false);
	});
});

describe('jumpsHref and jumpsQuery', () => {
	it('keeps the filters on every page and omits empty ones', () => {
		const filters = { ...NO_FILTERS, type: 'belly', from: '2026-01-01' };
		expect(jumpsHref(filters)).toBe('/jumps?type=belly&from=2026-01-01');
		expect(jumpsHref(filters, 'c1')).toBe('/jumps?type=belly&from=2026-01-01&cursor=c1');
		expect(jumpsHref(NO_FILTERS)).toBe('/jumps');
	});

	it('maps the place choice to a venue or a private place', () => {
		expect(jumpsQuery({ ...NO_FILTERS, at: `place:${ID}` })).toMatchObject({
			place_id: ID,
			venue_id: undefined
		});
		expect(jumpsQuery({ ...NO_FILTERS, at: `venue:${ID}`, to_number: '5' })).toMatchObject({
			venue_id: ID,
			place_id: undefined,
			number_to: '5'
		});
	});
});

describe('freefall totals', () => {
	it('formats durations', () => {
		expect(formatDuration(45)).toBe('45 s');
		expect(formatDuration(570)).toBe('9 min 30 s');
		expect(formatDuration(3720)).toBe('1 h 2 min');
	});

	it('says how many jumps the sum covers, and nothing when none recorded it', () => {
		expect(freefallText(120, 2, 2)).toBe('2 min of freefall');
		expect(freefallText(120, 2, 5)).toBe('2 min of freefall (recorded on 2 of 5)');
		expect(freefallText(null, 0, 5)).toBeNull();
	});
});
