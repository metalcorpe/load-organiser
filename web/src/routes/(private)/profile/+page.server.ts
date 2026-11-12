import { fail, redirect } from '@sveltejs/kit';
import { statusFor } from '#lib/auth-messages.ts';
import type { LicenceOut } from '#lib/contracts/index.ts';
import { isLicence } from '#lib/currency.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { field } from '#lib/server/forms.ts';
import { call, failStatus, isRecord } from '#lib/server/maintenance.ts';
import {
	changePassword,
	deleteAccount,
	resendVerification,
	revokeAllSessions
} from '#lib/server/identity.ts';
import { clearSession, readSessionSecret } from '#lib/server/session.ts';
import { requireViewer } from '#lib/server/viewer.ts';
import type { Actions, PageServerLoad } from './$types';

const isLicenceOut = (body: unknown) => isRecord(body) && isLicence(body.licence);

export const load: PageServerLoad = async ({ locals, url, cookies }) => {
	const viewer = requireViewer(locals.viewer, url);
	const secret = readSessionSecret(cookies);
	// Without an answer the licence form still shows; only the current value is unknown.
	const licence = secret
		? await call<LicenceOut>(createRequestApi(), 'getLicence', { bearer: secret }, isLicenceOut)
		: null;
	return {
		licence: licence?.ok ? licence.value.licence : null,
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

	licence: async ({ locals, url, cookies, request }) => {
		const secret = secretOrSignIn(locals, url, cookies);
		const value = field(await request.formData(), 'licence', { max: 8 });
		if (!isLicence(value)) return fail(400, { form: 'licence', error: 'missing' });
		const outcome = await call<LicenceOut>(
			createRequestApi(),
			'setLicence',
			{ bearer: secret, body: { licence: value } },
			isLicenceOut
		);
		if (!outcome.ok) return fail(failStatus(outcome), { form: 'licence', error: outcome.reason });
		return { form: 'licence', done: true };
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
