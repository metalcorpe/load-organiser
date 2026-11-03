/** Board filters parsed from the URL: only known values pass; everything else is dropped. */
import { isCountryCode } from '#lib/countries.ts';

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
