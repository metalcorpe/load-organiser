/**
 * Wing loading: exit weight in pounds over the main canopy's size in square feet,
 * from the jumper's own entries. Client-safe, no I/O. The API computes the stored
 * values; this mirrors it for the jump form's note and formats what it returns.
 * Nothing here is advice: no limit or recommendation is applied.
 */

export type WeightUnit = 'kg' | 'lb';
export type Missing = 'exit_weight' | 'main_canopy' | 'canopy_size' | 'several_mains';

/** Exact, by definition. */
export const GRAMS_PER_POUND = 453.59237;
export const WEIGHT_MIN_GRAMS = 30_000;
export const WEIGHT_MAX_GRAMS = 250_000;
/** The form notes a loading this much above the highest recorded before. */
export const NOTABLE_STEP = 0.1;

export const UNIT_LABEL: Record<WeightUnit, string> = { kg: 'kg', lb: 'lb' };
export const UNIT_NAME: Record<WeightUnit, string> = { kg: 'Kilograms', lb: 'Pounds' };

const perUnit = (unit: WeightUnit) => (unit === 'kg' ? 1000 : GRAMS_PER_POUND);

/** An entered weight in whole grams. */
export function toGrams(value: number, unit: WeightUnit): number {
	return Math.round(value * perUnit(unit));
}

/** Grams in the jumper's unit, to one decimal. */
export function inUnit(grams: number, unit: WeightUnit): number {
	return Math.round((grams / perUnit(unit)) * 10) / 10;
}

/** "81.6 kg", "180 lb": one decimal only when it is not zero. */
export function formatWeight(grams: number, unit: WeightUnit): string {
	const value = inUnit(grams, unit);
	return `${value.toLocaleString('en-GB', { maximumFractionDigits: 1 })} ${UNIT_LABEL[unit]}`;
}

/**
 * A weight field: empty, or a number with at most one decimal (a comma works too)
 * within 30 to 250 kg. Returns grams.
 */
export function parseWeight(raw: string, unit: WeightUnit): number | null | 'invalid' {
	const text = raw.trim().replace(',', '.');
	if (!text) return null;
	if (!/^\d{1,4}(\.\d)?$/.test(text)) return 'invalid';
	const grams = toGrams(Number(text), unit);
	return grams >= WEIGHT_MIN_GRAMS && grams <= WEIGHT_MAX_GRAMS ? grams : 'invalid';
}

/** The loading to two decimals, or null when either value is missing. */
export function wingLoading(grams: number | null, sqft: number | null): number | null {
	if (grams === null || sqft === null || sqft <= 0) return null;
	// Half up on the cents, with a tolerance for binary fractions (1.005 → 1.01).
	return Math.round((grams / GRAMS_PER_POUND / sqft) * 100 + 1e-9) / 100;
}

/** "1.12" */
export function formatLoading(value: number): string {
	return value.toFixed(2);
}

/** More than NOTABLE_STEP above the highest loading recorded before. */
export function isNotable(candidate: number | null, highest: number | null): boolean {
	if (candidate === null || highest === null) return false;
	return Math.round(candidate * 100) - Math.round(highest * 100) > NOTABLE_STEP * 100;
}

export type LoadingContext = { usualGrams: number | null; unit: WeightUnit; highest: number | null };

/**
 * The jump form's context, or an empty one in `unit` when it could not be read, so
 * the prefilled number, its label and the unit sent with it always agree.
 */
export function formLoading(loading: LoadingContext | null, unit: WeightUnit): LoadingContext {
	return loading ?? { usualGrams: null, unit, highest: null };
}

/** The calm note on the jump form; no advice. */
export function highestNote(candidate: number, highest: number): string {
	return `This is your highest wing loading so far (${formatLoading(candidate)}; previous highest ${formatLoading(highest)}).`;
}

const MISSING_TEXT: Record<Missing, string> = {
	exit_weight: 'no exit weight is set',
	main_canopy: 'no main canopy is recorded on the jump',
	canopy_size: 'the main canopy has no size',
	several_mains: 'more than one main canopy is recorded on the jump'
};

const MISSING_ORDER: Missing[] = ['exit_weight', 'main_canopy', 'canopy_size', 'several_mains'];

/** "no exit weight is set and the main canopy has no size", each reason once. */
export function missingText(missing: readonly string[]): string {
	const found = MISSING_ORDER.filter((m) => missing.includes(m));
	if (found.length === 0) return '';
	const parts = found.map((m) => MISSING_TEXT[m]);
	return parts.length === 1 ? parts[0] : `${parts.slice(0, -1).join(', ')} and ${parts.at(-1)}`;
}

/** Where to fix each reason, once: profile for the weight, gear and the jump for the rest. */
export function missingHelp(missing: readonly string[]): { profile: boolean; gear: boolean } {
	return {
		profile: missing.includes('exit_weight'),
		gear: missing.some((m) => m === 'main_canopy' || m === 'canopy_size' || m === 'several_mains')
	};
}

type WithLoading = { wing_loading: { value: number | null; missing: string[] } };

/**
 * One note for a list of jumps: how many show no wing loading and why, each reason
 * once. Null when every jump has one, and for a jumper who records neither an exit
 * weight nor a main canopy (they are not reminded on every page).
 */
export function listNote(
	items: readonly WithLoading[]
): { count: number; text: string; missing: string[] } | null {
	const unknown = items.filter((i) => i.wing_loading.value === null);
	if (unknown.length === 0) return null;
	const missing = MISSING_ORDER.filter((m) => unknown.some((i) => i.wing_loading.missing.includes(m)));
	const unused =
		unknown.length === items.length &&
		missing.includes('exit_weight') &&
		missing.every((m) => m === 'exit_weight' || m === 'main_canopy');
	if (unused) return null;
	return { count: unknown.length, text: missingText(missing), missing };
}

export const WEIGHT_MESSAGES: Record<string, string> = {
	exit_weight_invalid: 'Enter an exit weight from 30 to 250 kg (67 to 551 lb), with at most one decimal.',
	missing: 'Choose kilograms or pounds.',
	email_unverified: 'Confirm your email address before saving your exit weight.',
	not_authenticated: 'Your session has ended. Sign in again.',
	invalid_input: 'Enter an exit weight from 30 to 250 kg (67 to 551 lb), with at most one decimal.',
	uncertain:
		'Not confirmed: the service did not answer in time. Reload the page to check before saving again.',
	unavailable: 'The service is unavailable right now. Nothing was saved. Try again later.'
};

export function weightMessage(code: string | undefined): string | undefined {
	return code ? (WEIGHT_MESSAGES[code] ?? WEIGHT_MESSAGES.unavailable) : undefined;
}
