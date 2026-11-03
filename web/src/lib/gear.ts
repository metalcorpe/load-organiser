/** Labels and messages for private gear (#152). Client-safe. */

export const KIND_LABEL: Record<string, string> = {
	container: 'Container / harness',
	main: 'Main canopy',
	reserve: 'Reserve canopy',
	aad: 'AAD',
	other: 'Other'
};

export const RELATION_LABEL: Record<string, string> = {
	owned: 'Mine (owned)',
	borrowed: 'Borrowed',
	rented: 'Rented'
};

export const METHOD_LABEL: Record<string, string> = {
	purchase: 'Purchase',
	gift: 'Gift',
	inheritance: 'Inheritance',
	other: 'Other'
};

export const SERVICE_LABEL: Record<string, string> = {
	repack: 'Repack',
	inspection: 'Inspection',
	maintenance: 'Maintenance / repair',
	aad_service: 'AAD service',
	other: 'Other'
};

export const GEAR_MESSAGES: Record<string, string> = {
	missing: 'Fill in the type and a label.',
	confirm_delete: 'Tick the box to confirm deleting this item and its history.',
	not_found: 'That item no longer exists.',
	not_authenticated: 'Your session has ended. Sign in again.',
	email_unverified: 'Confirm your email address before saving gear.',
	edit_conflict:
		'This item changed since you opened it (perhaps in another tab). Nothing was saved. Reload to see the current details.',
	client_key_reused: 'This form was already sent with different details. Reload and try again.',
	component_limit_reached:
		'You have reached the limit of 50 components. Archive or delete one first.',
	rig_limit_reached: 'You have reached the limit of 20 rigs.',
	service_limit_reached: 'This item has reached the limit of 100 service entries.',
	label_required: 'Enter a label you will recognise.',
	label_too_long: 'Use at most 80 characters for the label.',
	serial_invalid: 'The serial contains characters that cannot be stored.',
	serial_too_long: 'Use at most 120 characters for the serial.',
	manufactured_invalid: 'Use YYYY, YYYY-MM or YYYY-MM-DD, not in the future.',
	acquired_invalid: 'Use YYYY, YYYY-MM or YYYY-MM-DD, not in the future.',
	acquisition_requires_owned: 'Acquisition details apply only to gear you own.',
	notes_too_long: 'Use at most 1,000 characters for notes.',
	manufacturer_too_long: 'Use at most 80 characters for the manufacturer.',
	model_too_long: 'Use at most 80 characters for the model.',
	performed_by_too_long: 'Use at most 120 characters for who did the work.',
	rig_date_in_future: 'The date cannot be in the future.',
	rig_date_before_current:
		'The date cannot be before its latest rig change (the current rig started, or the last one ended).',
	rig_unavailable: 'That rig is archived or no longer exists.',
	already_in_rig: 'It is already in that rig.',
	component_in_use:
		'A jump records it as used, so it cannot be deleted. Archive it instead; past jumps keep it.',
	not_in_rig: 'It is not in a rig.',
	component_archived: 'Restore the item before changing its rig.',
	service_incomplete: 'Choose the service type and the date it was done.',
	service_date_in_future: 'The service date cannot be in the future.',
	due_before_service: 'The due date cannot be before the service date.',
	invalid_input: 'Check the details you entered.',
	uncertain:
		'The service did not answer in time. The change may or may not have been saved; reload to check before trying again.',
	unavailable: 'The service is unavailable right now. Try again later.'
};

export function gearMessage(code: string | undefined): string | undefined {
	return code ? (GEAR_MESSAGES[code] ?? GEAR_MESSAGES.invalid_input) : undefined;
}
