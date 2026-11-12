import { describe, expect, it } from 'vitest';
import { addDays, currencyState, localToday, type CurrencyIn } from './currency.ts';

const c = (over: Partial<CurrencyIn> = {}): CurrencyIn => ({
	licence: 'a',
	threshold_days: 60,
	current_until: '2026-04-30',
	...over
});

describe('addDays', () => {
	it('counts calendar days across months and years', () => {
		expect(addDays('2026-03-01', 60)).toBe('2026-04-30');
		expect(addDays('2026-12-31', 1)).toBe('2027-01-01');
		expect(addDays('2028-02-28', 1)).toBe('2028-02-29');
	});
});

describe('currencyState', () => {
	it('is current through the last day (day 60 for an A licence)', () => {
		expect(currencyState(c(), '2026-04-30')).toEqual({
			kind: 'current',
			until: '2026-04-30',
			text: 'Current until 30 April 2026 (USPA guidance for an A licence: 60 days).'
		});
	});

	it('is not current the day after (day 61)', () => {
		const state = currencyState(c(), '2026-05-01');
		expect(state).toMatchObject({ kind: 'lapsed', since: '2026-05-01' });
		expect(state.kind === 'lapsed' && state.text).toBe(
			'Not current since 1 May 2026: USPA recommends a supervised jump before your next solo jump. Your dropzone may require more.'
		);
	});

	it('names each licence in the guidance', () => {
		const text = (licence: CurrencyIn["licence"], days: number) => {
			const s = currencyState(c({ licence, threshold_days: days }), '2026-01-01');
			return s.kind === 'current' ? s.text : '';
		};
		expect(text('student', 30)).toContain('USPA guidance for a student: 30 days');
		expect(text('b', 90)).toContain('USPA guidance for a B licence: 90 days');
		expect(text('c', 180)).toContain('USPA guidance for a C licence: 180 days');
		expect(text('d', 180)).toContain('USPA guidance for a D licence: 180 days');
	});

	it('asks for a licence when none is set', () => {
		expect(currencyState(c({ licence: 'none', threshold_days: null, current_until: null }), '2026-01-01')).toEqual({
			kind: 'no_licence'
		});
	});

	it('says there are no jumps when a licence is set but nothing is logged', () => {
		expect(currencyState(c({ current_until: null }), '2026-01-01')).toEqual({ kind: 'no_jumps' });
	});
});

describe('localToday', () => {
	it('uses the device calendar day', () => {
		expect(localToday(new Date(2026, 10, 12, 23, 59))).toBe('2026-11-12');
	});
});
