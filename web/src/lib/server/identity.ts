/**
 * Typed identity calls over the server-only transport (#145).
 *
 * Every outcome is reduced to a small reason code; upstream bodies, URLs and
 * secrets are never passed to pages.
 */
import type { SessionOut, ViewerOut } from '#lib/contracts/index.ts';
import type { ApiTransport, OperationId, RequestOptions } from './api/transport.ts';

/** Minimal request-local identity for rendering. Never contains the session secret. */
export interface Viewer {
	accountId: string;
	personId: string;
	email: string;
	displayName: string | null;
	emailVerified: boolean;
	sessionExpiresAt: string;
}

export type Reason =
	| 'invalid_credentials'
	| 'not_authenticated'
	| 'too_many_attempts'
	| 'registration_closed'
	| 'invalid_or_expired_token'
	| 'password_too_short'
	| 'password_too_long'
	| 'password_confirmation_failed'
	| 'mail_unavailable'
	| 'invalid_input'
	/** Timed out: the API may or may not have completed the operation. */
	| 'uncertain'
	| 'unavailable';

export type Outcome<T> = { ok: true; value: T } | { ok: false; reason: Reason; retryAfter?: number };

const KNOWN = new Set<Reason>([
	'invalid_credentials',
	'not_authenticated',
	'too_many_attempts',
	'registration_closed',
	'invalid_or_expired_token',
	'password_too_short',
	'password_too_long',
	'password_confirmation_failed',
	'mail_unavailable'
]);

async function call(
	api: ApiTransport,
	operation: OperationId,
	options: RequestOptions
): Promise<Outcome<unknown>> {
	const result = await api.request(operation, options);
	if (result.kind === 'timeout') return { ok: false, reason: 'uncertain' };
	if (result.kind !== 'response') return { ok: false, reason: 'unavailable' };
	if (result.status >= 200 && result.status < 300) return { ok: true, value: result.body };

	const detail =
		typeof result.body === 'object' && result.body !== null && 'detail' in result.body
			? (result.body as { detail: unknown }).detail
			: undefined;
	if (typeof detail === 'string' && KNOWN.has(detail as Reason)) {
		const failure: Outcome<never> = { ok: false, reason: detail as Reason };
		if (result.retryAfter !== undefined) failure.retryAfter = result.retryAfter;
		return failure;
	}
	if (result.status === 422 || result.status === 400) return { ok: false, reason: 'invalid_input' };
	if (result.status === 401) return { ok: false, reason: 'not_authenticated' };
	return { ok: false, reason: 'unavailable' };
}

function isViewerOut(value: unknown): value is ViewerOut {
	if (typeof value !== 'object' || value === null) return false;
	const v = value as Record<string, unknown>;
	return (
		typeof v.account_id === 'string' &&
		typeof v.person_id === 'string' &&
		typeof v.email === 'string' &&
		(v.display_name === null || typeof v.display_name === 'string') &&
		typeof v.email_verified === 'boolean' &&
		typeof v.session_expires_at === 'string' &&
		!Number.isNaN(Date.parse(v.session_expires_at))
	);
}

function toViewer(value: ViewerOut): Viewer {
	return {
		accountId: value.account_id,
		personId: value.person_id,
		email: value.email,
		displayName: value.display_name ?? null,
		emailVerified: value.email_verified,
		sessionExpiresAt: new Date(value.session_expires_at).toISOString()
	};
}

function done(outcome: Outcome<unknown>): Outcome<null> {
	return outcome.ok ? { ok: true, value: null } : outcome;
}

export async function getViewer(api: ApiTransport, secret: string): Promise<Outcome<Viewer>> {
	const outcome = await call(api, 'getSession', { bearer: secret });
	if (!outcome.ok) return outcome;
	return isViewerOut(outcome.value)
		? { ok: true, value: toViewer(outcome.value) }
		: { ok: false, reason: 'unavailable' };
}

export async function signIn(
	api: ApiTransport,
	input: { email: string; password: string },
	clientIp: string
): Promise<Outcome<{ secret: string; viewer: Viewer }>> {
	const outcome = await call(api, 'createSession', { body: input, clientIp });
	if (!outcome.ok) return outcome;
	const body = outcome.value as Partial<SessionOut> | null;
	if (
		!body ||
		typeof body.session_secret !== 'string' ||
		!/^[A-Za-z0-9_-]{43,128}$/.test(body.session_secret) ||
		!isViewerOut(body.viewer)
	) {
		return { ok: false, reason: 'unavailable' };
	}
	return { ok: true, value: { secret: body.session_secret, viewer: toViewer(body.viewer) } };
}

export async function signOut(api: ApiTransport, secret: string): Promise<Outcome<null>> {
	return done(await call(api, 'deleteSession', { bearer: secret }));
}

export async function register(
	api: ApiTransport,
	input: { email: string; password: string; display_name: string | null },
	clientIp: string
): Promise<Outcome<null>> {
	return done(await call(api, 'register', { body: input, clientIp }));
}

export async function confirmEmail(api: ApiTransport, token: string): Promise<Outcome<null>> {
	return done(await call(api, 'confirmEmail', { body: { token } }));
}

export async function resendVerification(
	api: ApiTransport,
	secret: string
): Promise<Outcome<null>> {
	return done(await call(api, 'resendVerification', { bearer: secret }));
}

export async function requestPasswordReset(
	api: ApiTransport,
	email: string,
	clientIp: string
): Promise<Outcome<null>> {
	return done(await call(api, 'requestPasswordReset', { body: { email }, clientIp }));
}

export async function resetPassword(
	api: ApiTransport,
	token: string,
	newPassword: string
): Promise<Outcome<null>> {
	return done(
		await call(api, 'resetPassword', { body: { token, new_password: newPassword } })
	);
}

export async function changePassword(
	api: ApiTransport,
	secret: string,
	input: { current_password: string; new_password: string },
	clientIp: string
): Promise<Outcome<null>> {
	return done(await call(api, 'changePassword', { bearer: secret, body: input, clientIp }));
}

export async function revokeAllSessions(
	api: ApiTransport,
	secret: string,
	password: string,
	clientIp: string
): Promise<Outcome<null>> {
	return done(await call(api, 'revokeAllSessions', { bearer: secret, body: { password }, clientIp }));
}
