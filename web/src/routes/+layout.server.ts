import { DEMO_DATA } from '$app/env/private';
import { THEME_COOKIE, parseTheme } from '#lib/theme.ts';
import type { LayoutServerLoad } from './$types';

// Minimal identity for rendering the current account. Never the session secret.
export const load: LayoutServerLoad = ({ locals, cookies }) => {
	const viewer = locals.viewer;
	return {
		viewer: viewer
			? {
					accountId: viewer.accountId,
					email: viewer.email,
					displayName: viewer.displayName,
					emailVerified: viewer.emailVerified,
					sessionExpiresAt: viewer.sessionExpiresAt,
					reviewer: viewer.reviewer
				}
			: null,
		sessionUnconfirmed: locals.sessionUnconfirmed,
		// The header theme button shows the current choice (theme.ts).
		theme: parseTheme(cookies.get(THEME_COOKIE)),
		// Said once for the whole copy, not per listing (scripts/dev.sh sets it).
		demoData: DEMO_DATA
	};
};
