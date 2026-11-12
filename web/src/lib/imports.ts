/** Labels and messages for importing a logbook from a spreadsheet. Client-safe. */

export const IMPORT_FIELDS = [
	'date',
	'number',
	'place',
	'type',
	'altitude',
	'freefall',
	'notes'
] as const;

export type ImportField = (typeof IMPORT_FIELDS)[number];

export const FIELD_LABEL: Record<ImportField, string> = {
	date: 'Date',
	number: 'Jump number',
	place: 'Dropzone or place',
	type: 'Type',
	altitude: 'Exit altitude',
	freefall: 'Freefall (seconds)',
	notes: 'Notes'
};

export const DATE_ORDER_LABEL: Record<string, string> = {
	dmy: 'Day/month/year (31/12/2024)',
	mdy: 'Month/day/year (12/31/2024)',
	ymd: 'Year-month-day (2024-12-31)'
};

export const PLACE_KIND_LABEL: Record<string, string> = {
	venue: 'listed dropzone',
	place: 'your private place',
	new_place: 'new private place'
};

/** Why a row was skipped, in words. Keyed by the API's row problem code. */
export const ROW_PROBLEMS: Record<string, string> = {
	jump_date_required: 'no date',
	jump_date_invalid: 'the date is not a real date in the chosen order',
	jump_date_in_future: 'the date is in the future',
	jump_number_invalid: 'the jump number is not a whole number of 1 or more',
	location_required: 'no dropzone or place',
	place_too_long: 'the place name is longer than 120 characters',
	place_ambiguous:
		'more than one listed dropzone has this name; choose the country it is in, or write the name differently',
	altitude_invalid: 'the altitude is not a whole number in the chosen unit, or is too high',
	freefall_invalid: 'the freefall time is not between 0 and 600 seconds',
	notes_too_long: 'the notes are longer than 2,000 characters',
	likely_duplicate: 'it looks like a jump already in your logbook',
	repeated_in_file: 'its jump number is used by an earlier row of the file'
};

export function rowProblem(code: string): string {
	return ROW_PROBLEMS[code] ?? 'this row could not be read';
}

export const IMPORT_MESSAGES: Record<string, string> = {
	file_required: 'Choose a spreadsheet file (.csv).',
	file_too_large:
		'That file is larger than 1 MB. Split it into smaller files and import them one at a time. Nothing was changed.',
	file_unreadable:
		'That file could not be read as a spreadsheet. Save it as CSV (CSV UTF-8 if your spreadsheet offers it) and try again. Nothing was changed.',
	header_required:
		'The file is empty or has no headings. Put the column headings (such as Date and Dropzone) in the first row.',
	too_many_rows:
		'That file has more than 2,000 rows. Split it into smaller files. Nothing was changed.',
	too_many_columns: 'That file has more than 100 columns. Remove the columns you do not need.',
	date_column_required: 'Choose which column holds the date.',
	place_column_required: 'Choose which column holds the dropzone or place.',
	mapping_invalid: 'Each column can be used for one thing only. Check the column choices.',
	country_required:
		'Some places are not in the directory. Choose the country to create them in as private places.',
	country_invalid: 'Choose a country from the list.',
	nothing_to_import: 'Every row is skipped, so there is nothing to import. Nothing was changed.',
	jump_limit_reached:
		'This import would take your logbook over 2,000 jumps. Nothing was changed. Remove rows from the file, or jumps from your logbook, and try again.',
	place_limit_reached: 'This import would take you over 200 private places. Nothing was changed.',
	import_changed:
		'The file or choices are not the ones you checked. Nothing was changed. Check the file again, then import.',
	import_busy: 'Another import was being saved at the same time. Nothing was changed. Try again.',
	already_undone: 'This import was already undone.',
	not_found: 'That import no longer exists.',
	confirm_undo: 'Tick the box to confirm deleting the jumps from this import.',
	confirm_required: 'Tick the box to confirm deleting the jumps from this import.',
	email_unverified: 'Confirm your email address before importing.',
	too_many_attempts: 'Too many attempts. Wait a while and try again.',
	not_authenticated: 'Your session has ended. Sign in again.',
	uncertain:
		'Not confirmed: the service did not answer in time. Check the file again: if it was imported, it shows as already imported and nothing is applied twice.',
	unavailable: 'The service is unavailable right now. Nothing was changed. Try again later.',
	invalid_input: 'Something in the request was not accepted. Nothing was changed.'
};

export function importMessage(code: string | undefined): string | undefined {
	return code ? (IMPORT_MESSAGES[code] ?? IMPORT_MESSAGES.invalid_input) : undefined;
}

const n = (value: number) => value.toLocaleString('en-GB');
const plural = (value: number, one: string, many: string) =>
	`${n(value)} ${value === 1 ? one : many}`;

/** "3 jumps, 1 new private place, 2 rows skipped" from an import's counts. */
export function describeImport(counts: Record<string, number>): string {
	const parts = [plural(counts.jumps ?? 0, 'jump', 'jumps')];
	if (counts.new_places)
		parts.push(plural(counts.new_places, 'new private place', 'new private places'));
	if (counts.skipped) parts.push(plural(counts.skipped, 'row skipped', 'rows skipped'));
	return parts.join(', ');
}

/** "Removed 3 jumps and 1 private place" for an undone import. */
export function describeUndo(counts: Record<string, number>): string {
	const jumps = plural(counts.removed_jumps ?? 0, 'jump', 'jumps');
	const places = counts.removed_places
		? ` and ${plural(counts.removed_places, 'private place', 'private places')}`
		: '';
	return `Removed ${jumps}${places}`;
}

/**
 * When an import happened, to the minute in UTC: "12 November 2026, 13:05 UTC". Also
 * what makes each past import's undo controls distinct for assistive technology.
 */
export function importWhen(instant: string): string {
	const at = new Date(instant);
	if (Number.isNaN(at.getTime())) return instant;
	const date = at.toLocaleDateString('en-GB', {
		day: 'numeric',
		month: 'long',
		year: 'numeric',
		timeZone: 'UTC'
	});
	const time = at.toLocaleTimeString('en-GB', {
		hour: '2-digit',
		minute: '2-digit',
		hourCycle: 'h23',
		timeZone: 'UTC'
	});
	return `${date}, ${time} UTC`;
}
