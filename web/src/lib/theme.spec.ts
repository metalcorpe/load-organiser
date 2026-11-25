import { describe, expect, it } from 'vitest';
import { THEMES, htmlTheme, nextTheme, parseTheme } from './theme.ts';

describe('parseTheme', () => {
	it('keeps light and dark', () => {
		expect(parseTheme('light')).toBe('light');
		expect(parseTheme('dark')).toBe('dark');
	});

	it('treats anything else, or nothing, as following the system', () => {
		for (const value of [undefined, null, '', 'system', 'Dark', 'blue', 'dark;x']) {
			expect(parseTheme(value)).toBe('system');
		}
	});

	it('offers system first', () => {
		expect(THEMES.map((theme) => theme.value)).toEqual(['system', 'light', 'dark']);
	});
});

describe('htmlTheme', () => {
	const page = '<html lang="en-GB" %lo.theme%><meta name="color-scheme" content="%lo.color-scheme%" />';

	it('follows the system without an attribute', () => {
		expect(htmlTheme(page, 'system')).toBe(
			'<html lang="en-GB" ><meta name="color-scheme" content="light dark" />'
		);
	});

	it('pins a chosen theme on the root element and the colour scheme', () => {
		expect(htmlTheme(page, 'dark')).toBe(
			'<html lang="en-GB" data-theme="dark"><meta name="color-scheme" content="dark" />'
		);
		expect(htmlTheme(page, 'light')).toBe(
			'<html lang="en-GB" data-theme="light"><meta name="color-scheme" content="light" />'
		);
	});
});

describe('nextTheme', () => {
	it('cycles device setting, light, dark, then back', () => {
		expect(nextTheme('system')).toBe('light');
		expect(nextTheme('light')).toBe('dark');
		expect(nextTheme('dark')).toBe('system');
	});
});
