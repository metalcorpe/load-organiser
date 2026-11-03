import { describe, expect, it } from 'vitest';
import { formatPrice, formatRange, statusLabel } from './listings.ts';

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
