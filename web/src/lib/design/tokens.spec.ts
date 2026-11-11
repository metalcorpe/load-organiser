import { readFileSync } from 'node:fs';
import Color from 'colorjs.io';
import StyleDictionary from 'style-dictionary';
import { describe, expect, it } from 'vitest';

// The generated CSS must be what Style Dictionary builds from the token files now.
describe('generated tokens', () => {
	for (const config of ['sd.light.json', 'sd.dark.json']) {
		it(`${config} output is up to date (npm run tokens:build)`, async () => {
			const sd = new StyleDictionary(config, { verbosity: 'silent' });
			const [file] = await sd.formatPlatform('css');
			const committed = readFileSync(file.destination ?? '', 'utf8');
			expect(committed).toBe(file.output);
		});
	}
});

type Tokens = Record<string, unknown>;
const load = (name: string): Tokens =>
	JSON.parse(readFileSync(`src/lib/design/tokens/${name}.json`, 'utf8')) as Tokens;

function value(tokens: Tokens, path: string): string {
	const token = path.split('.').reduce<unknown>((at, key) => (at as Tokens)[key], tokens);
	return (token as { $value: string }).$value;
}

// Text needs 4.5:1; large numbers on the brand card and non-text icons need 3:1 (WCAG 2.1).
const PAIRS: [fg: string, bg: string, minimum: number][] = [
	['fg', 'bg', 4.5],
	['fg', 'surface', 4.5],
	['muted', 'bg', 4.5],
	['muted', 'surface', 4.5],
	['accent', 'surface', 4.5],
	['accent', 'bg', 4.5],
	['accent-fg', 'accent', 4.5],
	['brand-fg', 'brand', 4.5],
	['brand-muted', 'brand', 4.5],
	['highlight', 'brand', 3],
	['icon', 'bg', 3],
	['boogie.fg', 'boogie.bg', 4.5],
	['camp.fg', 'camp.bg', 4.5],
	['course.fg', 'course.bg', 4.5],
	['event.fg', 'event.bg', 4.5],
	['boogie.fg', 'surface', 4.5],
	['camp.fg', 'surface', 4.5],
	['course.fg', 'surface', 4.5],
	['event.fg', 'surface', 4.5],
	['warn.fg', 'warn.bg', 4.5],
	['ok.fg', 'ok.bg', 4.5],
	['bad.fg', 'bad.bg', 4.5]
];

describe('token contrast', () => {
	for (const theme of ['light', 'dark']) {
		const tokens = load(theme);
		it.each(PAIRS)(`${theme}: %s on %s ≥ %d`, (fg, bg, minimum) => {
			const ratio = new Color(value(tokens, fg)).contrast(new Color(value(tokens, bg)), 'WCAG21');
			expect(ratio).toBeGreaterThanOrEqual(minimum);
		});
	}
});
