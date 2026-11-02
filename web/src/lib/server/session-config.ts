/**
 * Session cookie configuration (architecture A4).
 *
 * Production uses `__Host-organiser_session`: Secure, HttpOnly, SameSite=Lax,
 * Path=/, no Domain. A non-Secure cookie exists only as an explicit
 * `localhost-dev` mode, and only for a loopback APP_ORIGIN; production defaults
 * never silently drop Secure.
 */
import { isLoopbackOrigin } from './api/origin.ts';

export type CookieMode = 'secure' | 'localhost-dev';

export const SECURE_COOKIE_NAME = '__Host-organiser_session';
export const DEV_COOKIE_NAME = 'organiser_session_dev';

export function parseCookieMode(raw: string | undefined): CookieMode {
	if (raw === undefined || raw.trim() === '' || raw === 'secure') return 'secure';
	if (raw === 'localhost-dev') return 'localhost-dev';
	throw new Error("SESSION_COOKIE_MODE must be 'secure' or 'localhost-dev'");
}

export function parseProxyKey(raw: string | undefined): string | undefined {
	if (raw === undefined || raw === '') return undefined;
	if (raw.length < 32) throw new Error('API_PROXY_KEY must be at least 32 characters');
	return raw;
}

export interface SessionCookieConfig {
	name: string;
	secure: boolean;
}

export function sessionCookieConfig(
	mode: CookieMode,
	appOrigin: string | undefined
): SessionCookieConfig {
	if (mode === 'localhost-dev') {
		if (!appOrigin || !isLoopbackOrigin(appOrigin)) {
			throw new Error("SESSION_COOKIE_MODE 'localhost-dev' requires a loopback APP_ORIGIN");
		}
		return { name: DEV_COOKIE_NAME, secure: false };
	}
	return { name: SECURE_COOKIE_NAME, secure: true };
}
