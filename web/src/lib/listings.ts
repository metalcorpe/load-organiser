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

/** How many calendar days a listing runs, both ends included; 0 when undated. */
export function spanDays(start: string | null, end: string | null): number {
	if (!start || !end) return 0;
	return Math.round((day(end).getTime() - day(start).getTime()) / 86_400_000) + 1;
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
				spanDays(i.starts_on, i.ends_on) > 1 &&
				(i.starts_on ?? '') > today
		) ?? null
	);
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
