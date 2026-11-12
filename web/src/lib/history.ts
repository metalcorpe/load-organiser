/** Messages and formatting for personal history and the prior-history baseline (#154). */

export const HISTORY_MESSAGES: Record<string, string> = {
	missing: 'Enter the number of jumps and the date.',
	prior_jumps_invalid: 'Enter a whole number of jumps from 0 to 100,000.',
	baseline_date_in_future: 'The date cannot be in the future.',
	baseline_date_invalid: 'Check the date.',
	edit_conflict:
		'Your prior jump count changed since you opened this page (perhaps in another tab). Nothing was saved. Reload to see the current values.',
	confirm_remove: 'Tick the box to confirm removing your prior jump count.',
	not_authenticated: 'Your session has ended. Sign in again.',
	email_unverified: 'Confirm your email address before changing your prior jump count.',
	invalid_input: 'Check the details you entered.',
	uncertain:
		'Not confirmed: the service did not answer in time. It may or may not have been saved. Reload the page to check before sending again.',
	unavailable: 'The service is unavailable right now. Nothing was saved. Try again later.'
};

export function historyMessage(code: string | undefined): string | undefined {
	return code ? (HISTORY_MESSAGES[code] ?? HISTORY_MESSAGES.invalid_input) : undefined;
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/** "2026-10" → "Oct 2026". Built by hand: no time zone shift, same text on every runtime. */
export function formatMonth(month: string): string {
	const [year, m] = month.split('-');
	return `${MONTHS[Number(m) - 1] ?? m} ${year}`;
}

export function count(n: number, one = 'jump', many = 'jumps'): string {
	return `${n.toLocaleString('en-GB')} ${n === 1 ? one : many}`;
}

// -- milestones ---------------------------------------------------------------------

/** 1st, 2nd, 3rd, 4th, 11th, 21st, 1,000th. */
export function ordinal(n: number): string {
	const tens = n % 100;
	const suffix =
		tens >= 11 && tens <= 13 ? 'th' : ({ 1: 'st', 2: 'nd', 3: 'rd' }[n % 10] ?? 'th');
	return `${n.toLocaleString('en-GB')}${suffix}`;
}

/** Jump types as they read inside a sentence ("First wingsuit jump"). */
const TYPE_IN_SENTENCE: Record<string, string> = {
	belly: 'belly / formation',
	freefly: 'freefly',
	angle: 'angle / tracking',
	wingsuit: 'wingsuit',
	canopy: 'canopy piloting',
	crw: 'canopy formation (CRW)',
	accuracy: 'accuracy',
	hop_and_pop: 'hop and pop',
	tandem: 'tandem',
	training: 'training / coached'
};

/** The fields of MilestoneOut the wording needs. */
export interface MilestoneIn {
	kind: 'jump_count' | 'freefall' | 'jump_type' | 'place';
	number: number | null;
	hours: number | null;
	jump_type: string | null;
	location: { kind: 'venue' | 'place'; name: string | null } | null;
}

export function milestoneText(m: MilestoneIn): string {
	switch (m.kind) {
		case 'jump_count':
			return `${ordinal(m.number ?? 0)} jump`;
		case 'freefall':
			return `${count(m.hours ?? 0, 'hour', 'hours')} of recorded freefall`;
		case 'jump_type': {
			const type = TYPE_IN_SENTENCE[m.jump_type ?? ''];
			return type ? `First ${type} jump` : 'First jump of the type "Other"';
		}
		case 'place': {
			const loc = m.location;
			const name = loc?.name ?? (loc?.kind === 'venue' ? 'a dropzone no longer listed' : 'a private place');
			return `First jump at ${name}`;
		}
	}
}
