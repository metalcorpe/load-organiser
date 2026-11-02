import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { isRedirect } from '@sveltejs/kit';
import { describe, expect, it } from 'vitest';
import { isPrivateRoute, requireViewer, resolveViewer } from './viewer.ts';

const PRIVATE_ROUTES = join(import.meta.dirname, '../../routes/(private)');

describe('private route guard', () => {
	it('has no fabricated viewer before #145', () => {
		expect(resolveViewer()).toBeNull();
	});

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

	it('requires every private server module to call requireViewer itself', () => {
		const serverFiles = readdirSync(PRIVATE_ROUTES, { recursive: true, encoding: 'utf8' }).filter(
			(file) => /(^|[/\\])\+(page|layout)\.server\.ts$|(^|[/\\])\+server\.ts$/.test(file)
		);
		expect(serverFiles).toContain('+layout.server.ts');
		for (const file of serverFiles) {
			expect(readFileSync(join(PRIVATE_ROUTES, file), 'utf8'), file).toMatch(/requireViewer\(/);
		}
	});
});
