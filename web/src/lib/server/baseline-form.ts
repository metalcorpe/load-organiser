/**
 * Prior-jump-count input (#154), from the preview query or the save form. The API is
 * the authority on every rule; this only refuses malformed input before sending.
 */
const DATE = /^\d{4}-\d{2}-\d{2}$/;

export type BaselineInput = { prior_jumps: number; before_on: string; version: number | null };

type Source = { get(name: string): FormDataEntryValue | string | null };

function text(source: Source, name: string, max: number): string {
	const value = source.get(name);
	return typeof value === 'string' ? value.slice(0, max).trim() : '';
}

/** The declaration, null when nothing was entered, or an error code. */
export function baselineInput(source: Source): BaselineInput | null | { error: string } {
	const rawCount = text(source, 'prior_jumps', 16).replace(/[\s,]/g, '');
	const beforeOn = text(source, 'before_on', 10);
	if (!rawCount && !beforeOn) return null;
	if (!rawCount || !DATE.test(beforeOn)) return { error: 'missing' };
	if (!/^\d{1,6}$/.test(rawCount)) return { error: 'prior_jumps_invalid' };
	const rawVersion = text(source, 'version', 12);
	const version = /^[1-9]\d{0,9}$/.test(rawVersion) ? Number(rawVersion) : null;
	return { prior_jumps: Number(rawCount), before_on: beforeOn, version };
}
