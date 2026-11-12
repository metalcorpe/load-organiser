import { describe, expect, it } from 'vitest';
import type { JumpOut } from './contracts/index.ts';
import { dateParam, formatFreefall, paginate, toRow, truncate } from './print.ts';

let next = 0;
const jump = (over: Partial<JumpOut> = {}): JumpOut =>
	({
		id: `j${next++}`,
		jumped_on: '2026-10-10',
		location: { kind: 'place', id: 'p1', name: 'Farm strip', country: 'PT', closed: false },
		jump_type: 'belly',
		jump_number: 12,
		exit_altitude: 4000,
		altitude_unit: 'm',
		altitude_datum: 'agl',
		freefall_seconds: 50,
		components: [{ id: 'c1', kind: 'main', label: 'Sabre 170', archived: false }],
		other_gear: 'borrowed helmet',
		aircraft: 'Cessna 208',
		notes: 'Four-way, good exit.',
		exit_weight_grams: null,
		wing_loading: {
			value: 1.06,
			exit_weight_grams: 81_600,
			exit_weight_from_jump: false,
			unit: 'kg',
			canopy_size_sqft: 170,
			missing: []
		},
		...over
	}) as unknown as JumpOut;

describe('formatFreefall', () => {
	it('uses plain units', () => {
		expect(formatFreefall(0)).toBe('0 s');
		expect(formatFreefall(45)).toBe('45 s');
		expect(formatFreefall(65)).toBe('1 min 5 s');
		expect(formatFreefall(3600)).toBe('1 h 0 min 0 s');
		expect(formatFreefall(7385)).toBe('2 h 3 min 5 s');
	});
});

describe('truncate', () => {
	it('keeps short notes and flattens whitespace', () => {
		expect(truncate('  one\n two  ')).toBe('one two');
	});

	it('cuts long notes at a word with an ellipsis', () => {
		const out = truncate('alpha beta gamma delta epsilon', 16);
		expect(out).toBe('alpha beta…');
		expect(out.length).toBeLessThanOrEqual(16);
	});

	it('cuts a single long word', () => {
		expect(truncate('x'.repeat(30), 10)).toBe(`${'x'.repeat(9)}…`);
	});
});

describe('toRow', () => {
	it('formats one entry like a paper logbook line', () => {
		expect(toRow(jump(), { notes: true })).toMatchObject({
			number: '12',
			date: '10 Oct 2026',
			place: 'Farm strip',
			type: 'Belly / formation',
			aircraft: 'Cessna 208',
			exit: '4,000 m AGL',
			freefall: '50 s',
			equipment: 'Sabre 170, borrowed helmet',
			notes: 'Four-way, good exit.'
		});
	});

	it('leaves unknown values empty and omits notes when asked', () => {
		const row = toRow(
			jump({
				jump_number: null,
				exit_altitude: null,
				altitude_unit: null,
				freefall_seconds: null,
				components: [],
				other_gear: null,
				aircraft: null,
				location: { kind: 'venue', id: 'v', name: null, country: null, closed: false }
			}),
			{ notes: false }
		);
		expect(row).toMatchObject({
			number: '',
			aircraft: '',
			exit: '',
			freefall: '',
			equipment: '',
			notes: '',
			place: 'Dropzone no longer listed'
		});
	});

	it('prints the wing loading only when asked and known', () => {
		expect(toRow(jump(), { notes: false }).loading).toBe('');
		expect(toRow(jump(), { notes: false, loading: true }).loading).toBe('1.06');
		const unknown = jump({
			wing_loading: {
				value: null,
				exit_weight_grams: null,
				exit_weight_from_jump: false,
				unit: 'kg',
				canopy_size_sqft: null,
				missing: ['exit_weight', 'main_canopy']
			}
		});
		expect(toRow(unknown, { notes: false, loading: true }).loading).toBe('');
	});
});

describe('paginate', () => {
	it('adds page totals and running totals from what came before', () => {
		const jumps = [
			jump({ freefall_seconds: 40 }),
			jump({ freefall_seconds: null }),
			jump({ freefall_seconds: 60 }),
			jump({ freefall_seconds: 30 }),
			jump({ freefall_seconds: 10 })
		];
		const pages = paginate(jumps, { notes: false, before: { jumps: 7, freefall: 300 }, perPage: 2 });
		expect(pages.map((p) => p.rows.length)).toEqual([2, 2, 1]);
		expect(pages[0]).toMatchObject({
			number: 1,
			page: { jumps: 2, freefall: 40 },
			broughtForward: { jumps: 7, freefall: 300 },
			toDate: { jumps: 9, freefall: 340 }
		});
		expect(pages[1]).toMatchObject({
			page: { jumps: 2, freefall: 90 },
			broughtForward: { jumps: 9, freefall: 340 },
			toDate: { jumps: 11, freefall: 430 }
		});
		expect(pages[2].toDate).toEqual({ jumps: 12, freefall: 440 });
	});

	it('has no pages without jumps', () => {
		expect(paginate([], { notes: true, before: { jumps: 0, freefall: 0 } })).toEqual([]);
	});
});

describe('dateParam', () => {
	it('accepts real calendar dates only', () => {
		expect(dateParam('2026-02-28')).toBe('2026-02-28');
		expect(dateParam('2026-02-30')).toBe('');
		expect(dateParam('2026-2-1')).toBe('');
		expect(dateParam(null)).toBe('');
	});
});
