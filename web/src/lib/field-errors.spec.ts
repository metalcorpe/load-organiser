import { describe, expect, it } from 'vitest';
import { fieldsFor } from './field-errors.ts';

describe('fieldsFor', () => {
	it('marks the altitude that failed, not both', () => {
		expect(fieldsFor('altitude_invalid')).toEqual(['exit_altitude']);
		expect(fieldsFor('deployment_altitude_invalid')).toEqual(['deployment_altitude']);
		expect(fieldsFor('deployment_above_exit')).toEqual(['deployment_altitude']);
	});

	it('names no field for a code about the whole form', () => {
		expect(fieldsFor('edit_conflict')).toEqual([]);
		expect(fieldsFor('unavailable')).toEqual([]);
		expect(fieldsFor(undefined)).toEqual([]);
	});
});
