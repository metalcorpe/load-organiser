import { describe, expect, it } from 'vitest';
import { isUnsafeMethod, originAllowed } from './origin-check.ts';

describe('unsafe-method Origin check', () => {
	it('treats only GET/HEAD/OPTIONS as safe', () => {
		for (const method of ['GET', 'head', 'OPTIONS']) expect(isUnsafeMethod(method)).toBe(false);
		for (const method of ['POST', 'PUT', 'PATCH', 'DELETE', 'post']) expect(isUnsafeMethod(method)).toBe(true);
	});

	it('accepts only the exact configured origin', () => {
		const app = 'https://app.example';
		expect(originAllowed(app, app)).toBe(true);
		for (const origin of [
			null,
			'null',
			'https://evil.example',
			'http://app.example',
			'https://app.example:444',
			'https://app.example.evil.example',
			'https://APP.example '
		]) {
			expect(originAllowed(origin, app), String(origin)).toBe(false);
		}
	});

	it('refuses everything when APP_ORIGIN is not configured', () => {
		expect(originAllowed('https://app.example', undefined)).toBe(false);
	});
});
