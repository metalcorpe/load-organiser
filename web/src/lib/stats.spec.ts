import { describe, expect, it } from 'vitest';
import {
	aircraftRows,
	freefallRows,
	monthRows,
	placeRows,
	totalText,
	typeRows,
	yearParam,
	yearRows
} from './stats.ts';

const place = (name: string | null, kind: 'venue' | 'place' = 'venue') => ({
	kind,
	id: `${kind}-${name}`,
	name,
	country: 'PT',
	closed: false
});

describe('statistics rows', () => {
	it('lists years and months newest first', () => {
		expect(
			yearRows({
				per_year: [
					{ year: 2024, jumps: 3 },
					{ year: 2025, jumps: 0 },
					{ year: 2026, jumps: 9 }
				]
			}).map((r) => [r.label, r.value])
		).toEqual([
			['2026', 9],
			['2025', 0],
			['2024', 3]
		]);
		expect(
			monthRows({
				per_month: [
					{ month: '2026-10', jumps: 2 },
					{ month: '2026-11', jumps: 1 }
				]
			})[0]
		).toEqual({ label: 'Nov 2026', value: 1 });
	});

	it('names types, places and aircraft, with the rest as others', () => {
		expect(typeRows({ by_type: [{ jump_type: 'freefly', jumps: 2 }] })).toEqual([
			{ label: 'Freefly', value: 2 }
		]);
		const places = placeRows({
			by_place: {
				items: [
					{ location: place('Axe Field'), jumps: 5 },
					{ location: place('Farm strip', 'place'), jumps: 2 },
					{ location: place(null), jumps: 1 }
				],
				others: 4,
				other_places: 3
			}
		});
		expect(places.map((r) => r.label)).toEqual([
			'Axe Field',
			'Farm strip (private place)',
			'Dropzone no longer listed',
			'Other places (3)'
		]);
		expect(places.at(-1)?.value).toBe(4);
		const aircraft = aircraftRows({
			by_aircraft: { items: [{ aircraft: 'Caravan', jumps: 3 }], others: 0, other_aircraft: 0, not_recorded: 2 }
		});
		expect(aircraft).toEqual([{ label: 'Caravan', value: 3 }]);
	});

	it('shows freefall time in plain units with the jumps that lack one', () => {
		expect(
			freefallRows({
				freefall: [{ year: 2026, seconds: 3725, with_freefall: 60, without_freefall: 4 }]
			})
		).toEqual([{ label: '2026', value: 3725, text: '1 h 2 min 5 s', extra: '4' }]);
	});

	it('includes the declared prior jump count only in the total, and says so', () => {
		expect(totalText({ year: null, total: { recorded: 5, reported: null, prior_jumps: null } })).toBe(
			'5 jumps recorded here.'
		);
		expect(totalText({ year: null, total: { recorded: 5, reported: 205, prior_jumps: 200 } })).toBe(
			'5 jumps recorded here. Reported total 205, including your declared prior jump count of 200.'
		);
		expect(totalText({ year: 2025, total: { recorded: 1, reported: null, prior_jumps: null } })).toBe(
			'1 jump recorded in 2025.'
		);
	});

	it('reads a four-digit year from the query, else all years', () => {
		expect(yearParam('2025')).toBe('2025');
		expect(yearParam(' 2025 ')).toBe('2025');
		expect(yearParam('25')).toBe('');
		expect(yearParam(null)).toBe('');
		expect(yearParam('2025-01')).toBe('');
	});
});
