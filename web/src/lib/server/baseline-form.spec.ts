import { describe, expect, it } from 'vitest';
import { baselineInput } from './baseline-form.ts';

const q = (entries: Record<string, string>) => new URLSearchParams(entries);

describe('baselineInput', () => {
	it('reads a declaration with or without the version it was based on', () => {
		expect(baselineInput(q({ prior_jumps: '1,200', before_on: '2026-01-01' }))).toEqual({
			prior_jumps: 1200,
			before_on: '2026-01-01',
			version: null
		});
		const form = new FormData();
		form.set('prior_jumps', ' 0 ');
		form.set('before_on', '2025-06-30');
		form.set('version', '3');
		expect(baselineInput(form)).toEqual({ prior_jumps: 0, before_on: '2025-06-30', version: 3 });
	});

	it('is null when nothing was entered', () => {
		expect(baselineInput(q({}))).toBeNull();
		expect(baselineInput(q({ prior_jumps: '', before_on: '' }))).toBeNull();
	});

	it('refuses incomplete or malformed input before sending', () => {
		expect(baselineInput(q({ prior_jumps: '10' }))).toEqual({ error: 'missing' });
		expect(baselineInput(q({ before_on: '2026-01-01' }))).toEqual({ error: 'missing' });
		expect(baselineInput(q({ prior_jumps: '10', before_on: '1/1/2026' }))).toEqual({
			error: 'missing'
		});
		for (const bad of ['-1', '1.5', 'ten', '1234567']) {
			expect(baselineInput(q({ prior_jumps: bad, before_on: '2026-01-01' }))).toEqual({
				error: 'prior_jumps_invalid'
			});
		}
	});

	it('ignores a malformed version rather than guessing one', () => {
		const input = baselineInput(q({ prior_jumps: '1', before_on: '2026-01-01', version: '0' }));
		expect(input).toMatchObject({ version: null });
	});
});
