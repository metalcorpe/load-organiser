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

/** Both dates given and "to" before "from": no event can be available in that window. */
export function datesOutOfOrder(filters: Pick<BoardFilters, 'from' | 'to'>): boolean {
	return Boolean(filters.from && filters.to && filters.to < filters.from);
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

/**
 * Longest board search accepted as a context. A search of 80 characters of text, every
 * filter and a page cursor fits; the same local-path checks apply as for any return path.
 */
export const RESULTS_LIMIT = 2048;

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
	const path = safeReturnPath(raw, RESULTS_LIMIT);
	if (!path) return null;
	const url = new URL(path, BOARD_BASE);
	if (url.pathname !== '/') return null;
	const cursor = (url.searchParams.get('cursor') ?? '').slice(0, 512);
	const href = boardHref(parseFilters(url.searchParams), cursor || undefined);
	return href === '/' ? null : href;
}

/** Longest return path the sign-in pages accept (safeReturnPath checks the decoded value). */
const RETURN_LIMIT = 512;
/** A sane cap for an ordinary link: the board URL is encoded twice inside it. */
const LINK_LIMIT = 4096;

/**
 * An event's address, optionally carrying the board search it was opened from and the
 * "sign in to save" intent. The context is dropped when the address would be too long: for
 * the sign-in return path (`save`), past what sign-in accepts, so the return itself is never
 * lost (the server then carries the context another way: results-context.ts); for an
 * ordinary link, only past a generous cap.
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
	const limit = save ? RETURN_LIMIT : LINK_LIMIT;
	return href.length > limit && context ? eventHref(id, { save }) : href;
}
