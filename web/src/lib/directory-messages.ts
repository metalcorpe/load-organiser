/** User-facing text for directory outcomes. No upstream detail is ever shown. */
export const DIRECTORY_MESSAGES: Record<string, string> = {
	missing: 'Fill in the name and country.',
	not_found: 'That item no longer exists.',
	not_authenticated: 'Your session has ended. Sign in again.',
	email_unverified: 'Confirm your email address before saving private places.',
	venue_not_listed: 'That dropzone is not listed.',
	place_limit_reached: 'You have reached the limit of 200 private places. Remove one to add another.',
	place_in_use:
		'A logged jump is at this place, so it cannot be removed. Move those jumps to another place first.',
	name_required: 'Enter a name.',
	name_too_long: 'Use at most 120 characters for the name.',
	country_invalid: 'Choose a country from the list.',
	cursor_invalid: 'That page of results is no longer valid. Search again.',
	invalid_input: 'Check the details you entered.',
	uncertain:
		'The service did not answer in time. The change may or may not have been saved; reload to check before trying again.',
	unavailable: 'The service is unavailable right now. Try again later.'
};

export function directoryMessage(code: string | undefined): string | undefined {
	return code ? (DIRECTORY_MESSAGES[code] ?? DIRECTORY_MESSAGES.unavailable) : undefined;
}

export function directoryStatus(reason: string): number {
	switch (reason) {
		case 'not_authenticated':
			return 401;
		case 'email_unverified':
			return 403;
		case 'not_found':
			return 404;
		case 'place_limit_reached':
			return 409;
		case 'unavailable':
		case 'uncertain':
			return 503;
		default:
			return 400;
	}
}
