/** Text for maintenance and submission outcomes (#151). Client-safe. */

/** Reviewer-facing text for rule codes; unknown codes are shown as the code itself. */
export const REVIEW_MESSAGES: Record<string, string> = {
	edit_conflict:
		'Someone changed this since you opened it. Nothing was saved. Copy what you need, then reload to see the current version.',
	not_found: 'That record no longer exists.',
	forbidden: 'Reviewer access is required.',
	not_authenticated: 'Your session has ended. Sign in again.',
	email_unverified: 'Confirm your email address first.',
	uncertain:
		'The service did not answer in time. The change may or may not have been saved; reload to check.',
	unavailable: 'The service is unavailable right now. Try again later.',
	invalid_input: 'Check the values entered.',
	missing: 'Fill in the required fields.',
	provider_in_use:
		'This organizer still has live public listings. Move, end or withdraw them first.',
	provider_not_published: 'The organizer must be published before its listings can be.',
	source_required: 'A source link and last-checked date are required to publish.',
	registration_url_required: 'A registration or contact link is required to publish.',
	location_required: 'Choose a public dropzone or describe the location to publish.',
	schedule_required: 'Dates are required unless the listing is postponed.',
	status_change_invalid: 'That status change is not allowed from the current status.',
	submission_resolved: 'This submission was already resolved.',
	submissions_paused: 'Submissions are paused right now. Try again later.',
	submission_limit_reached:
		'You have reached the submission limit for now (10 a day, 20 waiting). Try again later.',
	submission_key_reused: 'This form was already sent with different content. Reload and try again.',
	target_unavailable: 'That listing is no longer public.',
	target_required: 'Corrections and reports need the listing they are about.',
	message_required: 'Describe the suggestion or problem.',
	message_too_long: 'Use at most 1,000 characters.',
	source_url_invalid: 'Use a full http(s) link, or leave it empty.'
};

export function reviewMessage(code: string | undefined): string | undefined {
	if (!code) return undefined;
	return REVIEW_MESSAGES[code] ?? `Refused by the service: ${code.replaceAll('_', ' ')}.`;
}
