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
	/** Longer upstream timeout for bounded bulk operations (restore). */
	readonly timeoutMs?: number;
	/** Return the JSON response as text, unparsed (export files are passed through). */
	readonly raw?: boolean;
}

export const OPERATIONS = {
	getHealth: { method: 'GET', path: '/api/skydiver/v1/health' },
	register: { method: 'POST', path: `${AUTH}/registrations` },
	createSession: { method: 'POST', path: `${AUTH}/sessions` },
	getSession: { method: 'GET', path: `${AUTH}/session` },
	deleteSession: { method: 'DELETE', path: `${AUTH}/session` },
	revokeAllSessions: { method: 'POST', path: `${AUTH}/sessions/revoke-all` },
	deleteAccount: { method: 'POST', path: `${AUTH}/account/deletion` },
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
	deletePlan: { method: 'DELETE', path: `${BETA}/plans/{id}` },
	// Reviewer maintenance (#151); the API enforces the reviewer role.
	listReviewVenues: {
		method: 'GET',
		path: `${BETA}/directory/venues`,
		query: ['q', 'status', 'due', 'cursor', 'limit']
	},
	listReviewProviders: {
		method: 'GET',
		path: `${BETA}/directory/providers`,
		query: ['q', 'status', 'due', 'cursor', 'limit']
	},
	listReviewOpportunities: {
		method: 'GET',
		path: `${BETA}/directory/opportunities`,
		query: ['q', 'status', 'due', 'cursor', 'limit']
	},
	reviewVenue: { method: 'GET', path: `${BETA}/directory/venues/{id}`, maxBodyBytes: 1024 * 1024 },
	createVenue: { method: 'POST', path: `${BETA}/directory/venues` },
	updateVenue: { method: 'PATCH', path: `${BETA}/directory/venues/{id}` },
	addVenueAlias: { method: 'POST', path: `${BETA}/directory/venues/{id}/aliases` },
	setVenueStatus: { method: 'POST', path: `${BETA}/directory/venues/{id}/status` },
	mergeVenue: { method: 'POST', path: `${BETA}/directory/venues/{id}/merge` },
	reviewProvider: {
		method: 'GET',
		path: `${BETA}/directory/providers/{id}`,
		maxBodyBytes: 1024 * 1024
	},
	createProvider: { method: 'POST', path: `${BETA}/directory/providers` },
	updateProvider: { method: 'PATCH', path: `${BETA}/directory/providers/{id}` },
	setProviderStatus: { method: 'POST', path: `${BETA}/directory/providers/{id}/status` },
	mergeProvider: { method: 'POST', path: `${BETA}/directory/providers/{id}/merge` },
	reviewOpportunity: {
		method: 'GET',
		path: `${BETA}/directory/opportunities/{id}`,
		maxBodyBytes: 1024 * 1024
	},
	createOpportunity: { method: 'POST', path: `${BETA}/directory/opportunities` },
	updateOpportunity: { method: 'PATCH', path: `${BETA}/directory/opportunities/{id}` },
	setOpportunityStatus: { method: 'POST', path: `${BETA}/directory/opportunities/{id}/status` },
	markOpportunityDuplicate: {
		method: 'POST',
		path: `${BETA}/directory/opportunities/{id}/duplicate`
	},
	listReviewSubmissions: {
		method: 'GET',
		path: `${BETA}/directory/submissions`,
		query: ['status', 'cursor', 'limit'],
		// Up to 50 cases with 1,000-character messages and source links.
		maxBodyBytes: 1024 * 1024
	},
	resolveSubmission: { method: 'POST', path: `${BETA}/directory/submissions/{id}/resolve` },
	// Suggestions, corrections and reports (#151).
	createSubmission: { method: 'POST', path: `${BETA}/submissions` },
	listOwnSubmissions: {
		method: 'GET',
		path: `${BETA}/submissions`,
		maxBodyBytes: 1024 * 1024
	},
	// Private gear (#152). Lists are bounded by 50 components and 20 rigs.
	listComponents: {
		method: 'GET',
		path: `${BETA}/gear/components`,
		query: ['archived'],
		maxBodyBytes: 1024 * 1024
	},
	createComponent: { method: 'POST', path: `${BETA}/gear/components` },
	getComponent: {
		method: 'GET',
		path: `${BETA}/gear/components/{id}`,
		maxBodyBytes: 1024 * 1024
	},
	updateComponent: { method: 'PATCH', path: `${BETA}/gear/components/{id}` },
	archiveComponent: { method: 'POST', path: `${BETA}/gear/components/{id}/archive` },
	deleteComponent: {
		method: 'DELETE',
		path: `${BETA}/gear/components/{id}`,
		query: ['version']
	},
	placeComponent: { method: 'POST', path: `${BETA}/gear/components/{id}/rig` },
	addServiceEntry: { method: 'POST', path: `${BETA}/gear/components/{id}/service` },
	listRigs: { method: 'GET', path: `${BETA}/gear/rigs`, maxBodyBytes: 1024 * 1024 },
	createRig: { method: 'POST', path: `${BETA}/gear/rigs` },
	deleteServiceEntry: {
		method: 'DELETE',
		path: `${BETA}/gear/components/{id}/service/{sub}`
	},
	updateRig: { method: 'PATCH', path: `${BETA}/gear/rigs/{id}` },
	listJumps: {
		method: 'GET',
		path: `${BETA}/jumps`,
		query: ['cursor', 'limit'],
		maxBodyBytes: 1024 * 1024
	},
	createJump: { method: 'POST', path: `${BETA}/jumps` },
	getJump: { method: 'GET', path: `${BETA}/jumps/{id}`, maxBodyBytes: 1024 * 1024 },
	updateJump: { method: 'PATCH', path: `${BETA}/jumps/{id}` },
	deleteJump: { method: 'DELETE', path: `${BETA}/jumps/{id}`, query: ['version'] },
	getHistory: { method: 'GET', path: `${BETA}/history`, maxBodyBytes: 1024 * 1024 },
	previewBaseline: {
		method: 'GET',
		path: `${BETA}/history/baseline/preview`,
		query: ['prior_jumps', 'before_on']
	},
	setBaseline: { method: 'PUT', path: `${BETA}/history/baseline` },
	removeBaseline: { method: 'DELETE', path: `${BETA}/history/baseline`, query: ['version'] },
	getRecords: { method: 'GET', path: `${BETA}/records` },
	exportRecords: {
		method: 'GET',
		path: `${BETA}/records/export`,
		raw: true,
		maxBodyBytes: 9 * 1024 * 1024,
		timeoutMs: 30_000
	},
	checkRestore: { method: 'POST', path: `${BETA}/records/restore/check`, timeoutMs: 30_000 },
	restoreRecords: { method: 'POST', path: `${BETA}/records/restore`, timeoutMs: 60_000 },
	getOwnProfile: { method: 'GET', path: `${BETA}/me/profile` },
	saveOwnProfile: { method: 'PUT', path: `${BETA}/me/profile` },
	listFollowRequests: { method: 'GET', path: `${BETA}/me/people/requests`, maxBodyBytes: 512 * 1024 },
	listFollowers: { method: 'GET', path: `${BETA}/me/people/followers`, maxBodyBytes: 512 * 1024 },
	listFollowing: { method: 'GET', path: `${BETA}/me/people/following`, maxBodyBytes: 512 * 1024 },
	listBlocked: { method: 'GET', path: `${BETA}/me/people/blocked`, maxBodyBytes: 512 * 1024 },
	searchPeople: { method: 'GET', path: `${BETA}/people`, query: ['q'] },
	getPerson: { method: 'GET', path: `${BETA}/people/{handle}` },
	followPerson: { method: 'PUT', path: `${BETA}/people/{handle}/follow` },
	unfollowPerson: { method: 'DELETE', path: `${BETA}/people/{handle}/follow` },
	approveFollower: { method: 'POST', path: `${BETA}/me/people/requests/{handle}/approve` },
	rejectFollower: { method: 'DELETE', path: `${BETA}/me/people/requests/{handle}` },
	removeFollower: { method: 'DELETE', path: `${BETA}/me/people/followers/{handle}` },
	blockPerson: { method: 'PUT', path: `${BETA}/people/{handle}/block` },
	unblockPerson: { method: 'DELETE', path: `${BETA}/people/{handle}/block` },
	reportPerson: { method: 'POST', path: `${BETA}/people/{handle}/reports` },
	listSocialReports: {
		method: 'GET',
		path: `${BETA}/social/reports`,
		query: ['status'],
		maxBodyBytes: 1024 * 1024
	},
	decideSocialReport: { method: 'POST', path: `${BETA}/social/reports/{id}/decision` },
	moderateProfile: { method: 'PUT', path: `${BETA}/social/profiles/{handle}/moderation` },
	// Published jump summaries (#157).
	getJumpSharing: { method: 'GET', path: `${BETA}/me/jumps/{id}/sharing` },
	publishJump: { method: 'POST', path: `${BETA}/me/jumps/{id}/post` },
	changePostAudience: { method: 'PUT', path: `${BETA}/me/posts/{id}/audience` },
	unpublishPost: { method: 'DELETE', path: `${BETA}/me/posts/{id}`, query: ['version'] },
	getPost: { method: 'GET', path: `${BETA}/posts/{id}` },
	// 20 cards with 280-character captions and 2,048-character links.
	listPersonPosts: {
		method: 'GET',
		path: `${BETA}/people/{handle}/posts`,
		query: ['before'],
		maxBodyBytes: 512 * 1024
	},
	reportPost: { method: 'POST', path: `${BETA}/posts/{id}/reports` },
	// Following feed and dropzone activity (#158); 20 cards a page.
	getFeed: { method: 'GET', path: `${BETA}/me/feed`, query: ['before'], maxBodyBytes: 512 * 1024 },
	listVenuePosts: {
		method: 'GET',
		path: `${BETA}/venues/{id}/posts`,
		query: ['before'],
		maxBodyBytes: 512 * 1024
	}
} as const satisfies Record<string, Operation>;

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const HANDLE = /^[a-z][a-z0-9_]{2,29}$/;

/** True for a profile handle in its stored (lowercase) form. */
export function isHandle(value: unknown): value is string {
	return typeof value === 'string' && HANDLE.test(value);
}

/** True for a canonical UUID string, the only value a path parameter accepts. */
export function isUuid(value: unknown): value is string {
	return typeof value === 'string' && UUID.test(value);
}

/** Per-call inputs. Only values SvelteKit sets explicitly; never browser headers. */
export interface RequestOptions {
	/** JSON body for POST operations. */
	body?: unknown;
	/** Exact JSON bytes to send instead of `body` (a restore file, fingerprinted upstream). */
	rawBody?: Uint8Array<ArrayBuffer>;
	/** Fresh password for an operation that requires it; sent only to the API. */
	confirmPassword?: string;
	/** Opaque session secret from the HttpOnly cookie. */
	bearer?: string;
	/** Client address from the platform (`getClientAddress`), for API throttling. */
	clientIp?: string;
	/** Path parameter for `{id}` operations; must be a UUID. */
	id?: string;
	/** Second path parameter for `{sub}` operations; must be a UUID. */
	sub?: string;
	/** Path parameter for `{handle}` operations; must be a lowercase profile handle. */
	handle?: string;
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
			const payload =
				call.rawBody ?? (call.body === undefined ? undefined : JSON.stringify(call.body));

			const headers: Record<string, string> = { accept: 'application/json' };
			if (payload !== undefined) headers['content-type'] = 'application/json';
			if (call.confirmPassword) headers['x-organiser-confirm-password'] = call.confirmPassword;
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
					body: payload,
					redirect: 'manual',
					signal: AbortSignal.timeout(spec.timeoutMs ?? timeoutMs)
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
					body: spec.raw && response.ok ? text : JSON.parse(text)
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
	if (path.includes('{handle}')) {
		if (!isHandle(call.handle)) return null;
		path = path.replace('{handle}', call.handle);
	} else if (call.handle !== undefined) {
		return null;
	}
	if (path.includes('{sub}')) {
		if (!isUuid(call.sub)) return null;
		path = path.replace('{sub}', call.sub.toLowerCase());
	} else if (call.sub !== undefined) {
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
