import { describe, expect, it } from 'vitest';
import {
	daysUntil,
	dueBasis,
	dueSoon,
	dueState,
	dueText,
	dueWhat,
	itemState,
	parseInterval,
	parseJumpLimit,
	shortDay,
	type DueIn
} from './gear.ts';

const TODAY = '2026-11-12';

const due = (over: Partial<DueIn> = {}): DueIn => ({
	component: { id: 'c1', kind: 'reserve', label: 'PD 160' },
	kind: 'reserve_repack',
	service_kind: 'repack',
	due_on: '2026-11-17',
	basis: 'interval',
	interval_days: 180,
	interval_source: 'USPA / FAA 14 CFR 105.43',
	...over
});

describe('due dates', () => {
	it('counts calendar days across months and years', () => {
		expect(daysUntil('2026-11-17', TODAY)).toBe(5);
		expect(daysUntil('2026-11-11', TODAY)).toBe(-1);
		expect(daysUntil('2027-01-01', '2026-12-31')).toBe(1);
	});

	it('is soon through day 30, overdue from the day after the due date', () => {
		expect(dueState('2026-11-11', TODAY)).toBe('overdue');
		expect(dueState(TODAY, TODAY)).toBe('soon');
		expect(dueState('2026-12-12', TODAY)).toBe('soon');
		expect(dueState('2026-12-13', TODAY)).toBe('later');
	});

	it('says plainly when something is due or overdue', () => {
		expect(dueText(due(), TODAY)).toBe('Reserve repack due in 5 days (17 November)');
		expect(dueText(due({ due_on: TODAY }), TODAY)).toBe('Reserve repack due today');
		expect(dueText(due({ due_on: '2026-11-13' }), TODAY)).toBe(
			'Reserve repack due tomorrow (13 November)'
		);
		expect(dueText(due({ due_on: '2026-11-02' }), TODAY)).toBe(
			'Reserve repack overdue since 3 November'
		);
		expect(dueText(due({ due_on: '2027-01-05' }), TODAY)).toBe(
			'Reserve repack due in 54 days (5 January 2027)'
		);
	});

	it('names each kind of date', () => {
		const aad = { id: 'a', kind: 'aad', label: 'Cypres' };
		expect(dueWhat({ component: aad, kind: 'end_of_life', service_kind: null })).toBe(
			'AAD end of life'
		);
		expect(dueWhat({ component: aad, kind: 'service', service_kind: 'aad_service' })).toBe(
			'AAD maintenance'
		);
		expect(
			dueWhat({ component: { id: 'm', kind: 'main', label: 'Main' }, kind: 'end_of_life', service_kind: null })
		).toBe('End of service life');
		expect(dueWhat({ component: aad, kind: 'service', service_kind: 'inspection' })).toBe(
			'Inspection'
		);
	});

	it('cites the default interval and says when it is the owner’s own', () => {
		expect(dueBasis(due())).toContain(
			"180 days (USPA / FAA 14 CFR 105.43; your country's rule may differ)"
		);
		expect(dueBasis(due({ interval_days: 120, interval_source: null }))).toBe(
			'Your interval of 120 days after your last recorded repack.'
		);
	});

	it('keeps only overdue and due-within-30-days items for the logbook', () => {
		const items = [
			due({ due_on: '2026-11-01' }),
			due({ due_on: '2026-12-12' }),
			due({ due_on: '2026-12-13' })
		];
		expect(dueSoon(items, TODAY).map((i) => i.due_on)).toEqual(['2026-11-01', '2026-12-12']);
	});

	it('omits the year only in the current year', () => {
		expect(shortDay('2026-03-03', TODAY)).toBe('3 March');
		expect(shortDay('2025-03-03', TODAY)).toBe('3 March 2025');
	});
});

describe('parseInterval', () => {
	it('accepts empty or whole days from 1 to 730', () => {
		expect(parseInterval('')).toBeNull();
		expect(parseInterval(' 120 ')).toBe(120);
		expect(parseInterval('730')).toBe(730);
		for (const bad of ['0', '731', '1.5', '-3', 'abc', '1000']) {
			expect(parseInterval(bad)).toBe('invalid');
		}
	});
});

describe('jump limits', () => {
	const limit = (over: Partial<DueIn> = {}): DueIn => ({
		component: { id: 'm1', kind: 'main', label: 'Main canopy' },
		kind: 'jump_limit',
		service_kind: 'maintenance',
		due_on: null,
		basis: 'entered',
		interval_days: null,
		interval_source: null,
		status: 'soon',
		label: 'Reline',
		jump_limit: 500,
		jumps_used: 488,
		jumps_left: 12,
		counted_since: '2026-03-01',
		...over
	});

	it('says how many jumps are left or over', () => {
		expect(dueText(limit(), TODAY)).toBe('Reline due in 12 jumps');
		expect(dueText(limit({ jumps_left: 1 }), TODAY)).toBe('Reline due in 1 jump');
		expect(dueText(limit({ jumps_left: 0 }), TODAY)).toBe('Reline due now');
		expect(dueText(limit({ jumps_left: -3, status: 'overdue' }), TODAY)).toBe(
			'Reline overdue by 3 jumps'
		);
	});

	it('takes its state from the API, not the day', () => {
		expect(itemState(limit({ status: 'later' }), TODAY)).toBe('later');
		expect(dueSoon([limit(), limit({ status: 'later' }), due()], TODAY)).toHaveLength(2);
	});

	it('explains what is counted', () => {
		expect(dueBasis(limit())).toBe(
			'Your limit of 500 jumps: 488 jumps logged with it since your last maintenance / repair on 1 March 2026.'
		);
		expect(dueBasis(limit({ counted_since: null, jumps_used: 1 }))).toBe(
			'Your limit of 500 jumps: 1 jump logged with it since you added it (no maintenance / repair recorded).'
		);
	});

	it('reads the optional limit', () => {
		expect(parseJumpLimit('')).toBeNull();
		expect(parseJumpLimit(' 1,000 ')).toBe(1000);
		expect(parseJumpLimit('0')).toBe('invalid');
		expect(parseJumpLimit('100001')).toBe('invalid');
		expect(parseJumpLimit('ten')).toBe('invalid');
	});
});
