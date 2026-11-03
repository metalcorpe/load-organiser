import { fail, redirect } from '@sveltejs/kit';
import { statusFor } from '#lib/auth-messages.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { field } from '#lib/server/forms.ts';
import { resetPassword } from '#lib/server/identity.ts';
import { clearSession } from '#lib/server/session.ts';
import type { Actions, PageServerLoad } from './$types';

const TOKEN = /^[A-Za-z0-9_-]{20,128}$/;

export const load: PageServerLoad = ({ url }) => ({
	hasToken: TOKEN.test(url.searchParams.get('token') ?? '')
});

export const actions: Actions = {
	default: async ({ request, url, cookies, locals, getClientAddress }) => {
		const token = url.searchParams.get('token') ?? '';
		if (!TOKEN.test(token)) return fail(400, { error: 'invalid_or_expired_token' });
		const data = await request.formData();
		const password = field(data, 'password', { max: 1024 });
		const confirm = field(data, 'password_confirm', { max: 1024 });
		if (!password) return fail(400, { error: 'missing' });
		if (password !== confirm) return fail(400, { error: 'password_mismatch' });

		const outcome = await resetPassword(
			createRequestApi(),
			token,
			password,
			getClientAddress()
		);
		if (!outcome.ok) return fail(statusFor(outcome.reason), { error: outcome.reason });

		// Every session was revoked by the API, including any held by this browser.
		clearSession(cookies);
		locals.clearSiteCache = true;
		redirect(303, '/sign-in?notice=reset');
	}
};
