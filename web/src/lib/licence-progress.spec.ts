import { describe, expect, it } from 'vitest';
import {
	OTHER_REQUIREMENTS,
	duration,
	progressLines,
	progressSummary,
	type ProgressIn
} from './licence-progress.ts';

const p = (over: Partial<ProgressIn> = {}): ProgressIn => ({
	licence: 'b',
	next_licence: 'c',
	jumps: 60,
	jumps_required: 200,
	jumps_include_prior: false,
	freefall_seconds: 40 * 60,
	freefall_required_seconds: 60 * 60,
	entries_without_freefall: 0,
	...over
});

describe('duration', () => {
	it('uses minutes below two hours, then hours and minutes', () => {
		expect(duration(0)).toBe('0 minutes');
		expect(duration(60)).toBe('1 minute');
		expect(duration(40 * 60 + 59)).toBe('40 minutes');
		expect(duration(60 * 60)).toBe('60 minutes');
		expect(duration(3 * 3600)).toBe('3 hours');
		expect(duration(2 * 3600 + 15 * 60)).toBe('2 hours 15 minutes');
	});
});

describe('progress toward the next licence', () => {
	it('shows jumps and recorded freefall time toward C for a B licence', () => {
		const lines = progressLines(p());
		expect(lines.toward).toBe('Toward a C licence');
		expect(lines.jumps).toBe('Jumps: 60 of 200 (140 to go).');
		expect(lines.freefall).toBe('Recorded freefall time: 40 minutes of 60 minutes (20 minutes to go).');
		expect(lines.missing).toBeNull();
		expect(progressSummary(p())).toBe(
			'Toward a C licence: 60 of 200 jumps, 40 minutes of 60 minutes of freefall.'
		);
	});

	it('says reached once a threshold is met, exactly at it included', () => {
		const lines = progressLines(p({ jumps: 200, freefall_seconds: 3600 }));
		expect(lines.jumps).toBe('Jumps: 200 of 200 (reached).');
		expect(lines.freefall).toContain('(reached)');
	});

	it('says how many entries lack a freefall time and that prior jumps add none', () => {
		const lines = progressLines(p({ entries_without_freefall: 3, jumps_include_prior: true }));
		expect(lines.missing).toBe('3 entries have no freefall time, so they add none.');
		expect(lines.prior).toContain('in the jump total but not in the freefall time');
		expect(progressLines(p({ entries_without_freefall: 1 })).missing).toBe(
			'1 entry has no freefall time, so it adds none.'
		);
	});

	it('lists only jumps for a student toward A', () => {
		const student = p({
			licence: 'student',
			next_licence: 'a',
			jumps: 12,
			jumps_required: 25,
			freefall_required_seconds: null
		});
		expect(progressLines(student).toward).toBe('Toward an A licence');
		expect(progressLines(student).freefall).toBeNull();
		expect(progressSummary(student)).toBe('Toward an A licence: 12 of 25 jumps.');
	});

	it('has no next step for a D licence', () => {
		const d = p({ licence: 'd', next_licence: null, jumps_required: null, freefall_required_seconds: null });
		expect(progressLines(d).highest).toBe(
			'You stated a D licence, the highest USPA licence: there is no next licence to track.'
		);
		expect(progressSummary(d)).toBeNull();
	});

	it('cites USPA SIM 3-1 for what the app does not check', () => {
		expect(OTHER_REQUIREMENTS).toContain('checked by USPA and your instructors, not by this app');
		expect(OTHER_REQUIREMENTS).toContain('USPA SIM 3-1');
	});
});
