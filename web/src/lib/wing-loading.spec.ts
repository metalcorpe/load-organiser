import { describe, expect, it } from 'vitest';
import {
	formatLoading,
	formatWeight,
	highestNote,
	inUnit,
	isNotable,
	listNote,
	missingHelp,
	missingText,
	parseWeight,
	toGrams,
	wingLoading
} from './wing-loading.ts';

describe('wing loading', () => {
	it('is pounds over square feet to two decimals, as the API computes it', () => {
		// 81.6 kg over 170 sq ft; 180 lb over 150 sq ft; 90 kg over 170 sq ft.
		expect(wingLoading(81_600, 170)).toBe(1.06);
		expect(wingLoading(toGrams(180, 'lb'), 150)).toBe(1.2);
		expect(wingLoading(90_000, 170)).toBe(1.17);
		expect(wingLoading(null, 170)).toBeNull();
		expect(wingLoading(81_600, null)).toBeNull();
	});

	it('shows two decimals', () => {
		expect(formatLoading(1.2)).toBe('1.20');
		expect(formatLoading(1.06)).toBe('1.06');
		expect(formatLoading(0.95)).toBe('0.95');
	});

	it('notes a loading more than 0.1 above the highest so far, calmly', () => {
		expect(isNotable(1.35, 1.2)).toBe(true);
		expect(isNotable(1.3, 1.2)).toBe(false); // exactly 0.1 above
		expect(isNotable(1.31, 1.2)).toBe(true);
		expect(isNotable(1.35, null)).toBe(false); // nothing to compare with
		expect(isNotable(null, 1.2)).toBe(false);
		expect(highestNote(1.35, 1.2)).toBe(
			'This is your highest wing loading so far (1.35; previous highest 1.20).'
		);
	});

	it('says what is missing once, in a fixed order', () => {
		expect(missingText(['canopy_size', 'exit_weight'])).toBe(
			'no exit weight is set and the main canopy has no size'
		);
		expect(missingText(['main_canopy'])).toBe('no main canopy is recorded on the jump');
		expect(missingText([])).toBe('');
		expect(missingHelp(['exit_weight'])).toEqual({ profile: true, gear: false });
		expect(missingHelp(['several_mains'])).toEqual({ profile: false, gear: true });
	});

	it('gives a list one note, and none to a jumper who uses neither value', () => {
		const row = (value: number | null, ...missing: string[]) => ({ wing_loading: { value, missing } });
		expect(listNote([row(1.1), row(1.2)])).toBeNull();
		expect(listNote([row(null, 'exit_weight', 'main_canopy'), row(null, 'exit_weight')])).toBeNull();
		expect(listNote([row(1.1), row(null, 'main_canopy'), row(null, 'canopy_size')])).toEqual({
			count: 2,
			text: 'no main canopy is recorded on the jump and the main canopy has no size',
			missing: ['main_canopy', 'canopy_size']
		});
		// A weight is set (no row lacks one): say why the others have none.
		expect(listNote([row(null, 'main_canopy')])?.count).toBe(1);
	});
});

describe('exit weight', () => {
	it('converts units to grams and back as entered', () => {
		expect(toGrams(81.6, 'kg')).toBe(81_600);
		expect(toGrams(180, 'lb')).toBe(81_647);
		expect(inUnit(81_647, 'lb')).toBe(180);
		expect(formatWeight(81_647, 'lb')).toBe('180 lb');
		expect(formatWeight(81_600, 'kg')).toBe('81.6 kg');
	});

	it('accepts one decimal within 30 to 250 kg', () => {
		expect(parseWeight('', 'kg')).toBeNull();
		expect(parseWeight(' 81,6 ', 'kg')).toBe(81_600);
		expect(parseWeight('180', 'lb')).toBe(81_647);
		expect(parseWeight('81.65', 'kg')).toBe('invalid');
		expect(parseWeight('29.9', 'kg')).toBe('invalid');
		expect(parseWeight('66', 'lb')).toBe('invalid');
		expect(parseWeight('67', 'lb')).toBe(30_391);
		expect(parseWeight('heavy', 'kg')).toBe('invalid');
	});
});
