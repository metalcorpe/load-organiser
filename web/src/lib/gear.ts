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
	repack_interval_invalid:
		'Enter a repack interval in whole days from 1 to 730, or leave it empty for 180 days.',
	end_of_life_invalid: 'Check the end-of-life date.',
	invalid_input: 'Check the details you entered.',
	uncertain:
		'The service did not answer in time. The change may or may not have been saved; reload to check before trying again.',
	unavailable: 'The service is unavailable right now. Try again later.'
};

export function gearMessage(code: string | undefined): string | undefined {
	return code ? (GEAR_MESSAGES[code] ?? GEAR_MESSAGES.invalid_input) : undefined;
}

// -- due dates ----------------------------------------------------------------------

/** The interval used when the owner sets none (backend gear/policy.py). */
export const REPACK_INTERVAL_DEFAULT = 180;
export const REPACK_INTERVAL_LABEL =
	"180 days (USPA / FAA 14 CFR 105.43; your country's rule may differ)";
/** "Due soon": due within this many days, or overdue. */
export const DUE_SOON_DAYS = 30;

/** The fields of a due date the wording needs (GearDueOut). */
export interface DueIn {
	component: { id: string; kind: string; label: string };
	kind: 'reserve_repack' | 'service' | 'end_of_life';
	service_kind: string | null;
	due_on: string;
	basis: 'entered' | 'interval';
	interval_days: number | null;
	interval_source: string | null;
}

const SERVICE_DUE: Record<string, string> = {
	repack: 'Repack',
	inspection: 'Inspection',
	maintenance: 'Maintenance',
	aad_service: 'AAD maintenance',
	other: 'Service'
};

/** What is due, as a sentence start: "Reserve repack", "AAD end of life". */
export function dueWhat(item: Pick<DueIn, 'component' | 'kind' | 'service_kind'>): string {
	if (item.kind === 'reserve_repack') return 'Reserve repack';
	if (item.kind === 'end_of_life')
		return item.component.kind === 'aad' ? 'AAD end of life' : 'End of service life';
	return SERVICE_DUE[item.service_kind ?? 'other'] ?? 'Service';
}

const DAY_MS = 86_400_000;
const utc = (day: string) => Date.parse(`${day}T00:00:00Z`);

/** Whole calendar days from `today` to `day` (negative once it has passed). */
export function daysUntil(day: string, today: string): number {
	return Math.round((utc(day) - utc(today)) / DAY_MS);
}

const MONTH_DAY = new Intl.DateTimeFormat('en-GB', {
	day: 'numeric',
	month: 'long',
	timeZone: 'UTC'
});
const FULL_DAY = new Intl.DateTimeFormat('en-GB', { dateStyle: 'long', timeZone: 'UTC' });

/** "3 November" in `today`'s year, "3 November 2027" otherwise. */
export function shortDay(day: string, today: string): string {
	const d = new Date(utc(day));
	return day.slice(0, 4) === today.slice(0, 4) ? MONTH_DAY.format(d) : FULL_DAY.format(d);
}

export type DueState = 'overdue' | 'soon' | 'later';

/** Due on `dueOn` is still in time that day; overdue from the day after. */
export function dueState(dueOn: string, today: string): DueState {
	const days = daysUntil(dueOn, today);
	if (days < 0) return 'overdue';
	return days <= DUE_SOON_DAYS ? 'soon' : 'later';
}

/** "Reserve repack due in 5 days (17 November)", "AAD maintenance overdue since 3 November". */
export function dueText(item: DueIn, today: string): string {
	const what = dueWhat(item);
	const days = daysUntil(item.due_on, today);
	if (days < 0) {
		const since = new Date(utc(item.due_on) + DAY_MS).toISOString().slice(0, 10);
		return `${what} overdue since ${shortDay(since, today)}`;
	}
	if (days === 0) return `${what} due today`;
	if (days === 1) return `${what} due tomorrow (${shortDay(item.due_on, today)})`;
	return `${what} due in ${days} days (${shortDay(item.due_on, today)})`;
}

/** Where a date comes from, in plain words. */
export function dueBasis(item: DueIn): string {
	if (item.kind === 'end_of_life') return 'The end-of-life date you entered.';
	if (item.basis === 'interval') {
		return item.interval_source
			? `${REPACK_INTERVAL_LABEL} after your last recorded repack.`
			: `Your interval of ${item.interval_days} days after your last recorded repack.`;
	}
	return 'The due date you entered with the latest service entry of this kind.';
}

/** Overdue or due within 30 days of `today`, in the given (soonest first) order. */
export function dueSoon<T extends DueIn>(items: T[], today: string): T[] {
	return items.filter((item) => dueState(item.due_on, today) !== 'later');
}

/** The optional repack interval field: empty, or whole days from 1 to 730. */
export function parseInterval(raw: string): number | null | 'invalid' {
	const text = raw.trim();
	if (!text) return null;
	if (!/^\d{1,3}$/.test(text)) return 'invalid';
	const days = Number(text);
	return days >= 1 && days <= 730 ? days : 'invalid';
}
