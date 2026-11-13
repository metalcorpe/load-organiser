/** Board filters parsed from the URL: only known values pass; everything else is dropped. */
import { isCountryCode } from '#lib/countries.ts';
import { safeReturnPath } from '#lib/safe-return.ts';

export const CATEGORY_VALUES = ['event', 'boogie', 'camp', 'course'] as const;
export const DISCIPLINE_VALUES = [
	'belly',
	'freefly',
	'angle',
	'wingsuit',
	'canopy',
	'crw',
	'accuracy'
] as const;
export const AUDIENCE_VALUES = ['students', 'licensed', 'experienced'] as const;

export interface BoardFilters {
	q: string;
	category: string;
	country: string;
	discipline: string;
	audience: string;
	from: string;
	to: string;
}

const DATE = /^\d{4}-\d{2}-\d{2}$/;

function validDate(raw: string | null): string {
	if (!raw || !DATE.test(raw)) return '';
	const parsed = new Date(`${raw}T00:00:00Z`);
	return !Number.isNaN(parsed.getTime()) && parsed.toISOString().startsWith(raw) ? raw : '';
}

function pick(raw: string | null, allowed: readonly string[]): string {
	return raw && allowed.includes(raw) ? raw : '';
}

export function parseFilters(params: URLSearchParams): BoardFilters {
	const country = (params.get('country') ?? '').toUpperCase();
	return {
		q: (params.get('q') ?? '').trim().slice(0, 80),
		category: pick(params.get('category'), CATEGORY_VALUES),
		country: isCountryCode(country) ? country : '',
		discipline: pick(params.get('discipline'), DISCIPLINE_VALUES),
		audience: pick(params.get('audience'), AUDIENCE_VALUES),
		from: validDate(params.get('from')),
		to: validDate(params.get('to'))
	};
}

export function hasFilters(filters: BoardFilters): boolean {
	return Object.values(filters).some(Boolean);
}

/** The board URL for these filters (and optional page cursor); empty values are omitted. */
export function boardHref(filters: BoardFilters, cursor?: string): string {
	const params = new URLSearchParams();
	for (const [key, value] of Object.entries(filters)) if (value) params.set(key, value);
	if (cursor) params.set('cursor', cursor);
	const search = params.toString();
	return search ? `/?${search}` : '/';
}

/** Any absolute base works: only the path and query of a checked local path are read. */
const BOARD_BASE = 'https://board.invalid';

/**
 * The board search an event was opened from ("Back to results"), from an untrusted `results`
 * parameter. Only a local path to the board itself passes (no other page, host, scheme or
 * backslash: safeReturnPath first), and it is rebuilt from its known filters and page cursor,
 * so nothing else in it survives. The plain board (no filters, first page) is not a search
 * context: null, and the event page offers only "All events".
 */
export function resultsPath(raw: string | null | undefined): string | null {
	const path = safeReturnPath(raw);
	if (!path) return null;
	const url = new URL(path, BOARD_BASE);
	if (url.pathname !== '/') return null;
	const cursor = (url.searchParams.get('cursor') ?? '').slice(0, 512);
	const href = boardHref(parseFilters(url.searchParams), cursor || undefined);
	return href === '/' ? null : href;
}

/** Longest return path the sign-in pages accept (safeReturnPath). */
const RETURN_LIMIT = 512;

/**
 * An event's address, optionally carrying the board search it was opened from and the
 * "sign in to save" intent. A search context too long to survive the sign-in round trip is
 * dropped, rather than the sign-in losing the whole return path.
 */
export function eventHref(
	id: string,
	{ results, save = false }: { results?: string | null; save?: boolean } = {}
): string {
	const params = new URLSearchParams();
	if (save) params.set('save', '1');
	const context = resultsPath(results);
	if (context) params.set('results', context);
	const search = params.toString();
	const href = search ? `/events/${id}?${search}` : `/events/${id}`;
	return href.length > RETURN_LIMIT && context ? eventHref(id, { save }) : href;
}
