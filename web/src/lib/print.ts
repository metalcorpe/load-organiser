/** The printable logbook (/records/print): rows, pages and totals. Client-safe, no I/O. */
import type { JumpOut } from './contracts/index.ts';
import { JUMP_TYPE_LABEL } from './jumps.ts';

/** Rows on one printed sheet: fits A4 or Letter in landscape with room for signatures. */
export const ROWS_PER_PAGE = 12;
/** The logbook holds at most 2,000 jumps; the page never asks for more. */
export const MAX_PRINT_JUMPS = 2000;
export const NOTES_MAX = 80;

export interface Totals {
	jumps: number;
	/** Recorded freefall seconds; entries without a freefall time add nothing. */
	freefall: number;
}

export interface PrintRow {
	id: string;
	number: string;
	date: string;
	place: string;
	type: string;
	exit: string;
	freefall: string;
	equipment: string;
	notes: string;
}

export interface PrintPage {
	number: number;
	rows: PrintRow[];
	page: Totals;
	broughtForward: Totals;
	toDate: Totals;
}

const SHORT_DAY = new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium', timeZone: 'UTC' });

/** A calendar date (YYYY-MM-DD) as a short day, never shifted by a time zone. */
export function shortDay(value: string): string {
	return SHORT_DAY.format(new Date(`${value}T00:00:00Z`));
}

/** Freefall time in plain units: "45 s", "1 min 5 s", "2 h 3 min 0 s". */
export function formatFreefall(seconds: number): string {
	const s = Math.max(0, Math.floor(seconds));
	const h = Math.floor(s / 3600);
	const m = Math.floor((s % 3600) / 60);
	const rest = s % 60;
	if (h > 0) return `${h} h ${m} min ${rest} s`;
	if (m > 0) return `${m} min ${rest} s`;
	return `${rest} s`;
}

/** At most `max` characters, cut at a word where possible, with an ellipsis when cut. */
export function truncate(text: string, max = NOTES_MAX): string {
	const flat = text.replace(/\s+/g, ' ').trim();
	if (flat.length <= max) return flat;
	const cut = flat.slice(0, max - 1);
	const space = cut.lastIndexOf(' ');
	return `${(space > max / 2 ? cut.slice(0, space) : cut).trimEnd()}…`;
}

export function placeName(location: JumpOut['location']): string {
	return location.name ?? (location.kind === 'venue' ? 'Dropzone no longer listed' : 'Private place');
}

export function exitText(jump: Pick<JumpOut, 'exit_altitude' | 'altitude_unit' | 'altitude_datum'>): string {
	if (jump.exit_altitude === null || !jump.altitude_unit) return '';
	const datum = jump.altitude_datum === 'unspecified' ? '' : ` ${jump.altitude_datum.toUpperCase()}`;
	return `${jump.exit_altitude.toLocaleString('en-GB')} ${jump.altitude_unit}${datum}`;
}

export function equipmentText(jump: Pick<JumpOut, 'components' | 'other_gear'>): string {
	const parts = jump.components.map((c) => c.label);
	if (jump.other_gear) parts.push(jump.other_gear);
	return parts.join(', ');
}

export function toRow(jump: JumpOut, { notes }: { notes: boolean }): PrintRow {
	return {
		id: jump.id,
		number: jump.jump_number === null ? '' : String(jump.jump_number),
		date: shortDay(jump.jumped_on),
		place: placeName(jump.location),
		type: JUMP_TYPE_LABEL[jump.jump_type] ?? jump.jump_type,
		exit: exitText(jump),
		freefall: jump.freefall_seconds === null ? '' : formatFreefall(jump.freefall_seconds),
		equipment: equipmentText(jump),
		notes: notes && jump.notes ? truncate(jump.notes) : ''
	};
}

const add = (a: Totals, b: Totals): Totals => ({
	jumps: a.jumps + b.jumps,
	freefall: a.freefall + b.freefall
});

/**
 * Sheets of `perPage` rows in the given order, like a paper logbook: each sheet's own
 * totals, what was brought forward to it, and the total to date after it. `before`
 * holds the entries dated before the chosen range.
 */
export function paginate(
	jumps: JumpOut[],
	{ notes, before, perPage = ROWS_PER_PAGE }: { notes: boolean; before: Totals; perPage?: number }
): PrintPage[] {
	const pages: PrintPage[] = [];
	let carried = before;
	for (let start = 0; start < jumps.length; start += perPage) {
		const slice = jumps.slice(start, start + perPage);
		const page: Totals = {
			jumps: slice.length,
			freefall: slice.reduce((sum, j) => sum + (j.freefall_seconds ?? 0), 0)
		};
		const toDate = add(carried, page);
		pages.push({
			number: pages.length + 1,
			rows: slice.map((j) => toRow(j, { notes })),
			page,
			broughtForward: carried,
			toDate
		});
		carried = toDate;
	}
	return pages;
}

export const PRINT_MESSAGES: Record<string, string> = {
	date_range_invalid: 'The start date must be on or before the end date.',
	not_authenticated: 'Your session has ended. Sign in again.',
	invalid_input: 'Check the dates you entered.',
	uncertain: 'The service did not answer in time. Reload the page to try again.',
	unavailable: 'The service is unavailable right now. Try again later.'
};

export function printMessage(code: string): string {
	return PRINT_MESSAGES[code] ?? PRINT_MESSAGES.unavailable;
}

const DATE = /^\d{4}-\d{2}-\d{2}$/;

/** A YYYY-MM-DD query value that is a real calendar date, else ''. */
export function dateParam(raw: string | null): string {
	const value = (raw ?? '').trim();
	if (!DATE.test(value)) return '';
	const parsed = new Date(`${value}T00:00:00Z`);
	return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value ? value : '';
}
