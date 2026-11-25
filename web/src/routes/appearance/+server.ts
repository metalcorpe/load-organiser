import { redirect } from '@sveltejs/kit';
import { safeReturnPath } from '#lib/safe-return.ts';
import { cookieSecure } from '#lib/server/session.ts';
import { THEME_COOKIE, THEME_MAX_AGE_SECONDS, parseTheme } from '#lib/theme.ts';
import type { RequestHandler } from './$types';

/**
 * The header theme button (ThemeToggle) posts here, signed in or not: the choice is a cookie on
 * this device (theme.ts), then back to the same page, which the server renders in the new theme.
 * A cross-site post is refused by hooks.server.ts before it gets here.
 */
export const POST: RequestHandler = async ({ request, cookies }) => {
	const form = await request.formData();
	const value = form.get('theme');
	const theme = parseTheme(typeof value === 'string' ? value : null);
	const options = { path: '/', httpOnly: true, secure: cookieSecure(), sameSite: 'lax' } as const;
	if (theme === 'system') cookies.delete(THEME_COOKIE, options);
	else cookies.set(THEME_COOKIE, theme, { ...options, maxAge: THEME_MAX_AGE_SECONDS });
	const back = form.get('returnTo');
	redirect(303, safeReturnPath(typeof back === 'string' ? back : null) ?? '/');
};
