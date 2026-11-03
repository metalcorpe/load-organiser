import { fail, redirect } from '@sveltejs/kit';
import { safeReturnPath } from '#lib/safe-return.ts';
import { statusFor } from '#lib/auth-messages.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { field } from '#lib/server/forms.ts';
import { signIn, signOut } from '#lib/server/identity.ts';
import { readSessionSecret, storeSession } from '#lib/server/session.ts';
import type { Actions, PageServerLoad } from './$types';

const NOTICES = new Set(['reset', 'signed-out', 'signed-out-everywhere', 'signed-out-unconfirmed', 'verified']);

export const load: PageServerLoad = ({ locals, url }) => {
	const returnTo = safeReturnPath(url.searchParams.get('returnTo'));
	if (locals.viewer) redirect(303, returnTo ?? '/profile');
	const notice = url.searchParams.get('notice');
	return {
		returnTo,
		notice: notice && NOTICES.has(notice) ? notice : null,
		sessionUnconfirmed: locals.sessionUnconfirmed
	};
};

export const actions: Actions = {
	default: async ({ request, cookies, url, getClientAddress, locals }) => {
		const data = await request.formData();
		const email = field(data, 'email', { max: 254, trim: true });
		const password = field(data, 'password');
		if (!email || !password) return fail(400, { email, error: 'missing' });

		const api = createRequestApi();
		const outcome = await signIn(api, { email, password }, getClientAddress());
		if (!outcome.ok) {
			return fail(statusFor(outcome.reason), {
				email,
				error: outcome.reason,
				retryAfter: outcome.retryAfter ?? null
			});
		}

		// A new sign-in replaces any session this browser still holds.
		const previous = readSessionSecret(cookies);
		if (previous) await signOut(api, previous);
		storeSession(cookies, outcome.value.secret, new Date(outcome.value.viewer.sessionExpiresAt));
		// Drop any cached pages (including back/forward cache) from a previous account.
		locals.clearSiteCache = true;
		redirect(303, safeReturnPath(url.searchParams.get('returnTo')) ?? '/');
	}
};
