import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { COUNTRY_CODES, COUNTRY_OPTIONS, countryName, isCountryCode } from './countries.ts';

describe('countries', () => {
	it('matches the API list exactly', () => {
		const python = readFileSync(
			fileURLToPath(new URL('../../../backend/app/skydiver/directory/countries.py', import.meta.url)),
			'utf8'
		);
		const block = python.split('"""')[3];
		const backend = block.match(/\b[A-Z]{2}\b/g) ?? [];
		expect([...COUNTRY_CODES].sort()).toEqual([...backend].sort());
		expect(new Set(COUNTRY_CODES).size).toBe(249);
	});

	it('names every code and sorts options by name', () => {
		for (const code of COUNTRY_CODES) expect(countryName(code)).not.toBe(code);
		const names = COUNTRY_OPTIONS.map((o) => o.name);
		expect(names).toEqual([...names].sort((a, b) => a.localeCompare(b, 'en')));
		expect(isCountryCode('ES')).toBe(true);
		expect(isCountryCode('UK')).toBe(false);
	});
});
