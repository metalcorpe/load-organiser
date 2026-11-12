import { describe, expect, it } from 'vitest';
import type { JumpOut } from './contracts/index.ts';
import { nextJumpValues } from './jumps.ts';

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
		components: [
			{ id: 'main', archived: false },
			{ id: 'old', archived: true }
		],
		...over
	}) as unknown as JumpOut;

describe('nextJumpValues', () => {
	it('keeps the day, type, altitudes and gear, and counts on', () => {
		const next = nextJumpValues(jump());
		expect(next.values).toEqual({
			jumped_on: '2026-11-08',
			jump_type: 'freefly',
			jump_number: '121',
			time_zone: 'Europe/Athens',
			exit_altitude: '4000',
			deployment_altitude: '1000',
			altitude_unit: 'm',
			altitude_datum: 'agl'
		});
		expect(next.selected).toEqual(['main']); // archived gear is not preselected
	});

	it('never carries what describes one jump only', () => {
		const values = nextJumpValues(jump()).values;
		for (const name of ['notes', 'links', 'other_gear', 'exit_time', 'freefall_seconds']) {
			expect(values).not.toHaveProperty(name);
		}
	});

	it('leaves the number empty when the jump had none', () => {
		expect(nextJumpValues(jump({ jump_number: null })).values.jump_number).toBe('');
		expect(nextJumpValues(jump({ exit_altitude: null })).values.exit_altitude).toBe('');
	});
});
