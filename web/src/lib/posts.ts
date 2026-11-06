/** Labels and messages for published jump summaries (#157). Client-safe. */
import { SOCIAL_MESSAGES } from './social.ts';

export const SHARE_PARTS = [
	{ value: 'type', label: 'Jump type' },
	{ value: 'venue', label: 'Dropzone' },
	{ value: 'altitude', label: 'Exit altitude' },
	{ value: 'freefall', label: 'Freefall time' }
] as const;

export const AUDIENCE_LABEL: Record<string, string> = {
	followers: 'Approved followers',
	public: 'Public'
};

const POST_MESSAGES: Record<string, string> = {
	...SOCIAL_MESSAGES,
	edit_conflict:
		'The jump or this post changed since you opened the page (perhaps in another tab). Nothing was published or changed. Review it again.',
	already_published: 'This jump is already published. Change or unpublish the existing post.',
	public_needs_discoverable:
		'A public post needs a discoverable profile. Turn on "Let people find my profile" or share with approved followers.',
	publishing_restricted: 'A reviewer has restricted publishing on your profile.',
	profile_hidden: 'Your profile is hidden by a reviewer, so you cannot publish.',
	profile_required: 'Create your public profile first; posts appear under its handle.',
	type_not_recorded: 'This jump has no type recorded, so there is none to share.',
	altitude_not_recorded: 'This jump has no exit altitude recorded.',
	freefall_not_recorded: 'This jump has no freefall time recorded.',
	venue_not_listed:
		'Only a listed dropzone can be shared. A private place, or a dropzone no longer listed, is never shared.',
	caption_too_long: 'Use at most 280 characters for the caption.',
	link_invalid: 'Enter a full http(s) link, or leave it empty.',
	audience_invalid: 'Choose who can see it.',
	share_invalid: 'Choose from the listed parts.',
	confirm_unpublish: 'Tick the box to confirm unpublishing.',
	not_found: 'This post is not available.'
};

export function postMessage(code: string | undefined): string | undefined {
	return code ? (POST_MESSAGES[code] ?? POST_MESSAGES.invalid_input) : undefined;
}

/** History lines for post events on the owner's jump page. */
export function postEventText(kind: string, detail: Record<string, unknown>): string | null {
	switch (kind) {
		case 'post_published':
			return `Published to ${(AUDIENCE_LABEL[String(detail.audience)] ?? 'an audience').toLowerCase()}`;
		case 'post_audience':
			return `Post audience changed to ${(AUDIENCE_LABEL[String(detail.to)] ?? '').toLowerCase()}`;
		case 'post_unpublished':
			return 'Post unpublished';
		case 'post_withdrawn':
			return detail.reason === 'profile_not_discoverable'
				? 'Public post withdrawn: your profile stopped being discoverable'
				: 'Post withdrawn: you changed a value it shared';
		case 'post_removed':
			return `Post removed by a reviewer${detail.reason ? `: ${String(detail.reason)}` : ''}`;
		default:
			return null;
	}
}
