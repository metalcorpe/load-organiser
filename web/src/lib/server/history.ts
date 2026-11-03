/** Response checks for personal history (#154). The API remains the authority. */
import type { BaselinePreviewOut, HistoryOut, TotalsOut } from '#lib/contracts/index.ts';

function isTotals(value: unknown): value is TotalsOut {
	const t = value as TotalsOut | null;
	return (
		typeof t === 'object' &&
		t !== null &&
		typeof t.recorded === 'number' &&
		typeof t.inconsistent === 'boolean'
	);
}

export function isHistory(body: unknown): boolean {
	const b = body as HistoryOut | null;
	return (
		typeof b === 'object' &&
		b !== null &&
		isTotals(b.totals) &&
		Array.isArray(b.months) &&
		Array.isArray(b.by_type) &&
		Array.isArray(b.by_location) &&
		Array.isArray(b.by_component) &&
		Array.isArray(b.baseline_events)
	);
}

export function isPreview(body: unknown): boolean {
	const b = body as BaselinePreviewOut | null;
	return typeof b === 'object' && b !== null && isTotals(b.current) && isTotals(b.proposed);
}
