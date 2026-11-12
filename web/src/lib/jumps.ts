/** Labels and messages for the private jump logbook (#153). Client-safe. */
import type { JumpNumberingOut, JumpOut } from './contracts/index.ts';

export const JUMP_TYPE_LABEL: Record<string, string> = {
	unspecified: 'Not specified',
	belly: 'Belly / formation',
	freefly: 'Freefly',
	angle: 'Angle / tracking',
	wingsuit: 'Wingsuit',
	canopy: 'Canopy piloting',
	crw: 'Canopy formation (CRW)',
	accuracy: 'Accuracy',
	hop_and_pop: 'Hop and pop',
	tandem: 'Tandem',
	training: 'Training / coached',
	other: 'Other'
};

export const DATUM_LABEL: Record<string, string> = {
	unspecified: 'Not stated',
	agl: 'Above ground (AGL)',
	msl: 'Above sea level (MSL)'
};

export const JUMP_MESSAGES: Record<string, string> = {
	missing: 'Enter the date and choose the jump type.',
	confirm_delete: 'Tick the box to confirm deleting this jump.',
	not_found: 'That jump no longer exists.',
	not_authenticated: 'Your session has ended. Sign in again.',
	email_unverified: 'Confirm your email address before saving jumps.',
	edit_conflict:
		'This jump changed since you opened it (perhaps in another tab). Nothing was saved. Reload to see the current details.',
	client_key_reused: 'This form was already sent with different details. Reload and try again.',
	jump_deleted: 'This jump was saved and later deleted. It was not saved again.',
	jump_limit_reached: 'You have reached the limit of 2,000 jumps.',
	jump_date_required: 'Enter the date of the jump.',
	jump_date_in_future: 'The date cannot be in the future.',
	jump_date_invalid: 'Check the date.',
	location_required: 'Choose where you jumped.',
	venue_not_listed: 'That dropzone is no longer listed. Choose another place.',
	place_unknown: 'That private place no longer exists. Choose another place.',
	jump_type_invalid: 'Choose the jump type.',
	jump_number_invalid: 'The jump number must be a whole number of 1 or more.',
	exit_time_invalid: 'Check the exit time.',
	exit_time_incomplete: 'Enter the exit time together with its time zone.',
	time_zone_required: 'An exit time needs its time zone, e.g. Europe/Madrid.',
	time_zone_invalid: 'Use a time zone name such as Europe/Madrid.',
	altitude_unit_required: 'Choose feet or metres for the altitudes.',
	altitude_invalid: 'Check the altitudes.',
	altitudes_incomplete: 'Check the altitudes.',
	deployment_above_exit: 'The deployment altitude cannot be above the exit altitude.',
	freefall_invalid: 'Freefall time must be between 0 and 600 seconds.',
	notes_too_long: 'Use at most 2,000 characters for notes.',
	other_gear_too_long: 'Use at most 200 characters for other equipment.',
	too_many_links: 'Add at most five links.',
	link_invalid: 'Links must be full http(s) addresses.',
	too_many_components: 'Choose at most ten components.',
	component_unknown: 'One of the chosen components no longer exists.',
	component_limit_reached:
		'You have reached the limit of 50 components. Nothing was saved; untick "Add a new component" or archive one first.',
	label_required: 'Give the new component a label.',
	date_range_invalid: 'The "from" date must be on or before the "to" date.',
	number_range_invalid: 'The lowest jump number must not be above the highest.',
	location_filter_invalid: 'Choose one place to filter by.',
	invalid_input: 'Check the details you entered.',
	uncertain:
		'Save not confirmed: the service did not answer in time. It may or may not have been saved. Send the form again: it will not create a second entry.',
	unavailable: 'The service is unavailable right now. Nothing was saved. Try again later.'
};

export function jumpMessage(code: string | undefined): string | undefined {
	return code ? (JUMP_MESSAGES[code] ?? JUMP_MESSAGES.invalid_input) : undefined;
}

export function altitudeText(
	exit: number | null,
	deployment: number | null,
	unit: string | null,
	datum: string
): string | null {
	if (!unit || (exit === null && deployment === null)) return null;
	const parts = [];
	if (exit !== null) parts.push(`exit ${exit.toLocaleString('en-GB')} ${unit}`);
	if (deployment !== null) parts.push(`deployment ${deployment.toLocaleString('en-GB')} ${unit}`);
	const ref = datum === 'unspecified' ? '' : ` ${datum.toUpperCase()}`;
	return parts.join(', ') + ref;
}

/**
 * Form values for the next jump after `jump`: same place, type, gear and altitudes,
 * the next jump number, and the same day when `sameDay` (catching up on one day's
 * loads); otherwise the date starts empty and the form fills in the jumper's own today.
 * Notes, links, other gear, exit time and freefall time describe one jump only and
 * start empty. Archived gear is not preselected.
 */
export function nextJumpValues(
	jump: JumpOut,
	{ sameDay }: { sameDay: boolean }
): { values: Record<string, string>; selected: string[] } {
	return {
		values: {
			jumped_on: sameDay ? jump.jumped_on : '',
			jump_type: jump.jump_type,
			jump_number: jump.jump_number === null ? '' : String(jump.jump_number + 1),
			time_zone: jump.time_zone ?? '',
			exit_altitude: jump.exit_altitude?.toString() ?? '',
			deployment_altitude: jump.deployment_altitude?.toString() ?? '',
			altitude_unit: jump.altitude_unit ?? '',
			altitude_datum: jump.altitude_datum
		},
		selected: jump.components.filter((c) => !c.archived).map((c) => c.id)
	};
}

const MAX_JUMP_NUMBER = 1_000_000;

/** The number to propose for a new jump: one after the highest, or none if never numbered. */
export function proposedNumber(highest: number | null | undefined): number | null {
	return typeof highest === 'number' && highest >= 1 && highest < MAX_JUMP_NUMBER ? highest + 1 : null;
}

/** The hint shown beside a proposed number. */
export function numberHint(highest: number | null | undefined): string | null {
	return proposedNumber(highest) === null ? null : `Your last numbered jump is #${highest}.`;
}

const TIMES = ['', 'once', 'twice', 'three times'];

export type NumberingNote =
	| { kind: 'gap'; text: string; before: { id: string; number: number }; after: { id: string; number: number } }
	| { kind: 'repeat'; text: string; jumps: { id: string; jumped_on: string }[] };

/** Brief notes on gaps and repeats in the jumper's own numbering; empty when all is in order. */
export function numberingNotes(numbering: JumpNumberingOut): { notes: NumberingNote[]; more: string | null } {
	const n = (value: number) => value.toLocaleString('en-GB');
	const notes: NumberingNote[] = [
		...numbering.gaps.map(
			(gap): NumberingNote => ({
				kind: 'gap',
				text:
					gap.first === gap.last
						? `Number ${n(gap.first)} is missing`
						: `Numbers ${n(gap.first)}–${n(gap.last)} are missing`,
				before: { id: gap.before.id, number: gap.before.jump_number },
				after: { id: gap.after.id, number: gap.after.jump_number }
			})
		),
		...numbering.repeats.map(
			(repeat): NumberingNote => ({
				kind: 'repeat',
				text: `#${n(repeat.jump_number)} is used ${TIMES[repeat.uses] ?? `${repeat.uses} times`}`,
				jumps: repeat.jumps.map((j) => ({ id: j.id, jumped_on: j.jumped_on }))
			})
		)
	];
	const extraGaps = numbering.gap_count - numbering.gaps.length;
	const extraRepeats = numbering.repeat_count - numbering.repeats.length;
	const parts = [
		extraGaps > 0 ? `${extraGaps} more ${extraGaps === 1 ? 'gap' : 'gaps'}` : '',
		extraRepeats > 0 ? `${extraRepeats} more repeated ${extraRepeats === 1 ? 'number' : 'numbers'}` : ''
	].filter(Boolean);
	return { notes, more: parts.length ? `And ${parts.join(' and ')}.` : null };
}
