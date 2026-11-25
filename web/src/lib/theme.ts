/**
 * Appearance: follow the device (the default), or always light, or always dark.
 *
 * The choice is a cookie on this device, not an account setting, so the server can render the
 * page in the chosen theme before anything else loads (no flash) and it works signed out too.
 * hooks.server.ts writes it into app.html; tokens-*-forced.css then outrank the system theme.
 */
export type Theme = 'system' | 'light' | 'dark';

export const THEME_COOKIE = 'theme';

/** A year; choosing "Use device setting" deletes the cookie instead. */
export const THEME_MAX_AGE_SECONDS = 60 * 60 * 24 * 365;

export const THEMES: { value: Theme; label: string }[] = [
	{ value: 'system', label: 'Use device setting' },
	{ value: 'light', label: 'Light' },
	{ value: 'dark', label: 'Dark' }
];

/** A cookie or form value as a theme; anything unknown follows the system. */
export function parseTheme(value: string | null | undefined): Theme {
	return value === 'light' || value === 'dark' ? value : 'system';
}

/** Fills app.html's placeholders: the root element's data-theme and the colour-scheme meta. */
export function htmlTheme(html: string, theme: Theme): string {
	return html
		.replace('%lo.theme%', theme === 'system' ? '' : `data-theme="${theme}"`)
		.replace('%lo.color-scheme%', theme === 'system' ? 'light dark' : theme);
}
