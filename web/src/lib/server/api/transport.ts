/**
 * Server-only transport to the fixed FastAPI origin.
 *
 * - Constructed per request (no module-level client, token or user state).
 * - Only allowlisted operations: a fixed method + path, never a caller-supplied URL.
 *   A path may contain `{id}`, filled only with a validated UUID; query keys are
 *   allowlisted per operation.
 * - Never forwards browser headers/cookies and never follows redirects.
 * - Failures are reduced to sanitized kinds; upstream bodies/URLs are not exposed.
 */

import { API_TIMEOUT_MS } from '#lib/api-timeouts.ts';

export type FetchLike = (input: string, init: RequestInit) => Promise<Response>;

const BETA = '/api/skydiver/v1';
const AUTH = `${BETA}/auth`;

interface Operation {
	readonly method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
	readonly path: string;
	readonly query?: readonly string[];
	/** Larger response cap for list operations whose bounded size exceeds the default. */
	readonly maxBodyBytes?: number;
}

export const OPERATIONS = {
	getHealth: { method: 'GET', path: '/api/skydiver/v1/health' },
	register: { method: 'POST', path: `${AUTH}/registrations` },
	createSession: { method: 'POST', path: `${AUTH}/sessions` },
	getSession: { method: 'GET', path: `${AUTH}/session` },
	deleteSession: { method: 'DELETE', path: `${AUTH}/session` },
	revokeAllSessions: { method: 'POST', path: `${AUTH}/sessions/revoke-all` },
	changePassword: { method: 'POST', path: `${AUTH}/password` },
	resendVerification: { method: 'POST', path: `${AUTH}/email-verification` },
	confirmEmail: { method: 'POST', path: `${AUTH}/email-verification/confirm` },
	requestPasswordReset: { method: 'POST', path: `${AUTH}/password-reset` },
	resetPassword: { method: 'POST', path: `${AUTH}/password-reset/confirm` },
	searchVenues: {
		method: 'GET',
		path: `${BETA}/venues`,
		query: ['q', 'country', 'cursor', 'limit']
	},
	getVenue: { method: 'GET', path: `${BETA}/venues/{id}` },
	listPlaces: { method: 'GET', path: `${BETA}/places` },
	createPlace: { method: 'POST', path: `${BETA}/places` },
	updatePlace: { method: 'PATCH', path: `${BETA}/places/{id}` },
	deletePlace: { method: 'DELETE', path: `${BETA}/places/{id}` },
	searchOpportunities: {
		method: 'GET',
		path: `${BETA}/opportunities`,
		query: [
			'q',
			'category',
			'country',
			'discipline',
			'audience',
			'provider',
			'venue',
			'from',
			'to',
			'cursor',
			'limit'
		],
		// At most 50 listings with bounded text fields.
		maxBodyBytes: 1024 * 1024
	},
	getOpportunity: { method: 'GET', path: `${BETA}/opportunities/{id}` },
	getProvider: { method: 'GET', path: `${BETA}/providers/{id}` },
	// Bounded by the per-person caps (200 saves, 100 plans) and field limits.
	listSaved: {
		method: 'GET',
		path: `${BETA}/saved`,
		maxBodyBytes: 4 * 1024 * 1024
	},
	getSaved: { method: 'GET', path: `${BETA}/saved/{id}` },
	saveOpportunity: { method: 'PUT', path: `${BETA}/saved/{id}` },
	unsaveOpportunity: { method: 'DELETE', path: `${BETA}/saved/{id}` },
	listPlans: {
		method: 'GET',
		path: `${BETA}/plans`,
		maxBodyBytes: 4 * 1024 * 1024
	},
	createPlan: { method: 'POST', path: `${BETA}/plans` },
	updatePlan: { method: 'PATCH', path: `${BETA}/plans/{id}` },
	deletePlan: { method: 'DELETE', path: `${BETA}/plans/{id}` }
} as const satisfies Record<string, Operation>;

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** True for a canonical UUID string, the only value a path parameter accepts. */
export function isUuid(value: unknown): value is string {
	return typeof value === 'string' && UUID.test(value);
}

/** Per-call inputs. Only values SvelteKit sets explicitly; never browser headers. */
export interface RequestOptions {
	/** JSON body for POST operations. */
	body?: unknown;
	/** Opaque session secret from the HttpOnly cookie. */
	bearer?: string;
	/** Client address from the platform (`getClientAddress`), for API throttling. */
	clientIp?: string;
	/** Path parameter for `{id}` operations; must be a UUID. */
	id?: string;
	/** Query values; only the operation's allowlisted keys are accepted. */
	query?: Record<string, string | undefined>;
}

export type OperationId = keyof typeof OPERATIONS;

export type TransportFailure =
	| { kind: 'not_configured' }
	/** The call itself was invalid (bad path id or query key); nothing was sent. */
	| { kind: 'invalid_request' }
	| { kind: 'unreachable' }
	| { kind: 'timeout' }
	| { kind: 'upstream_error'; status: number }
	| { kind: 'invalid_response' };

export type TransportResult =
	| { kind: 'response'; status: number; body: unknown; retryAfter?: number }
	| TransportFailure;

export interface TransportOptions {
	fetch: FetchLike;
	/** Validated origin from `parseApiOrigin`; `undefined` fails closed. */
	origin: string | undefined;
	timeoutMs?: number;
	/** Upper bound on a JSON body read from upstream. */
	maxBodyBytes?: number;
	/** Shared key that lets the API trust the forwarded client address. */
	proxyKey?: string;
}

const DEFAULT_MAX_BODY_BYTES = 64 * 1024;

export interface ApiTransport {
	request(operation: OperationId, options?: RequestOptions): Promise<TransportResult>;
}

export function createApiTransport(options: TransportOptions): ApiTransport {
	const timeoutMs = options.timeoutMs ?? API_TIMEOUT_MS;
	const maxBodyBytes = options.maxBodyBytes ?? DEFAULT_MAX_BODY_BYTES;

	return {
		async request(operation, call = {}) {
			if (!options.origin) return { kind: 'not_configured' };
			const url = buildPath(OPERATIONS[operation], call);
			if (url === null) return { kind: 'invalid_request' };
			const spec: Operation = OPERATIONS[operation];
			const { method } = spec;
			const bodyLimit = spec.maxBodyBytes ?? maxBodyBytes;

			const headers: Record<string, string> = { accept: 'application/json' };
			if (call.body !== undefined) headers['content-type'] = 'application/json';
			if (call.bearer) headers.authorization = `Bearer ${call.bearer}`;
			if (call.clientIp && options.proxyKey) {
				headers['x-organiser-client-ip'] = call.clientIp;
				headers['x-organiser-proxy-key'] = options.proxyKey;
			}

			let response: Response;
			try {
				response = await options.fetch(`${options.origin}${url}`, {
					method,
					headers,
					body: call.body === undefined ? undefined : JSON.stringify(call.body),
					redirect: 'manual',
					signal: AbortSignal.timeout(timeoutMs)
				});
			} catch (error) {
				return isTimeout(error) ? { kind: 'timeout' } : { kind: 'unreachable' };
			}

			if (response.status >= 300 && response.status < 400) {
				return { kind: 'upstream_error', status: response.status };
			}

			if (response.status === 204) {
				await response.body?.cancel();
				return { kind: 'response', status: 204, body: null };
			}

			const retryAfter = parseRetryAfter(response.headers.get('retry-after'));
			const contentType = response.headers.get('content-type') ?? '';
			if (!contentType.includes('application/json')) {
				return response.ok
					? { kind: 'invalid_response' }
					: { kind: 'upstream_error', status: response.status };
			}

			try {
				const text = await readBounded(response, bodyLimit);
				if (text === null) return { kind: 'invalid_response' };
				const result: TransportResult = {
					kind: 'response',
					status: response.status,
					body: JSON.parse(text)
				};
				if (retryAfter !== undefined) result.retryAfter = retryAfter;
				return result;
			} catch (error) {
				if (isTimeout(error)) return { kind: 'timeout' };
				return { kind: 'invalid_response' };
			}
		}
	};
}

function buildPath(operation: Operation, call: RequestOptions): string | null {
	let path = operation.path;
	if (path.includes('{id}')) {
		if (!isUuid(call.id)) return null;
		path = path.replace('{id}', call.id.toLowerCase());
	} else if (call.id !== undefined) {
		return null;
	}
	const allowed = new Set(operation.query ?? []);
	const params = new URLSearchParams();
	for (const [key, value] of Object.entries(call.query ?? {})) {
		if (!allowed.has(key)) return null;
		if (value !== undefined && value !== '') params.set(key, value);
	}
	const search = params.toString();
	return search ? `${path}?${search}` : path;
}

function parseRetryAfter(raw: string | null): number | undefined {
	if (!raw || !/^\d{1,6}$/.test(raw)) return undefined;
	return Number(raw);
}

/** Reads at most `maxBytes` of the body; returns `null` (and cancels) when it is larger. */
async function readBounded(response: Response, maxBytes: number): Promise<string | null> {
	const declared = Number(response.headers.get('content-length'));
	if (Number.isFinite(declared) && declared > maxBytes) {
		await response.body?.cancel();
		return null;
	}
	if (!response.body) return '';

	const reader = response.body.getReader();
	const chunks: Uint8Array[] = [];
	let total = 0;
	for (;;) {
		const { done, value } = await reader.read();
		if (done) break;
		total += value.byteLength;
		if (total > maxBytes) {
			await reader.cancel();
			return null;
		}
		chunks.push(value);
	}

	const bytes = new Uint8Array(total);
	let offset = 0;
	for (const chunk of chunks) {
		bytes.set(chunk, offset);
		offset += chunk.byteLength;
	}
	return new TextDecoder().decode(bytes);
}

function isTimeout(error: unknown): boolean {
	return (
		typeof error === 'object' &&
		error !== null &&
		'name' in error &&
		(error.name === 'TimeoutError' || error.name === 'AbortError')
	);
}
