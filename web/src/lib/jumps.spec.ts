import { describe, expect, it } from 'vitest';
import type { JumpNumberingOut, JumpOut } from './contracts/index.ts';
import {
	jumpMessage,
	loadFailure,
	nextJumpValues,
	numberHint,
	numberingNotes,
	proposedNumber
} from './jumps.ts';

const jump = (over: Partial<JumpOut> = {}): JumpOut =>
	({
		jumped_on: '2026-11-08',
		jump_type: 'freefly',
		jump_number: 120,
		time_zone: 'Europe/Athens',
		exit_altitude: 4000,
		deployment_altitude: 1000,
		altitude_unit: 'm',
		altitude_datum: 'agl',
		exit_time: '10:15:00',
		freefall_seconds: 55,
		notes: 'private note',
		links: ['https://video.example/1'],
		other_gear: 'borrowed helmet',
		aircraft: 'Cessna 208 SX-ABC',
		components: [
			{ id: 'main', archived: false },
			{ id: 'old', archived: true }
		],
		...over
	}) as unknown as JumpOut;

describe('nextJumpValues', () => {
	it('keeps the day, type, altitudes, aircraft and gear, and counts on', () => {
		const next = nextJumpValues(jump(), { sameDay: true });
		expect(next.values).toEqual({
			jumped_on: '2026-11-08',
			jump_type: 'freefly',
			jump_number: '121',
			time_zone: 'Europe/Athens',
			exit_altitude: '4000',
			deployment_altitude: '1000',
			altitude_unit: 'm',
			altitude_datum: 'agl',
			aircraft: 'Cessna 208 SX-ABC'
		});
		expect(next.selected).toEqual(['main']); // archived gear is not preselected
	});

	it('never carries what describes one jump only', () => {
		const values = nextJumpValues(jump(), { sameDay: true }).values;
		for (const name of ['notes', 'links', 'other_gear', 'exit_time', 'freefall_seconds']) {
			expect(values).not.toHaveProperty(name);
		}
	});

	it('leaves the aircraft empty when the jump had none', () => {
		expect(nextJumpValues(jump({ aircraft: null }), { sameDay: false }).values.aircraft).toBe('');
	});

	it('leaves the number empty when the jump had none', () => {
		expect(nextJumpValues(jump({ jump_number: null }), { sameDay: true }).values.jump_number).toBe('');
		expect(nextJumpValues(jump({ exit_altitude: null }), { sameDay: true }).values.exit_altitude).toBe('');
	});

	it('leaves the date to the jumper\'s own today unless it is the same day', () => {
		expect(nextJumpValues(jump(), { sameDay: false }).values.jumped_on).toBe('');
	});
});

describe('the proposed next number', () => {
	it('is one after the highest, with a hint', () => {
		expect(proposedNumber(120)).toBe(121);
		expect(numberHint(120)).toBe('Your last numbered jump is #120.');
	});

	it('is nothing for a jumper who never numbered a jump, or at the limit', () => {
		expect(proposedNumber(null)).toBeNull();
		expect(numberHint(null)).toBeNull();
		expect(numberHint(1_000_000)).toBeNull();
	});
});

describe('numberingNotes', () => {
	const ref = (id: string, n: number) => ({ id, jumped_on: '2026-10-01', jump_number: n });
	const numbering = (over: Partial<JumpNumberingOut> = {}): JumpNumberingOut => ({
		highest: 130,
		gaps: [],
		gap_count: 0,
		repeats: [],
		repeat_count: 0,
		...over
	});

	it('says nothing when the numbering is in order', () => {
		expect(numberingNotes(numbering())).toEqual({ notes: [], more: null });
	});

	it('names gaps and repeats briefly, linking to the jumps', () => {
		const { notes, more } = numberingNotes(
			numbering({
				gaps: [
					{ first: 121, last: 124, before: ref('a', 120), after: ref('b', 125) },
					{ first: 127, last: 127, before: ref('c', 126), after: ref('d', 128) }
				],
				gap_count: 3,
				repeats: [{ jump_number: 130, uses: 2, jumps: [ref('e', 130), ref('f', 130)] }],
				repeat_count: 1
			})
		);
		expect(notes.map((note) => note.text)).toEqual([
			'Numbers 121–124 are missing',
			'Number 127 is missing',
			'#130 is used twice'
		]);
		expect(notes[0]).toMatchObject({ before: { id: 'a', number: 120 }, after: { id: 'b', number: 125 } });
		expect(notes[2]).toMatchObject({ jumps: [{ id: 'e' }, { id: 'f' }] });
		expect(more).toBe('And 1 more gap.');
	});

	it('counts larger repeats', () => {
		const { notes } = numberingNotes(
			numbering({ repeats: [{ jump_number: 7, uses: 5, jumps: [] }], repeat_count: 1 })
		);
		expect(notes[0].text).toBe('#7 is used 5 times');
	});
});

describe('loadFailure', () => {
	it('offers a retry only when the service failed or did not answer', () => {
		expect(loadFailure('unavailable')).toBe('retry');
		expect(loadFailure('uncertain')).toBe('retry');
	});

	it('treats an old page link as stale, not as a failure', () => {
		expect(loadFailure('cursor_invalid')).toBe('stale');
	});

	it('keeps every other refusal with its own message', () => {
		for (const reason of ['not_authenticated', 'forbidden', 'invalid_input', 'not_found']) {
			expect(loadFailure(reason)).toBe('refused');
		}
		expect(jumpMessage('not_authenticated')).toBe('Your session has ended. Sign in again.');
	});
});

describe('altitude errors', () => {
	it('name the altitude that failed', () => {
		expect(jumpMessage('altitude_invalid')).toMatch(/^Check the exit altitude/);
		expect(jumpMessage('deployment_altitude_invalid')).toMatch(/^Check the deployment altitude/);
	});
});
