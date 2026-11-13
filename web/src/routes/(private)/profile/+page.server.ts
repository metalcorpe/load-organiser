import { fail, redirect } from '@sveltejs/kit';
import { statusFor } from '#lib/auth-messages.ts';
import type { ExitWeightSettingOut, LicenceOut } from '#lib/contracts/index.ts';
import { isLicence } from '#lib/currency.ts';
import { parseWeight, type WeightUnit } from '#lib/wing-loading.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { field } from '#lib/server/forms.ts';
import { call, failStatus, isRecord } from '#lib/server/maintenance.ts';
import { resendVerification } from '#lib/server/identity.ts';
import { readSessionSecret } from '#lib/server/session.ts';
import { requireViewer } from '#lib/server/viewer.ts';
import type { Actions, PageServerLoad } from './$types';

const isLicenceOut = (body: unknown) => isRecord(body) && isLicence(body.licence);
const isWeightOut = (body: unknown) =>
	isRecord(body) && (body.unit === 'kg' || body.unit === 'lb') && 'exit_weight' in body;
const isUnit = (value: string): value is WeightUnit => value === 'kg' || value === 'lb';

export const load: PageServerLoad = async ({ locals, url, cookies }) => {
	const viewer = requireViewer(locals.viewer, url);
	const secret = readSessionSecret(cookies);
	// Without an answer the forms still show; only the current value is unknown.
	const api = createRequestApi();
	const [licence, weight] = secret
		? await Promise.all([
				call<LicenceOut>(api, 'getLicence', { bearer: secret }, isLicenceOut),
				call<ExitWeightSettingOut>(api, 'getExitWeight', { bearer: secret }, isWeightOut)
			])
		: [null, null];
	return {
		licence: licence?.ok ? licence.value.licence : null,
		exitWeight: weight?.ok ? weight.value : null,
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

// Password, sign out everywhere and account deletion are on /profile/account.
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

	exitWeight: async ({ locals, url, cookies, request }) => {
		const secret = secretOrSignIn(locals, url, cookies);
		const data = await request.formData();
		const unit = field(data, 'exit_weight_unit', { max: 2 });
		const raw = field(data, 'exit_weight', { max: 12, trim: true });
		const values = { exit_weight: raw, exit_weight_unit: unit };
		if (!isUnit(unit)) return fail(400, { form: 'exitWeight', error: 'missing', values });
		const grams = parseWeight(raw, unit);
		if (grams === 'invalid') {
			return fail(400, { form: 'exitWeight', error: 'exit_weight_invalid', values });
		}
		const outcome = await call<ExitWeightSettingOut>(
			createRequestApi(),
			'setExitWeight',
			{
				bearer: secret,
				body: { value: grams === null ? null : Number(raw.replace(',', '.')), unit }
			},
			isWeightOut
		);
		if (!outcome.ok) {
			return fail(failStatus(outcome), { form: 'exitWeight', error: outcome.reason, values });
		}
		return { form: 'exitWeight', done: true, cleared: grams === null };
	}
};
