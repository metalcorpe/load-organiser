import { redirect } from '@sveltejs/kit';
import { createRequestApi } from '#lib/server/api/client.ts';
import { signOut } from '#lib/server/identity.ts';
import { clearSession, readSessionSecret } from '#lib/server/session.ts';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = ({ locals }) => {
	if (!locals.viewer) redirect(303, '/sign-in');
	return {};
};

export const actions: Actions = {
	// POST only: GET never changes session state.
	default: async ({ cookies, locals }) => {
		const secret = readSessionSecret(cookies);
		let confirmed = true;
		if (secret) confirmed = (await signOut(createRequestApi(), secret)).ok;
		clearSession(cookies);
		locals.clearSiteCache = true;
		redirect(303, confirmed ? '/sign-in?notice=signed-out' : '/sign-in?notice=signed-out-unconfirmed');
	}
};
