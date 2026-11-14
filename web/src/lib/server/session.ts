/** Reads and writes the session cookie. The raw secret never leaves server code. */
import type { Cookies } from '@sveltejs/kit';
import { APP_ORIGIN, SESSION_COOKIE_MODE } from '$app/env/private';
import { sessionCookieConfig } from './session-config.ts';

function config() {
	return sessionCookieConfig(SESSION_COOKIE_MODE, APP_ORIGIN);
}

/** Whether cookies must be Secure here (false only in the loopback dev mode). */
export function cookieSecure(): boolean {
	return config().secure;
}

export function readSessionSecret(cookies: Cookies): string | undefined {
	const value = cookies.get(config().name);
	// Opaque URL-safe secret; anything else is not ours.
	return value && /^[A-Za-z0-9_-]{43,128}$/.test(value) ? value : undefined;
}

export function storeSession(cookies: Cookies, secret: string, expiresAt: Date): void {
	const { name, secure } = config();
	cookies.set(name, secret, {
		path: '/',
		httpOnly: true,
		secure,
		sameSite: 'lax',
		expires: expiresAt
	});
}

export function clearSession(cookies: Cookies): void {
	const { name, secure } = config();
	cookies.delete(name, { path: '/', httpOnly: true, secure, sameSite: 'lax' });
}
