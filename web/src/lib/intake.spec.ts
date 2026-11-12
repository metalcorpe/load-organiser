import { describe, expect, it } from 'vitest';
import { intakePaused } from './intake.ts';

describe('intakePaused', () => {
	it('is paused only when the check answers closed', () => {
		expect(intakePaused({ ok: true, value: { open: false } })).toBe(true);
		expect(intakePaused({ ok: true, value: { open: true } })).toBe(false);
	});

	it('keeps the form when the check fails (unknown is not paused)', () => {
		expect(intakePaused({ ok: false })).toBe(false);
	});
});
