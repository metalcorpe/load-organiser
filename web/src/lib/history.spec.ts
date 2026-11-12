import { describe, expect, it } from 'vitest';
import { milestoneText, ordinal, type MilestoneIn } from './history.ts';

const m = (over: Partial<MilestoneIn>): MilestoneIn => ({
	kind: 'jump_count',
	number: null,
	hours: null,
	jump_type: null,
	location: null,
	...over
});

describe('ordinal', () => {
	it('uses st, nd, rd and th, with 11 to 13 as th', () => {
		expect([1, 2, 3, 4, 11, 12, 13, 21, 22, 23, 25, 101, 111].map(ordinal)).toEqual([
			'1st', '2nd', '3rd', '4th', '11th', '12th', '13th', '21st', '22nd', '23rd', '25th', '101st', '111th'
		]);
		expect(ordinal(1000)).toBe('1,000th');
	});
});

describe('milestoneText', () => {
	it('words each kind plainly', () => {
		expect(milestoneText(m({ number: 25 }))).toBe('25th jump');
		expect(milestoneText(m({ kind: 'freefall', hours: 1 }))).toBe('1 hour of recorded freefall');
		expect(milestoneText(m({ kind: 'freefall', hours: 10 }))).toBe('10 hours of recorded freefall');
		expect(milestoneText(m({ kind: 'jump_type', jump_type: 'wingsuit' }))).toBe('First wingsuit jump');
		expect(milestoneText(m({ kind: 'jump_type', jump_type: 'crw' }))).toBe(
			'First canopy formation (CRW) jump'
		);
		expect(
			milestoneText(m({ kind: 'place', location: { kind: 'venue', name: 'Skydive Algarve' } }))
		).toBe('First jump at Skydive Algarve');
		expect(milestoneText(m({ kind: 'place', location: { kind: 'venue', name: null } }))).toBe(
			'First jump at a dropzone no longer listed'
		);
	});
});
