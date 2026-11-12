/**
 * Changing many logbook jumps at once (/jumps in "Select" mode). Client-safe: the
 * wording of a change and its messages. The API is the authority on every rule.
 */
import { JUMP_TYPE_LABEL } from './jumps.ts';

/** At most this many jumps in one change (backend logbook/policy.py BATCH_MAX). */
export const BATCH_MAX = 200;

/** One change as chosen on the form; `undefined` keeps each jump's own value. */
export interface BatchChoice {
	jumpType?: string;
	/** The new place's name, when the place changes. */
	place?: string;
	/** The new aircraft; `null` clears it. */
	aircraft?: string | null;
	/** The labels of the new gear set; `[]` clears it. */
	gear?: string[];
}

/** "type → Freefly; aircraft → Cessna 208": what every chosen jump gets. */
export function changeText(choice: BatchChoice): string {
	const parts: string[] = [];
	if (choice.jumpType) parts.push(`type → ${JUMP_TYPE_LABEL[choice.jumpType] ?? choice.jumpType}`);
	if (choice.place !== undefined) parts.push(`place → ${choice.place}`);
	if (choice.aircraft !== undefined) parts.push(`aircraft → ${choice.aircraft ?? 'none'}`);
	if (choice.gear !== undefined) {
		parts.push(`gear used → ${choice.gear.length ? choice.gear.join(', ') : 'none'}`);
	}
	return parts.join('; ');
}

const jumps = (n: number) => `${n.toLocaleString('en-GB')} ${n === 1 ? 'jump' : 'jumps'}`;

/** "Change 23 jumps: type → Freefly; aircraft → Cessna 208". */
export function batchHeading(count: number, choice: BatchChoice): string {
	const what = changeText(choice);
	return what ? `Change ${jumps(count)}: ${what}` : `Change ${jumps(count)}`;
}

/** The outcome of a change, in one sentence. */
export function appliedText(changed: number, skipped: number, unchanged: number): string {
	const parts = [`Changed ${jumps(changed)}.`];
	if (skipped > 0) {
		parts.push(
			`${jumps(skipped)} ${skipped === 1 ? 'was' : 'were'} left as ${skipped === 1 ? 'it was' : 'they were'}: edited or deleted since you checked.`
		);
	}
	if (unchanged > 0) {
		parts.push(`${jumps(unchanged)} already had these values.`);
	}
	return parts.join(' ');
}

/** The outcome of an undo, in one sentence. */
export function undoneText(restored: number, skipped: number): string {
	const parts = [`Put back ${jumps(restored)}.`];
	if (skipped > 0) {
		parts.push(
			`${jumps(skipped)} ${skipped === 1 ? 'was' : 'were'} left as ${skipped === 1 ? 'it is' : 'they are'}: edited since the change, or an earlier place or gear is no longer available.`
		);
	}
	return parts.join(' ');
}

export const BATCH_MESSAGES: Record<string, string> = {
	jumps_required: 'Tick at least one jump to change.',
	too_many_jumps: `Choose at most ${BATCH_MAX} jumps at a time.`,
	nothing_to_change: 'Choose what to change: the type, the place, the aircraft or the gear used.',
	location_required: 'Choose one place.',
	venue_not_listed: 'That dropzone is no longer listed. Choose another place.',
	place_unknown: 'That private place no longer exists. Choose another place.',
	component_unknown: 'One of the chosen components no longer exists.',
	too_many_components: 'Choose at most ten components.',
	aircraft_too_long: 'Use at most 60 characters for the aircraft.',
	undo_unavailable:
		'That change can no longer be undone: a later change replaced it, or more than 24 hours have passed.',
	already_undone: 'That change was already undone.',
	email_unverified: 'Confirm your email address before changing jumps.',
	not_authenticated: 'Your session has ended. Sign in again.',
	invalid_input: 'Check what you chose.',
	uncertain:
		'Not confirmed: the service did not answer in time. Reload the logbook to see whether the jumps changed before trying again.',
	unavailable: 'The service is unavailable right now. Nothing was changed. Try again later.'
};

export function batchMessage(code: string | undefined): string | undefined {
	return code ? (BATCH_MESSAGES[code] ?? BATCH_MESSAGES.invalid_input) : undefined;
}
