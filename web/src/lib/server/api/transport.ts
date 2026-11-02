/**
 * Server-only transport to the fixed FastAPI origin.
 *
 * - Constructed per request (no module-level client, token or user state).
 * - Only allowlisted operations: a fixed method + path, never a caller-supplied URL.
 * - Never forwards browser headers/cookies and never follows redirects.
 * - Failures are reduced to sanitized kinds; upstream bodies/URLs are not exposed.
 */

import { API_TIMEOUT_MS } from '#lib/api-timeouts.ts';

export type FetchLike = (input: string, init: RequestInit) => Promise<Response>;

export const OPERATIONS = {
	getHealth: { method: 'GET', path: '/api/skydiver/v1/health' }
} as const;

export type OperationId = keyof typeof OPERATIONS;

export type TransportFailure =
	| { kind: 'not_configured' }
	| { kind: 'unreachable' }
	| { kind: 'timeout' }
	| { kind: 'upstream_error'; status: number }
	| { kind: 'invalid_response' };

export type TransportResult = { kind: 'response'; status: number; body: unknown } | TransportFailure;

export interface TransportOptions {
	fetch: FetchLike;
	/** Validated origin from `parseApiOrigin`; `undefined` fails closed. */
	origin: string | undefined;
	timeoutMs?: number;
	/** Upper bound on a JSON body read from upstream. */
	maxBodyBytes?: number;
}

const DEFAULT_MAX_BODY_BYTES = 64 * 1024;

export interface ApiTransport {
	request(operation: OperationId): Promise<TransportResult>;
}

export function createApiTransport(options: TransportOptions): ApiTransport {
	const timeoutMs = options.timeoutMs ?? API_TIMEOUT_MS;
	const maxBodyBytes = options.maxBodyBytes ?? DEFAULT_MAX_BODY_BYTES;

	return {
		async request(operation) {
			if (!options.origin) return { kind: 'not_configured' };
			const { method, path } = OPERATIONS[operation];

			let response: Response;
			try {
				response = await options.fetch(`${options.origin}${path}`, {
					method,
					headers: { accept: 'application/json' },
					redirect: 'manual',
					signal: AbortSignal.timeout(timeoutMs)
				});
			} catch (error) {
				return isTimeout(error) ? { kind: 'timeout' } : { kind: 'unreachable' };
			}

			if (response.status >= 300 && response.status < 400) {
				return { kind: 'upstream_error', status: response.status };
			}

			const contentType = response.headers.get('content-type') ?? '';
			if (!contentType.includes('application/json')) {
				return response.ok
					? { kind: 'invalid_response' }
					: { kind: 'upstream_error', status: response.status };
			}

			try {
				const text = await response.text();
				if (new TextEncoder().encode(text).byteLength > maxBodyBytes) {
					return { kind: 'invalid_response' };
				}
				return { kind: 'response', status: response.status, body: JSON.parse(text) };
			} catch (error) {
				if (isTimeout(error)) return { kind: 'timeout' };
				return { kind: 'invalid_response' };
			}
		}
	};
}

function isTimeout(error: unknown): boolean {
	return (
		typeof error === 'object' &&
		error !== null &&
		'name' in error &&
		(error.name === 'TimeoutError' || error.name === 'AbortError')
	);
}
