/**
 * Test-only account helpers for the isolated backend. Accounts are created through
 * the public API with the test proxy key, so each gets its own client address and
 * the per-IP registration limit applies per account rather than to the whole run.
 */
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { randomBytes, randomInt } from 'node:crypto';

export const PASSWORD = 'correct horse battery staple';
export const NEW_PASSWORD = 'a different long passphrase';

function required(name: string): string {
	const value = process.env[name];
	if (!value) throw new Error(`${name} must be set for the account e2e tests`);
	return value;
}

const api = () => required('E2E_API_ORIGIN');
const outbox = () => required('E2E_MAIL_OUTBOX');
const proxyKey = () => required('E2E_API_PROXY_KEY');

export function uniqueEmail(label = 'jumper'): string {
	return `${label}-${randomBytes(6).toString('hex')}@example.com`;
}

function clientIp(): string {
	return `10.${randomInt(256)}.${randomInt(256)}.${randomInt(1, 255)}`;
}

async function post(path: string, body: unknown, bearer?: string): Promise<Response> {
	const headers: Record<string, string> = {
		'content-type': 'application/json',
		'x-organiser-proxy-key': proxyKey(),
		'x-organiser-client-ip': clientIp()
	};
	if (bearer) headers.authorization = `Bearer ${bearer}`;
	return fetch(`${api()}/api/skydiver/v1/auth${path}`, {
		method: 'POST',
		headers,
		body: JSON.stringify(body)
	});
}

/** Most recent link of `kind` mailed to `to`, from the local file outbox. */
export async function mailedToken(to: string, kind: 'verify-email' | 'reset-password'): Promise<string> {
	const pattern = new RegExp(`/${kind}\\?token=([A-Za-z0-9_-]+)`);
	for (let attempt = 0; attempt < 20; attempt++) {
		const files = readdirSync(outbox()).sort().reverse();
		for (const file of files) {
			const message = JSON.parse(readFileSync(join(outbox(), file), 'utf8')) as {
				to: string;
				text: string;
			};
			const match = message.to === to ? pattern.exec(message.text) : null;
			if (match) return match[1];
		}
		await new Promise((resolve) => setTimeout(resolve, 100));
	}
	throw new Error(`no ${kind} mail for ${to}`);
}

export async function createAccount(
	{ verified = true, label = 'jumper' }: { verified?: boolean; label?: string } = {}
): Promise<string> {
	const email = uniqueEmail(label);
	const registered = await post('/registrations', { email, password: PASSWORD });
	if (registered.status !== 202) throw new Error(`registration failed: ${registered.status}`);
	if (verified) {
		const token = await mailedToken(email, 'verify-email');
		const confirmed = await post('/email-verification/confirm', { token });
		if (confirmed.status !== 204) throw new Error(`verification failed: ${confirmed.status}`);
	}
	return email;
}

/** Direct API probe: does this raw session secret still authenticate? */
export async function sessionStatus(secret: string): Promise<number> {
	const response = await fetch(`${api()}/api/skydiver/v1/auth/session`, {
		headers: { authorization: `Bearer ${secret}` }
	});
	return response.status;
}

/** Raw API session for `email`, for direct API setup and probes. */
export async function apiSession(email: string, password = PASSWORD): Promise<string> {
	const response = await post('/sessions', { email, password });
	if (response.status !== 201) throw new Error(`sign-in failed: ${response.status}`);
	return ((await response.json()) as { session_secret: string }).session_secret;
}

/** Session of the reviewer account that scripts/verify.sh granted the role to. */
export async function reviewerSession(): Promise<string> {
	return apiSession(required('E2E_REVIEWER_EMAIL'), required('E2E_REVIEWER_PASSWORD'));
}

/** Direct call to a beta API path (not the auth namespace). */
export async function apiCall(
	method: string,
	path: string,
	{ bearer, body }: { bearer?: string; body?: unknown } = {}
): Promise<Response> {
	const headers: Record<string, string> = {};
	if (body !== undefined) headers['content-type'] = 'application/json';
	if (bearer) headers.authorization = `Bearer ${bearer}`;
	return fetch(`${api()}/api/skydiver/v1${path}`, {
		method,
		headers,
		body: body === undefined ? undefined : JSON.stringify(body)
	});
}
