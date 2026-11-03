/**
 * Reviewer maintenance and submission calls over the server-only transport (#151).
 *
 * Reviewer responses are internal maintenance data: they are checked to be JSON
 * objects of the expected outer shape and typed from the generated contract. A
 * refusal carries the API's rule code (e.g. `provider_in_use`, `edit_conflict`) so
 * the tools can explain it; transport failures are reduced as elsewhere.
 */
import type { ApiTransport, OperationId, RequestOptions } from './api/transport.ts';

export type Refusal =
	| { ok: false; reason: string; status: number; body?: Record<string, unknown> }
	| { ok: false; reason: 'uncertain' | 'unavailable' | 'not_found'; status: 0 };

export type Result<T> = { ok: true; value: T; status: number } | Refusal;

const isRecord = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null;

export async function call<T>(
	api: ApiTransport,
	operation: OperationId,
	options: RequestOptions,
	check: (body: unknown) => boolean = isRecord
): Promise<Result<T>> {
	const result = await api.request(operation, options);
	if (result.kind === 'invalid_request') return { ok: false, reason: 'not_found', status: 0 };
	if (result.kind === 'timeout') return { ok: false, reason: 'uncertain', status: 0 };
	if (result.kind !== 'response') return { ok: false, reason: 'unavailable', status: 0 };
	if (result.status >= 200 && result.status < 300) {
		if (result.status === 204) return { ok: true, value: null as T, status: 204 };
		return check(result.body)
			? { ok: true, value: result.body as T, status: result.status }
			: { ok: false, reason: 'unavailable', status: 0 };
	}
	const detail = isRecord(result.body) ? result.body.detail : undefined;
	if (typeof detail === 'string' && /^[a-z_]{1,64}$/.test(detail)) {
		return { ok: false, reason: detail, status: result.status, body: result.body as Record<string, unknown> };
	}
	if (result.status === 401) return { ok: false, reason: 'not_authenticated', status: 401 };
	if (result.status === 403) return { ok: false, reason: 'forbidden', status: 403 };
	if (result.status === 404) return { ok: false, reason: 'not_found', status: 404 };
	if (result.status === 422) return { ok: false, reason: 'invalid_input', status: 422 };
	return { ok: false, reason: 'unavailable', status: 0 };
}

export const isPage = (v: unknown) =>
	isRecord(v) &&
	Array.isArray(v.items) &&
	v.items.every(isRecord) &&
	(v.next_cursor === null || typeof v.next_cursor === 'string');

export const isList = (v: unknown) => Array.isArray(v) && v.every(isRecord);

export function failStatus(refusal: Refusal): number {
	return refusal.status || 503;
}
