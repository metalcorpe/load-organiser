/**
 * Logbook search and filters, parsed from the /jumps URL (a plain GET form, so it works
 * without JavaScript and every filter stays in the address). Only well-formed values
 * pass; anything else is dropped, as on the listings board. Client-safe.
 */
import { JUMP_TYPE_LABEL } from './jumps.ts';

export interface JumpFilters {
	q: string;
	type: string;
	/** `venue:<id>` or `place:<id>`: one listed dropzone or one private place. */
	at: string;
	from: string;
	to: string;
	from_number: string;
	to_number: string;
}

export const NO_FILTERS: JumpFilters = {
	q: '',
	type: '',
	at: '',
	from: '',
	to: '',
	from_number: '',
	to_number: ''
};

const DATE = /^\d{4}-\d{2}-\d{2}$/;
const AT = /^(venue|place):[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const NUMBER = /^\d{1,7}$/;

function validDate(raw: string | null): string {
	if (!raw || !DATE.test(raw)) return '';
	const parsed = new Date(`${raw}T00:00:00Z`);
	return !Number.isNaN(parsed.getTime()) && parsed.toISOString().startsWith(raw) ? raw : '';
}

function validNumber(raw: string | null): string {
	const value = (raw ?? '').trim();
	if (!NUMBER.test(value)) return '';
	const n = Number(value);
	return n >= 1 && n <= 1_000_000 ? String(n) : '';
}

export function parseJumpFilters(params: URLSearchParams): JumpFilters {
	const type = params.get('type') ?? '';
	const at = (params.get('at') ?? '').toLowerCase();
	return {
		q: (params.get('q') ?? '').trim().slice(0, 100),
		type: type in JUMP_TYPE_LABEL ? type : '',
		at: AT.test(at) ? at : '',
		from: validDate(params.get('from')),
		to: validDate(params.get('to')),
		from_number: validNumber(params.get('from_number')),
		to_number: validNumber(params.get('to_number'))
	};
}

export function hasJumpFilters(filters: JumpFilters): boolean {
	return Object.values(filters).some(Boolean);
}

/** The logbook URL for these filters (and optional page cursor); empty values are omitted. */
export function jumpsHref(filters: JumpFilters, cursor?: string): string {
	const params = new URLSearchParams();
	for (const [key, value] of Object.entries(filters)) if (value) params.set(key, value);
	if (cursor) params.set('cursor', cursor);
	const search = params.toString();
	return search ? `/jumps?${search}` : '/jumps';
}

/** The API's query parameters for these filters. */
export function jumpsQuery(filters: JumpFilters): Record<string, string | undefined> {
	const [kind, id] = filters.at ? filters.at.split(':') : [];
	return {
		q: filters.q || undefined,
		jump_type: filters.type || undefined,
		venue_id: kind === 'venue' ? id : undefined,
		place_id: kind === 'place' ? id : undefined,
		from_date: filters.from || undefined,
		to_date: filters.to || undefined,
		number_from: filters.from_number || undefined,
		number_to: filters.to_number || undefined
	};
}

/** "1 h 2 min", "9 min 30 s", "45 s". */
export function formatDuration(seconds: number): string {
	const h = Math.floor(seconds / 3600);
	const m = Math.floor((seconds % 3600) / 60);
	const s = seconds % 60;
	if (h > 0) return m > 0 ? `${h} h ${m} min` : `${h} h`;
	if (m > 0) return s > 0 ? `${m} min ${s} s` : `${m} min`;
	return `${s} s`;
}

/** The freefall total for a filtered set, saying how many jumps it covers. */
export function freefallText(total: number | null, recorded: number, jumps: number): string | null {
	if (total === null || recorded === 0) return null;
	const sum = formatDuration(total);
	return recorded === jumps ? `${sum} of freefall` : `${sum} of freefall (recorded on ${recorded} of ${jumps})`;
}
