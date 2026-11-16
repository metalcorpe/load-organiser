/** Labels, date formatting and messages for listings, saves and plans (#150). */

export const CATEGORY_LABEL: Record<string, string> = {
	event: 'Event',
	boogie: 'Boogie',
	camp: 'Camp',
	course: 'Course'
};

export const DISCIPLINE_LABEL: Record<string, string> = {
	belly: 'Belly',
	freefly: 'Freefly',
	angle: 'Angle / tracking',
	wingsuit: 'Wingsuit',
	canopy: 'Canopy',
	crw: 'Canopy formation (CRW)',
	accuracy: 'Accuracy'
};

export const AUDIENCE_LABEL: Record<string, string> = {
	students: 'Students',
	licensed: 'Licensed jumpers',
	experienced: 'Experienced jumpers'
};

export const PRICE_BASIS_LABEL: Record<string, string> = {
	per_person: 'per person',
	per_jump: 'per jump',
	per_day: 'per day'
};

const DAY = new Intl.DateTimeFormat('en-GB', {
	dateStyle: 'long',
	timeZone: 'UTC'
});
const MONTH_DAY = new Intl.DateTimeFormat('en-GB', {
	day: 'numeric',
	month: 'long',
	timeZone: 'UTC'
});
const LANGUAGES = new Intl.DisplayNames(['en'], { type: 'language' });

/** A calendar date (YYYY-MM-DD) as that day, never shifted by a time zone. */
function day(value: string): Date {
	return new Date(`${value}T00:00:00Z`);
}

export function formatDay(value: string): string {
	return DAY.format(day(value));
}

export function formatRange(start: string | null, end: string | null): string {
	if (!start || !end) return 'Dates not announced';
	if (start === end) return formatDay(start);
	// Built by hand so every runtime renders the same text (ICU range output varies).
	const [sy, sm] = start.split('-');
	const [ey, em] = end.split('-');
	const startDay = Number(start.slice(8));
	if (sy === ey && sm === em) return `${startDay}–${formatDay(end)}`;
	const startText = sy === ey ? MONTH_DAY.format(day(start)) : formatDay(start);
	return `${startText} – ${formatDay(end)}`;
}

const MONTH_SHORT = new Intl.DateTimeFormat('en-GB', { month: 'short', timeZone: 'UTC' });

/** The card's date tile: start month and day; null when undated. */
export interface DateStub {
	month: string;
	day: string;
}

export function dateStub(start: string | null, end: string | null): DateStub | null {
	if (!start || !end) return null;
	return { month: MONTH_SHORT.format(day(start)), day: String(Number(start.slice(8))) };
}

/**
 * A card's dates in short, start and finish: "24–31 Dec", "29 Mar – 2 Apr", and both years
 * across a new year ("30 Dec 2027 – 2 Jan 2028"); one day is "24 Dec"; null when undated. The
 * year is otherwise left out: cards sit under their month's heading, which names it.
 */
export function shortRange(start: string | null, end: string | null): string | null {
	if (!start || !end) return null;
	const short = (value: string) => `${Number(value.slice(8))} ${MONTH_SHORT.format(day(value))}`;
	if (start === end) return short(start);
	const [sy, sm] = start.split('-');
	const [ey, em] = end.split('-');
	if (sy !== ey) return `${short(start)} ${sy} – ${short(end)} ${ey}`;
	if (sm !== em) return `${short(start)} – ${short(end)}`;
	return `${Number(start.slice(8))}–${short(end)}`;
}

/** The fields the board's highlight is chosen by. */
export interface FeaturedCandidate {
	category: string;
	status: string;
	starts_on: string | null;
	ends_on: string | null;
}

/**
 * The board's highlighted card: the first listing (results come in start-date order) that is a
 * published, multi-day boogie or camp starting after `today` (YYYY-MM-DD). Nothing more is
 * known about it (not its size, popularity or importance), so its wording says only that.
 */
export function pickFeatured<T extends FeaturedCandidate>(items: readonly T[], today: string): T | null {
	return (
		items.find(
			(i) =>
				(i.category === 'boogie' || i.category === 'camp') &&
				i.status === 'published' &&
				i.ends_on !== i.starts_on &&
				(i.starts_on ?? '') > today
		) ?? null
	);
}

const MONTH_YEAR = new Intl.DateTimeFormat('en-GB', {
	month: 'long',
	year: 'numeric',
	timeZone: 'UTC'
});

export interface MonthGroup<T> {
	/** "2026-11", or "undated". */
	key: string;
	/** "November 2026", or "Dates not announced". */
	label: string;
	items: T[];
}

/**
 * The board's listings under month headings, by start month (an event running into the next
 * month stays under the month it starts in). Months keep the order the listings came in (start
 * date order); undated listings, if any, form a last "Dates not announced" group.
 */
export function groupByMonth<T extends { starts_on: string | null }>(
	items: readonly T[]
): MonthGroup<T>[] {
	const groups = new Map<string, MonthGroup<T>>();
	let undated: MonthGroup<T> | null = null;
	for (const item of items) {
		if (!item.starts_on) {
			undated ??= { key: 'undated', label: 'Dates not announced', items: [] };
			undated.items.push(item);
			continue;
		}
		const key = item.starts_on.slice(0, 7);
		let group = groups.get(key);
		if (!group) {
			group = { key, label: MONTH_YEAR.format(day(`${key}-01`)), items: [] };
			groups.set(key, group);
		}
		group.items.push(item);
	}
	return undated ? [...groups.values(), undated] : [...groups.values()];
}

/** "Upcoming boogie", "Upcoming camp": what the selection above supports, and no more. */
export function featuredLabel(category: string): string {
	return `Upcoming ${(CATEGORY_LABEL[category] ?? 'event').toLowerCase()}`;
}

export function languageName(code: string): string {
	try {
		return LANGUAGES.of(code) ?? code;
	} catch {
		return code;
	}
}

export function formatPrice(
	amount: string | null,
	currency: string | null,
	basis: string | null
): string | null {
	if (!amount || !currency) return null;
	let money: string;
	try {
		money = new Intl.NumberFormat('en-GB', {
			style: 'currency',
			currency
		}).format(Number(amount));
	} catch {
		money = `${amount} ${currency}`;
	}
	return basis ? `${money} ${PRICE_BASIS_LABEL[basis] ?? ''}`.trim() : money;
}

/**
 * One dated or undated charge, as the organizer states it (see the API's PriceTierOut).
 * `from_on`/`until_on` are inclusive calendar dates in the listing's own time zone.
 */
export interface PriceTier {
	label: string;
	amount: string;
	currency: string;
	basis: string;
	from_on: string | null;
	until_on: string | null;
	optional: boolean;
}

/** Rows the reviewer form offers for a price list; the API accepts at most this many. */
export const PRICE_TIER_ROWS = 6;

/** What pricing is read from: a single stated price, or tiers that replace it. */
export interface Priced {
	price_amount: string | null;
	price_currency: string | null;
	price_basis: string | null;
	price_tiers?: readonly PriceTier[];
	time_zone: string | null;
}

/** Today's calendar date (YYYY-MM-DD) in `zone`, the listing's place; UTC without one. */
export function dateIn(zone: string | null, now: Date = new Date()): string {
	const parts = (timeZone: string) => {
		const found = Object.fromEntries(
			new Intl.DateTimeFormat('en-GB', {
				timeZone,
				year: 'numeric',
				month: '2-digit',
				day: '2-digit'
			})
				.formatToParts(now)
				.map((p) => [p.type, p.value])
		);
		return `${found.year}-${found.month}-${found.day}`;
	};
	try {
		return parts(zone ?? 'UTC');
	} catch {
		return parts('UTC');
	}
}

export type TierState = 'past' | 'current' | 'upcoming';

/** Whether a tier applies on `today`: both of its dates are inclusive. */
export function tierState(tier: Pick<PriceTier, 'from_on' | 'until_on'>, today: string): TierState {
	if (tier.until_on && today > tier.until_on) return 'past';
	if (tier.from_on && today < tier.from_on) return 'upcoming';
	return 'current';
}

/**
 * A card's one price line, or null when no price is stated.
 *
 * - A single stated price is shown as it is ("€80.00 per person").
 * - With tiers, only a required tier in effect today in the listing's zone is shown, with its
 *   label ("Registration: €95.00 per person"). An expired tier is never shown as current.
 * - When no single required tier applies today (none, or several at once), the card says
 *   "See pricing" and the event page lists the tiers.
 */
export function cardPrice(item: Priced, now: Date = new Date()): string | null {
	const tiers = item.price_tiers ?? [];
	if (!tiers.length) return formatPrice(item.price_amount, item.price_currency, item.price_basis);
	const today = dateIn(item.time_zone, now);
	const current = tiers.filter((t) => !t.optional && tierState(t, today) === 'current');
	if (current.length !== 1) return 'See pricing';
	const [tier] = current;
	return `${tier.label}: ${formatPrice(tier.amount, tier.currency, tier.basis)}`;
}

export interface PriceRow {
	label: string;
	price: string;
	/** "Until 14 November 2026", "From 15 November 2026", "1–14 November 2026" or null. */
	when: string | null;
	state: TierState;
	optional: boolean;
}

/** Every tier for the event page, in the organizer's order, each with its own state. */
export function priceRows(item: Priced, now: Date = new Date()): PriceRow[] {
	const today = dateIn(item.time_zone, now);
	return (item.price_tiers ?? []).map((t) => ({
		label: t.label,
		price: formatPrice(t.amount, t.currency, t.basis) ?? `${t.amount} ${t.currency}`,
		when:
			t.from_on && t.until_on
				? formatRange(t.from_on, t.until_on)
				: t.until_on
					? `Until ${formatDay(t.until_on)}`
					: t.from_on
						? `From ${formatDay(t.from_on)}`
						: null,
		state: tierState(t, today),
		optional: t.optional
	}));
}

/** Plain status wording; nothing here implies availability or registration. */
export function statusLabel(status: string, ended: boolean): string | null {
	if (status === 'cancelled') return 'Cancelled';
	if (status === 'postponed') return 'Postponed';
	if (ended) return 'Ended';
	return null;
}

export function hostOf(url: string): string {
	try {
		return new URL(url).hostname;
	} catch {
		return url;
	}
}

/** User-facing text for listing, save and plan outcomes. No upstream detail is shown. */
export const LISTING_MESSAGES: Record<string, string> = {
	missing: 'Fill in the title and both dates.',
	not_found: 'That item no longer exists.',
	not_authenticated: 'Your session has ended. Sign in again.',
	email_unverified: 'Confirm your email address before saving privately.',
	saved_limit_reached:
		'You have reached the limit of 200 saved listings. Remove one to save another.',
	plan_limit_reached: 'You have reached the limit of 100 plans. Remove one to add another.',
	title_required: 'Enter a title.',
	title_too_long: 'Use at most 120 characters for the title.',
	note_too_long: 'Use at most 500 characters for the note.',
	dates_required: 'Enter both dates.',
	dates_out_of_order: 'The last day cannot be before the first day.',
	dates_span_too_long: 'A plan can cover at most one year.',
	plan_link_conflict: 'A plan can be linked to one listing, dropzone or place.',
	opportunity_unavailable: 'That listing is no longer published.',
	venue_not_listed: 'That dropzone is not listed.',
	place_unknown: 'That private place no longer exists.',
	cursor_invalid: 'That page of results is no longer valid. Search again.',
	invalid_input: 'Check the details you entered.',
	uncertain:
		'The service did not answer in time. The change may or may not have been saved; reload to check before trying again.',
	unavailable: 'The service is unavailable right now. Try again later.'
};

export function listingMessage(code: string | undefined): string | undefined {
	return code ? (LISTING_MESSAGES[code] ?? LISTING_MESSAGES.unavailable) : undefined;
}

export function listingStatus(reason: string): number {
	switch (reason) {
		case 'not_authenticated':
			return 401;
		case 'email_unverified':
			return 403;
		case 'not_found':
			return 404;
		case 'saved_limit_reached':
		case 'plan_limit_reached':
			return 409;
		case 'unavailable':
		case 'uncertain':
			return 503;
		default:
			return 400;
	}
}
