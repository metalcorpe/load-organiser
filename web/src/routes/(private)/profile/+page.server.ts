import { fail, redirect } from '@sveltejs/kit';
import { statusFor } from '#lib/auth-messages.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { field } from '#lib/server/forms.ts';
import {
	changePassword,
	deleteAccount,
	resendVerification,
	revokeAllSessions
} from '#lib/server/identity.ts';
import { clearSession, readSessionSecret } from '#lib/server/session.ts';
import { requireViewer } from '#lib/server/viewer.ts';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = ({ locals, url }) => {
	const viewer = requireViewer(locals.viewer, url);
	return {
		account: {
			email: viewer.email,
			displayName: viewer.displayName,
			emailVerified: viewer.emailVerified,
			sessionExpiresAt: viewer.sessionExpiresAt
		}
	};
};

function secretOrSignIn(locals: App.Locals, url: URL, cookies: Parameters<typeof readSessionSecret>[0]) {
	requireViewer(locals.viewer, url);
	const secret = readSessionSecret(cookies);
	if (!secret) redirect(303, '/sign-in');
	return secret;
}

export const actions: Actions = {
	resend: async ({ locals, url, cookies }) => {
		const secret = secretOrSignIn(locals, url, cookies);
		const outcome = await resendVerification(createRequestApi(), secret);
		if (!outcome.ok) return fail(statusFor(outcome.reason), { form: 'resend', error: outcome.reason });
		return { form: 'resend', done: true };
	},

	password: async ({ locals, url, cookies, request, getClientAddress }) => {
		const secret = secretOrSignIn(locals, url, cookies);
		const data = await request.formData();
		const current = field(data, 'current_password');
		const next = field(data, 'new_password');
		const confirm = field(data, 'new_password_confirm');
		if (!current || !next) return fail(400, { form: 'password', error: 'missing' });
		if (next !== confirm) return fail(400, { form: 'password', error: 'password_mismatch' });
		const outcome = await changePassword(
			createRequestApi(),
			secret,
			{ current_password: current, new_password: next },
			getClientAddress()
		);
		if (!outcome.ok) return fail(statusFor(outcome.reason), { form: 'password', error: outcome.reason });
		return { form: 'password', done: true };
	},

	revokeAll: async ({ locals, url, cookies, request, getClientAddress }) => {
		const secret = secretOrSignIn(locals, url, cookies);
		const data = await request.formData();
		const password = field(data, 'password');
		if (!password) return fail(400, { form: 'revokeAll', error: 'missing' });
		const outcome = await revokeAllSessions(createRequestApi(), secret, password, getClientAddress());
		if (!outcome.ok) return fail(statusFor(outcome.reason), { form: 'revokeAll', error: outcome.reason });
		clearSession(cookies);
		locals.clearSiteCache = true;
		redirect(303, '/sign-in?notice=signed-out-everywhere');
	},

	deleteAccount: async ({ locals, url, cookies, request, getClientAddress }) => {
		const secret = secretOrSignIn(locals, url, cookies);
		const data = await request.formData();
		if (field(data, 'confirm', { max: 4 }) !== 'on') {
			return fail(400, { form: 'deleteAccount', error: 'confirm_delete' });
		}
		const password = field(data, 'password', { max: 1024 });
		if (!password) return fail(400, { form: 'deleteAccount', error: 'missing' });
		const outcome = await deleteAccount(createRequestApi(), secret, password, getClientAddress());
		if (!outcome.ok) {
			return fail(statusFor(outcome.reason), { form: 'deleteAccount', error: outcome.reason });
		}
		clearSession(cookies);
		locals.clearSiteCache = true;
		redirect(303, '/sign-in?notice=account-deleted');
	}
};
