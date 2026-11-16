import { describe, expect, it } from 'vitest';
import {
	cardPrice,
	dateIn,
	priceRows,
	tierState,
	dateStub,
	featuredLabel,
	formatPrice,
	formatRange,
	groupByMonth,
	pickFeatured,
	shortRange,
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

describe('shortRange', () => {
	it('names the start and the finish, briefly', () => {
		expect(shortRange('2026-12-24', '2026-12-31')).toBe('24–31 Dec');
		expect(shortRange('2027-03-29', '2027-04-02')).toBe('29 Mar – 2 Apr');
		expect(shortRange('2026-11-14', '2026-11-14')).toBe('14 Nov');
		expect(shortRange(null, null)).toBeNull();
	});

	it('names both years across a new year', () => {
		expect(shortRange('2027-12-30', '2028-01-02')).toBe('30 Dec 2027 – 2 Jan 2028');
	});
});

describe('groupByMonth', () => {
	const at = (id: string, starts_on: string | null) => ({ id, starts_on });

	it('groups by start month in the order given, undated last', () => {
		const groups = groupByMonth([
			at('a', '2026-11-28'),
			at('b', '2026-11-30'),
			at('c', '2026-12-30'),
			at('d', '2027-01-02'),
			at('e', null)
		]);
		expect(groups.map((g) => g.label)).toEqual([
			'November 2026',
			'December 2026',
			'January 2027',
			'Dates not announced'
		]);
		expect(groups.map((g) => g.items.map((i) => i.id))).toEqual([['a', 'b'], ['c'], ['d'], ['e']]);
	});

	it('has no undated group when every listing has dates', () => {
		expect(groupByMonth([at('a', '2027-03-01')]).map((g) => g.key)).toEqual(['2027-03']);
		expect(groupByMonth([])).toEqual([]);
	});
});

describe('date-aware pricing', () => {
	// The Christmas Boogie shape: a registration fee that rises after 14 November, in Madrid,
	// plus an optional per-jump extra.
	const registration = { label: 'Registration', currency: 'EUR', basis: 'per_person', optional: false };
	const boogie = {
		price_amount: null,
		price_currency: null,
		price_basis: null,
		time_zone: 'Europe/Madrid',
		price_tiers: [
			{ ...registration, amount: '80.00', from_on: null, until_on: '2026-11-14' },
			{ ...registration, amount: '95.00', from_on: '2026-11-15', until_on: null },
			{
				label: 'Load organising',
				amount: '4.80',
				currency: 'EUR',
				basis: 'per_jump',
				from_on: null,
				until_on: null,
				optional: true
			}
		]
	};
	const at = (iso: string) => new Date(iso);

	it("reads today's date in the listing's zone, not UTC", () => {
		// 23:30 UTC on the 14th is already the 15th in Madrid (UTC+1 in November).
		expect(dateIn('Europe/Madrid', at('2026-11-14T23:30:00Z'))).toBe('2026-11-15');
		expect(dateIn(null, at('2026-11-14T23:30:00Z'))).toBe('2026-11-14');
		expect(dateIn('Not/AZone', at('2026-11-14T23:30:00Z'))).toBe('2026-11-14');
	});

	it('treats both tier dates as inclusive', () => {
		const tier = { from_on: '2026-11-15', until_on: '2026-11-20' };
		expect(tierState(tier, '2026-11-14')).toBe('upcoming');
		expect(tierState(tier, '2026-11-15')).toBe('current');
		expect(tierState(tier, '2026-11-20')).toBe('current');
		expect(tierState(tier, '2026-11-21')).toBe('past');
	});

	it('shows the tier in effect before, on and after the boundary, never an expired one', () => {
		expect(cardPrice(boogie, at('2026-11-13T12:00:00Z'))).toBe('Registration: €80.00 per person');
		expect(cardPrice(boogie, at('2026-11-14T12:00:00Z'))).toBe('Registration: €80.00 per person');
		expect(cardPrice(boogie, at('2026-11-14T23:30:00Z'))).toBe('Registration: €95.00 per person');
		expect(cardPrice(boogie, at('2026-11-16T12:00:00Z'))).toBe('Registration: €95.00 per person');
	});

	it('says "See pricing" when no single required tier applies', () => {
		const undated = boogie.price_tiers.map((t) => ({ ...t, from_on: null, until_on: null }));
		expect(cardPrice({ ...boogie, price_tiers: undated }, at('2026-11-16T12:00:00Z'))).toBe(
			'See pricing'
		);
		const lapsed = { ...boogie, price_tiers: [boogie.price_tiers[0]] };
		expect(cardPrice(lapsed, at('2026-11-16T12:00:00Z'))).toBe('See pricing');
	});

	it('keeps fixed and unknown prices as they were', () => {
		const fixed = {
			price_amount: '1225.00',
			price_currency: 'EUR',
			price_basis: 'per_person',
			time_zone: null
		};
		expect(cardPrice(fixed)).toBe('€1,225.00 per person');
		expect(cardPrice({ ...fixed, price_tiers: [] })).toBe('€1,225.00 per person');
		const unknown = { price_amount: null, price_currency: null, price_basis: null, time_zone: null };
		expect(cardPrice(unknown)).toBeNull();
		expect(priceRows(fixed)).toEqual([]);
	});

	it('lists every tier for the event page with its dates, state and kind', () => {
		expect(priceRows(boogie, at('2026-11-16T12:00:00Z'))).toEqual([
			{
				label: 'Registration',
				price: '€80.00 per person',
				when: 'Until 14 November 2026',
				state: 'past',
				optional: false
			},
			{
				label: 'Registration',
				price: '€95.00 per person',
				when: 'From 15 November 2026',
				state: 'current',
				optional: false
			},
			{ label: 'Load organising', price: '€4.80 per jump', when: null, state: 'current', optional: true }
		]);
		const windowed = { ...boogie, price_tiers: [{ ...boogie.price_tiers[0], from_on: '2026-11-01' }] };
		expect(priceRows(windowed, at('2026-10-20T12:00:00Z'))[0]).toMatchObject({
			when: '1–14 November 2026',
			state: 'upcoming'
		});
	});
});
