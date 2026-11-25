import { describe, expect, it } from 'vitest';
import type { Viewer } from './identity.ts';
import { ViewerCache, cacheable, sessionKey } from './viewer-cache.ts';

const viewer = (expires: string): Viewer => ({
	accountId: 'a',
	personId: 'p',
	email: 'm@example.com',
	displayName: null,
	emailVerified: true,
	sessionExpiresAt: expires,
	reviewer: false
});
const T0 = Date.parse('2026-11-25T12:00:00Z');

describe('ViewerCache', () => {
	it('answers for 30 seconds after a confirmation, then asks again', () => {
		let now = T0;
		const cache = new ViewerCache(() => now);
		cache.remember('k', viewer('2026-11-26T12:00:00Z'));
		now = T0 + 29_999;
		expect(cache.get('k')?.accountId).toBe('a');
		now = T0 + 30_000;
		expect(cache.get('k')).toBeUndefined();
	});

	it('never outlives the session itself', () => {
		let now = T0;
		const cache = new ViewerCache(() => now);
		cache.remember('k', viewer('2026-11-25T12:00:10Z'));
		now = T0 + 10_000;
		expect(cache.get('k')).toBeUndefined();
	});

	it('forgets a session at once, and keeps at most its limit of sessions', () => {
		const cache = new ViewerCache(() => T0, 2);
		cache.remember('a', viewer('2026-11-26T12:00:00Z'));
		cache.remember('b', viewer('2026-11-26T12:00:00Z'));
		cache.forget('a');
		expect(cache.get('a')).toBeUndefined();
		cache.remember('c', viewer('2026-11-26T12:00:00Z'));
		cache.remember('d', viewer('2026-11-26T12:00:00Z'));
		expect(cache.get('b')).toBeUndefined();
		expect(cache.get('c')).toBeDefined();
		expect(cache.get('d')).toBeDefined();
	});
});

describe('sessionKey', () => {
	it('is a SHA-256 digest, never the secret', async () => {
		const secret = 'x'.repeat(43);
		const key = await sessionKey(secret);
		expect(key).toMatch(/^[0-9a-f]{64}$/);
		expect(key).not.toContain(secret);
		expect(await sessionKey(secret)).toBe(key);
	});
});

describe('cacheable', () => {
	it('only plain page and data loads outside the session pages', () => {
		expect(cacheable('GET', '/jumps')).toBe(true);
		expect(cacheable('GET', '/jumps/__data.json')).toBe(true);
		expect(cacheable('HEAD', '/')).toBe(true);
		expect(cacheable('POST', '/jumps')).toBe(false);
		for (const path of ['/sign-in', '/sign-out', '/verify-email', '/verify-email/__data.json', '/register', '/reset-password', '/forgot-password']) {
			expect(cacheable('GET', path), path).toBe(false);
		}
	});
});
