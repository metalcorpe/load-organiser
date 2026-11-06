/** Labels and messages for profiles, follows, blocks and reports (#156). Client-safe. */
import { JUMP_TYPE_LABEL } from './jumps.ts';

export const DISCIPLINES = [
	'belly',
	'freefly',
	'angle',
	'wingsuit',
	'canopy',
	'crw',
	'accuracy',
	'hop_and_pop',
	'tandem',
	'training'
] as const;

export const disciplineLabel = (value: string) => JUMP_TYPE_LABEL[value] ?? value;

export const REPORT_REASONS: Record<string, string> = {
	impersonation: 'Pretends to be someone else',
	harassment: 'Harassment or threats',
	spam: 'Spam or advertising',
	inappropriate: 'Inappropriate content',
	other: 'Something else'
};

export const DECISIONS: Record<string, string> = {
	no_action: 'No action',
	hide_profile: 'Hide the profile',
	restrict_publishing: 'Restrict publishing'
};

export const SOCIAL_MESSAGES: Record<string, string> = {
	handle_required: 'Choose a handle.',
	handle_invalid:
		'A handle is 3 to 30 characters: lowercase letters, digits or underscores, starting with a letter.',
	handle_reserved: 'That handle is reserved. Choose another.',
	handle_taken: 'That handle is already taken. Choose another.',
	handle_fixed: 'The handle cannot be changed.',
	display_name_required: 'Enter a display name.',
	display_name_too_long: 'Use at most 60 characters for the display name.',
	bio_too_long: 'Use at most 280 characters for the bio.',
	discipline_invalid: 'Choose disciplines from the list.',
	too_many_disciplines: 'Choose at most five disciplines.',
	venue_not_listed: 'That dropzone is no longer listed. Choose another or none.',
	edit_conflict:
		'Your profile changed since you opened this page (perhaps in another tab). Nothing was saved. Reload to see the current details.',
	profile_required: 'Create your public profile first, so the person can see who is asking.',
	profile_hidden: 'Your profile is hidden by a reviewer, so you cannot ask to follow people.',
	follow_self: 'You cannot follow yourself.',
	follow_limit_reached: 'You follow or have asked to follow 500 people, the current limit.',
	block_limit_reached: 'You have blocked 500 people, the current limit.',
	block_self: 'You cannot block yourself.',
	report_self: 'You cannot report your own profile.',
	reason_invalid: 'Choose a reason.',
	reason_required: 'Give a reason; it is recorded and shown to the profile owner.',
	note_too_long: 'Use at most 1,000 characters.',
	reason_too_long: 'Use at most 280 characters for the reason.',
	query_too_short: 'Enter at least two characters.',
	confirm_block: 'Tick the box to confirm blocking.',
	not_found: 'This profile is not available.',
	not_authenticated: 'Your session has ended. Sign in again.',
	email_unverified: 'Confirm your email address first.',
	too_many_attempts: 'Too many attempts. Wait a while and try again.',
	invalid_input: 'Check the details you entered.',
	uncertain:
		'Not confirmed: the service did not answer in time. Reload to see whether it was applied.',
	unavailable: 'The service is unavailable right now. Nothing was changed. Try again later.'
};

export function socialMessage(code: string | undefined): string | undefined {
	return code ? (SOCIAL_MESSAGES[code] ?? SOCIAL_MESSAGES.invalid_input) : undefined;
}
