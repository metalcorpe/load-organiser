import { describe, expect, it } from 'vitest';
import { parseAppOrigin } from './api/origin.ts';
import {
	DEV_COOKIE_NAME,
	SECURE_COOKIE_NAME,
	parseCookieMode,
	parseProxyKey,
	sessionCookieConfig
} from './session-config.ts';

describe('session cookie configuration', () => {
	it('defaults to the __Host- Secure cookie', () => {
		expect(parseCookieMode(undefined)).toBe('secure');
		expect(parseCookieMode('')).toBe('secure');
		expect(sessionCookieConfig('secure', 'https://app.example')).toEqual({
			name: SECURE_COOKIE_NAME,
			secure: true
		});
		expect(SECURE_COOKIE_NAME.startsWith('__Host-')).toBe(true);
	});

	it('allows the non-Secure dev cookie only for a loopback app origin', () => {
		expect(sessionCookieConfig('localhost-dev', 'http://127.0.0.1:5173')).toEqual({
			name: DEV_COOKIE_NAME,
			secure: false
		});
		expect(() => sessionCookieConfig('localhost-dev', 'https://app.example')).toThrow();
		expect(() => sessionCookieConfig('localhost-dev', undefined)).toThrow();
	});

	it('rejects unknown modes and short proxy keys', () => {
		expect(() => parseCookieMode('insecure')).toThrow();
		expect(parseProxyKey(undefined)).toBeUndefined();
		expect(() => parseProxyKey('short')).toThrow();
		expect(parseProxyKey('k'.repeat(32))).toBe('k'.repeat(32));
	});

	it('validates APP_ORIGIN like API_ORIGIN', () => {
		expect(parseAppOrigin('https://app.example/')).toBe('https://app.example');
		expect(() => parseAppOrigin('http://app.example')).toThrow(/APP_ORIGIN/);
		expect(() => parseAppOrigin('https://app.example/path')).toThrow();
	});
});
