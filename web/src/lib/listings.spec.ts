import { describe, expect, it } from 'vitest';
import {
	dateStub,
	featuredLabel,
	formatPrice,
	formatRange,
	pickFeatured,
	spanDays,
	statusLabel
} from './listings.ts';

describe('formatRange', () => {
	it('formats calendar dates without shifting them', () => {
		expect(formatRange('2027-07-10', '2027-07-14')).toBe('10–14 July 2027');
		expect(formatRange('2027-06-28', '2027-07-03')).toBe('28 June – 3 July 2027');
		expect(formatRange('2026-12-30', '2027-01-02')).toBe('30 December 2026 – 2 January 2027');
		expect(formatRange('2027-01-01', '2027-01-01')).toBe('1 January 2027');
		expect(formatRange(null, null)).toBe('Dates not announced');
	});

	it('names the year once within a year and both years across one', () => {
		expect(formatRange('2027-01-30', '2027-02-02')).toBe('30 January – 2 February 2027');
		expect(formatRange('2027-12-31', '2028-01-01')).toBe('31 December 2027 – 1 January 2028');
	});
});

describe('the highlighted listing', () => {
	const base = { status: 'published', starts_on: '2027-07-10', ends_on: '2027-07-14' };

	it('is the first upcoming multi-day boogie or camp, in the order given', () => {
		const items = [
			{ id: 'course', ...base, category: 'course' },
			{ id: 'one-day', ...base, category: 'boogie', ends_on: '2027-07-10' },
			{ id: 'cancelled', ...base, category: 'boogie', status: 'cancelled' },
			{ id: 'camp', ...base, category: 'camp', starts_on: '2027-07-11' },
			{ id: 'boogie', ...base, category: 'boogie', starts_on: '2027-07-12' }
		];
		expect(pickFeatured(items, '2027-01-01')?.id).toBe('camp');
	});

	it('is never one that has started, or an undated one', () => {
		const items = [
			{ id: 'today', ...base, category: 'boogie', starts_on: '2027-07-10' },
			{ id: 'undated', ...base, category: 'camp', starts_on: null, ends_on: null }
		];
		expect(pickFeatured(items, '2027-07-10')).toBeNull();
		expect(pickFeatured(items, '2027-07-09')?.id).toBe('today');
	});

	it('is described by what the selection knows: its type and that it is upcoming', () => {
		expect(featuredLabel('boogie')).toBe('Upcoming boogie');
		expect(featuredLabel('camp')).toBe('Upcoming camp');
		expect(featuredLabel('boogie')).not.toMatch(/big|next/i);
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
	it('shows the start month and day', () => {
		expect(dateStub('2026-12-24', '2026-12-31')).toEqual({ month: 'Dec', day: '24' });
		expect(dateStub('2027-06-28', '2027-07-03')).toEqual({ month: 'Jun', day: '28' });
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
