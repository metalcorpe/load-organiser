/** Jump currency guidance (USPA SIM 5-2) as shown to the jumper. Client-safe, no I/O. */
import type { CurrencyOut } from './contracts/index.ts';
import { formatDay } from './listings.ts';

export const LICENCES = ['none', 'student', 'a', 'b', 'c', 'd'] as const;
export type Licence = (typeof LICENCES)[number];

export const LICENCE_LABEL: Record<Licence, string> = {
	none: 'None',
	student: 'Student',
	a: 'A licence',
	b: 'B licence',
	c: 'C licence',
	d: 'D licence'
};

export type CurrencyIn = Pick<CurrencyOut, 'licence' | 'threshold_days' | 'current_until'>;

export type CurrencyState =
	| { kind: 'no_licence' }
	| { kind: 'no_jumps' }
	| { kind: 'current'; until: string; text: string }
	| { kind: 'lapsed'; since: string; text: string };

export const isLicence = (value: unknown): value is Licence =>
	(LICENCES as readonly unknown[]).includes(value);

/** YYYY-MM-DD plus `days` calendar days, without any time zone shift. */
export function addDays(day: string, days: number): string {
	const d = new Date(`${day}T00:00:00Z`);
	d.setUTCDate(d.getUTCDate() + days);
	return d.toISOString().slice(0, 10);
}

/** The jumper's own calendar day, from the device clock. */
export function localToday(now = new Date()): string {
	const pad = (n: number) => String(n).padStart(2, '0');
	return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

function guidance(licence: Licence, days: number): string {
	const who =
		licence === 'student' ? 'a student' : `${licence === 'a' ? 'an' : 'a'} ${LICENCE_LABEL[licence]}`;
	return `USPA guidance for ${who}: ${days} days`;
}

/** Current on `today` (the jumper's calendar day) up to and including `current_until`. */
export function currencyState(c: CurrencyIn, today: string): CurrencyState {
	if (!isLicence(c.licence) || c.licence === 'none' || c.threshold_days === null) {
		return { kind: 'no_licence' };
	}
	if (!c.current_until) return { kind: 'no_jumps' };
	if (today <= c.current_until) {
		return {
			kind: 'current',
			until: c.current_until,
			text: `Current until ${formatDay(c.current_until)} (${guidance(c.licence, c.threshold_days)}).`
		};
	}
	const since = addDays(c.current_until, 1);
	return {
		kind: 'lapsed',
		since,
		text: `Not current since ${formatDay(since)}: USPA recommends a supervised jump before your next solo jump. Your dropzone may require more.`
	};
}

export const LICENCE_MESSAGES: Record<string, string> = {
	missing: 'Choose a licence, or None.',
	email_unverified: 'Confirm your email address before saving your licence.',
	not_authenticated: 'Your session has ended. Sign in again.',
	invalid_input: 'Choose a licence, or None.',
	uncertain:
		'Not confirmed: the service did not answer in time. Reload the page to check before saving again.',
	unavailable: 'The service is unavailable right now. Nothing was saved. Try again later.'
};

export function licenceMessage(code: string | undefined): string | undefined {
	return code ? (LICENCE_MESSAGES[code] ?? LICENCE_MESSAGES.unavailable) : undefined;
}
