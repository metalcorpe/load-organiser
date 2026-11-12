import { describe, expect, it } from 'vitest';
import {
	IMPORT_MESSAGES,
	describeImport,
	describeUndo,
	importMessage,
	importWhen,
	rowProblem
} from './imports.ts';

describe('import labels', () => {
	it('describes what an import saved, in plain words', () => {
		expect(describeImport({ rows: 4, jumps: 3, new_places: 1, skipped: 1 })).toBe(
			'3 jumps, 1 new private place, 1 row skipped'
		);
		expect(describeImport({ rows: 1, jumps: 1, new_places: 0, skipped: 0 })).toBe('1 jump');
		expect(describeImport({ jumps: 1200, new_places: 2, skipped: 3 })).toBe(
			'1,200 jumps, 2 new private places, 3 rows skipped'
		);
	});

	it('describes what an undo removed', () => {
		expect(describeUndo({ removed_jumps: 3, removed_places: 1 })).toBe(
			'Removed 3 jumps and 1 private place'
		);
		expect(describeUndo({ removed_jumps: 1, removed_places: 0 })).toBe('Removed 1 jump');
	});

	it('explains every row problem the API sends, and something for unknown ones', () => {
		for (const code of [
			'jump_date_required',
			'jump_date_invalid',
			'jump_date_in_future',
			'jump_number_invalid',
			'location_required',
			'place_too_long',
			'place_ambiguous',
			'altitude_invalid',
			'freefall_invalid',
			'notes_too_long',
			'likely_duplicate',
			'repeated_in_file'
		]) {
			expect(rowProblem(code)).not.toBe('this row could not be read');
		}
		expect(rowProblem('something_new')).toBe('this row could not be read');
	});

	it('falls back to a generic message for codes it does not know', () => {
		expect(importMessage('country_required')).toBe(IMPORT_MESSAGES.country_required);
		expect(importMessage('mystery')).toBe(IMPORT_MESSAGES.invalid_input);
		expect(importMessage(undefined)).toBeUndefined();
	});

	it('names when an import happened, to the minute in UTC', () => {
		expect(importWhen('2026-11-12T13:05:59.123+00:00')).toBe('12 November 2026, 13:05 UTC');
		expect(importWhen('2026-11-12T23:30:00-02:00')).toBe('13 November 2026, 01:30 UTC');
		expect(importWhen('not a date')).toBe('not a date');
	});
});
