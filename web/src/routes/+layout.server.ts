import type { LayoutServerLoad } from './$types';

// Minimal identity for rendering the current account. Never the session secret.
export const load: LayoutServerLoad = ({ locals }) => {
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
		sessionUnconfirmed: locals.sessionUnconfirmed
	};
};
