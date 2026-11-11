import { describe, expect, it } from 'vitest';
import { dateStub, formatPrice, formatRange, spanDays, statusLabel } from './listings.ts';

describe('formatRange', () => {
	it('formats calendar dates without shifting them', () => {
		expect(formatRange('2027-07-10', '2027-07-14')).toBe('10–14 July 2027');
		expect(formatRange('2027-06-28', '2027-07-03')).toBe('28 June – 3 July 2027');
		expect(formatRange('2026-12-30', '2027-01-02')).toBe('30 December 2026 – 2 January 2027');
		expect(formatRange('2027-01-01', '2027-01-01')).toBe('1 January 2027');
		expect(formatRange(null, null)).toBe('Dates not announced');
	});
});

describe('listing labels', () => {
	it('states prices with their basis and never invents one', () => {
		expect(formatPrice('1250.50', 'EUR', 'per_person')).toBe('€1,250.50 per person');
		expect(formatPrice(null, null, null)).toBeNull();
	});

	it('labels status without implying availability', () => {
		expect(statusLabel('published', false)).toBeNull();
		expect(statusLabel('published', true)).toBe('Ended');
		expect(statusLabel('cancelled', true)).toBe('Cancelled');
	});
});

describe('dateStub', () => {
	it('shows the start and how far the listing runs', () => {
		expect(dateStub('2026-12-24', '2026-12-31')).toEqual({ month: 'Dec', day: '24', until: '–31' });
		expect(dateStub('2027-06-28', '2027-07-03')).toEqual({ month: 'Jun', day: '28', until: '–3 Jul' });
		expect(dateStub('2026-11-14', '2026-11-14')).toEqual({ month: 'Nov', day: '14', until: null });
		expect(dateStub(null, null)).toBeNull();
	});
});

describe('spanDays', () => {
	it('counts both ends, across months and years', () => {
		expect(spanDays('2026-12-24', '2026-12-31')).toBe(8);
		expect(spanDays('2026-12-30', '2027-01-02')).toBe(4);
		expect(spanDays('2026-11-14', '2026-11-14')).toBe(1);
		expect(spanDays(null, null)).toBe(0);
	});
});
