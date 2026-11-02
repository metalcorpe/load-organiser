import { fail } from '@sveltejs/kit';
import { statusFor } from '#lib/auth-messages.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { confirmEmail } from '#lib/server/identity.ts';
import type { Actions, PageServerLoad } from './$types';

const TOKEN = /^[A-Za-z0-9_-]{20,128}$/;

// GET never consumes the token (link scanners must not confirm addresses);
// the visitor confirms with a POST. The token stays in the URL, not page data.
export const load: PageServerLoad = ({ url }) => ({
	hasToken: TOKEN.test(url.searchParams.get('token') ?? '')
});

export const actions: Actions = {
	default: async ({ url }) => {
		const token = url.searchParams.get('token') ?? '';
		if (!TOKEN.test(token)) return fail(400, { error: 'invalid_or_expired_token' });
		const outcome = await confirmEmail(createRequestApi(), token);
		if (!outcome.ok) return fail(statusFor(outcome.reason), { error: outcome.reason });
		return { verified: true };
	}
};
