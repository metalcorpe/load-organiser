/**
 * A Server-Timing header for the browser's developer tools: how long this server spent on the
 * session check, on each API call, and in all. Names and durations only; never URLs, ids or
 * anything from a response.
 */
export interface UpstreamTiming {
	/** The API operation (OperationId), e.g. listJumps. */
	name: string;
	ms: number;
}

const safe = (name: string) => name.replace(/[^A-Za-z0-9_-]/g, '');
const dur = (ms: number) => ms.toFixed(1);

export function serverTimingHeader(
	calls: UpstreamTiming[],
	totals: { viewer?: number; total: number }
): string {
	const seen = new Map<string, number>();
	const parts = calls.map(({ name, ms }) => {
		const base = `api-${safe(name)}`;
		const count = (seen.get(base) ?? 0) + 1;
		seen.set(base, count);
		return `${count === 1 ? base : `${base}-${count}`};dur=${dur(ms)}`;
	});
	if (totals.viewer !== undefined) parts.push(`viewer;dur=${dur(totals.viewer)}`);
	parts.push(`total;dur=${dur(totals.total)}`);
	return parts.join(', ');
}
