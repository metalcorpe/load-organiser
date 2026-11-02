import type { HealthStatus } from '#lib/contracts/index.ts';
import type { ApiTransport, TransportFailure } from './transport.ts';

/** Sanitized, serializable health outcome safe to place in page data. */
export type HealthOutcome =
	| { kind: 'operational'; checkedAt: string }
	| { kind: 'degraded'; checkedAt: string }
	| TransportFailure;

const STATES = new Set(['ok', 'unavailable']);

export function isHealthStatus(value: unknown): value is HealthStatus {
	if (typeof value !== 'object' || value === null) return false;
	const record = value as Record<string, unknown>;
	return (
		typeof record.status === 'string' &&
		STATES.has(record.status) &&
		typeof record.database === 'string' &&
		STATES.has(record.database) &&
		typeof record.checked_at === 'string' &&
		!Number.isNaN(Date.parse(record.checked_at))
	);
}

export async function fetchHealth(transport: ApiTransport): Promise<HealthOutcome> {
	const result = await transport.request('getHealth');
	if (result.kind !== 'response') return result;

	if (result.status !== 200 && result.status !== 503) {
		return { kind: 'upstream_error', status: result.status };
	}
	if (!isHealthStatus(result.body)) return { kind: 'invalid_response' };

	const checkedAt = new Date(result.body.checked_at).toISOString();
	if (result.status === 200 && result.body.status === 'ok') {
		return { kind: 'operational', checkedAt };
	}
	return { kind: 'degraded', checkedAt };
}
