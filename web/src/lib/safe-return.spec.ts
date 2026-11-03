import { describe, expect, it } from 'vitest';
import { safeReturnPath, signInPath } from './safe-return.ts';

describe('safeReturnPath', () => {
	it.each(['/records', '/records?tab=gear', '/jumps/new'])('keeps same-origin path %s', (raw) => {
		expect(safeReturnPath(raw)).toBe(raw);
	});

	it.each([
		null,
		'',
		'records',
		'//evil.example',
		'/\\evil.example',
		'/.//evil.example',
		'/a/..//evil.example',
		'/%2e//evil.example',
		'/./%2e/..//evil.example',
		'https://evil.example/records',
		'javascript:alert(1)',
		'/records\nSet-Cookie: x',
		`/${'a'.repeat(600)}`
	])('rejects %s', (raw) => {
		expect(safeReturnPath(raw)).toBeNull();
	});

	it('drops fragments', () => {
		expect(safeReturnPath('/records#x')).toBe('/records');
	});
});

describe('signInPath', () => {
	it('encodes the current path as the return destination', () => {
		expect(signInPath(new URL('https://app.example/records?tab=gear'))).toBe(
			'/sign-in?returnTo=%2Frecords%3Ftab%3Dgear'
		);
	});
});
