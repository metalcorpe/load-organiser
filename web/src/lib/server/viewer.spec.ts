import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { isHttpError, isRedirect } from '@sveltejs/kit';
import { describe, expect, it } from 'vitest';
import { requireReviewer } from './reviewer.ts';
import { isPrivateRoute, requireViewer, type Viewer } from './viewer.ts';

const PRIVATE_ROUTES = join(import.meta.dirname, '../../routes/(private)');

describe('private route guard', () => {
	it('identifies private route ids', () => {
		expect(isPrivateRoute('/(private)/records')).toBe(true);
		expect(isPrivateRoute('/status')).toBe(false);
		expect(isPrivateRoute(null)).toBe(false);
	});

	it('redirects anonymous viewers to sign-in with a safe return path', () => {
		try {
			requireViewer(null, new URL('https://app.example/records'));
			expect.unreachable();
		} catch (error) {
			expect(isRedirect(error)).toBe(true);
			if (isRedirect(error)) {
				expect(error.status).toBe(303);
				expect(error.location).toBe('/sign-in?returnTo=%2Frecords');
			}
		}
	});

	it('requires every private server module to call requireViewer (or requireReviewer) itself', () => {
		const serverFiles = readdirSync(PRIVATE_ROUTES, { recursive: true, encoding: 'utf8' }).filter(
			(file) => /(^|[/\\])\+(page|layout)\.server\.ts$|(^|[/\\])\+server\.ts$/.test(file)
		);
		expect(serverFiles).toContain('+layout.server.ts');
		for (const file of serverFiles) {
			expect(readFileSync(join(PRIVATE_ROUTES, file), 'utf8'), file).toMatch(
				/requireViewer\(|requireReviewer\(/
			);
		}
	});

	it('requireReviewer redirects anonymous viewers and hides tools from members', () => {
		const url = new URL('https://app.example/review');
		const secret = 'a'.repeat(43);
		const cookies = { get: () => secret } as never;
		const member: Viewer = {
			accountId: 'a',
			personId: 'p',
			email: 'm@example.com',
			displayName: null,
			emailVerified: true,
			sessionExpiresAt: '2026-11-09T12:00:00.000Z',
			reviewer: false
		};
		expect(() => requireReviewer({ locals: { viewer: null }, url, cookies })).toThrow();
		try {
			requireReviewer({ locals: { viewer: member }, url, cookies });
			expect.unreachable();
		} catch (error) {
			expect(isHttpError(error) && error.status).toBe(404);
		}
		expect(
			requireReviewer({ locals: { viewer: { ...member, reviewer: true } }, url, cookies })
		).toBe(secret);
	});
});
