/** Labels and messages for personal export and restore (#155). Client-safe. */

export const RECORD_LABEL: Record<string, [string, string]> = {
	jumps: ['jump', 'jumps'],
	baseline: ['prior jump count', 'prior jump counts'],
	places: ['private place', 'private places'],
	components: ['gear item', 'gear items'],
	rigs: ['rig', 'rigs'],
	service_entries: ['service entry', 'service entries'],
	saved_listings: ['saved listing', 'saved listings'],
	plans: ['visit plan', 'visit plans']
};

/** "3 jumps, 1 rig" for the kinds present, in a fixed order. */
export function describeCounts(counts: Record<string, number>): string {
	const parts = Object.entries(RECORD_LABEL)
		.filter(([key]) => (counts[key] ?? 0) > 0)
		.map(
			([key, [one, many]]) =>
				`${counts[key].toLocaleString('en-GB')} ${counts[key] === 1 ? one : many}`
		);
	return parts.length ? parts.join(', ') : 'no records';
}

export const RECORDS_MESSAGES: Record<string, string> = {
	file_required: 'Choose an export file (.json).',
	password_required: 'Enter your password to restore.',
	archive_too_large: 'That file is larger than the 8 MiB restore limit. Nothing was changed.',
	archive_malformed:
		'That file is not a Load Organiser export (it is not a JSON export of this format). Nothing was changed.',
	archive_version_unsupported:
		'That export uses a format version this service cannot read. Nothing was changed.',
	archive_invalid:
		'That file does not pass the checks for a personal export, so nothing was changed. It may have been edited or damaged.',
	records_not_empty:
		'Restore only works into empty records, and yours already hold entries. Nothing was changed. Your existing records stay as they are and can be exported.',
	password_confirmation_failed: 'That password is not correct. Nothing was changed.',
	too_many_attempts: 'Too many attempts. Wait a while and try again.',
	email_unverified: 'Confirm your email address before restoring records.',
	not_authenticated: 'Your session has ended. Sign in again.',
	uncertain:
		'Not confirmed: the service did not answer in time. Check the file again: if it was restored, it shows as already restored and nothing is applied twice.',
	unavailable: 'The service is unavailable right now. Nothing was changed. Try again later.',
	invalid_input: 'Something in the request was not accepted. Nothing was changed.'
};

export function recordsMessage(code: string | undefined): string | undefined {
	return code ? (RECORDS_MESSAGES[code] ?? RECORDS_MESSAGES.invalid_input) : undefined;
}
