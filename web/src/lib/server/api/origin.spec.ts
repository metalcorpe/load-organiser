import { describe, expect, it } from 'vitest';
import { parseApiOrigin } from './origin.ts';

describe('parseApiOrigin', () => {
	it('treats unset/blank as not configured', () => {
		expect(parseApiOrigin(undefined)).toBeUndefined();
		expect(parseApiOrigin('  ')).toBeUndefined();
	});

	it('accepts https origins and loopback http', () => {
		expect(parseApiOrigin('https://api.example.org')).toBe('https://api.example.org');
		expect(parseApiOrigin('https://api.example.org/')).toBe('https://api.example.org');
		expect(parseApiOrigin('http://127.0.0.1:8144')).toBe('http://127.0.0.1:8144');
		expect(parseApiOrigin('http://localhost:8000')).toBe('http://localhost:8000');
	});

	it.each([
		['http://api.example.org', /https/],
		['ftp://api.example.org', /https/],
		['https://user:pw@api.example.org', /credentials/],
		['https://api.example.org/api', /without path/],
		['https://api.example.org?x=1', /without path/],
		['not a url', /absolute/]
	])('rejects %s', (raw, message) => {
		expect(() => parseApiOrigin(raw)).toThrow(message);
	});
});
