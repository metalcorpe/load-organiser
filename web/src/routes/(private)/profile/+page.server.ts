import { fail, redirect } from '@sveltejs/kit';
import { statusFor } from '#lib/auth-messages.ts';
import type { ExitWeightSettingOut, LicenceOut, OwnProfileOut } from '#lib/contracts/index.ts';
import { isLicence } from '#lib/currency.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { call, isRecord } from '#lib/server/maintenance.ts';
import { resendVerification } from '#lib/server/identity.ts';
import { listPlans, listSaved } from '#lib/server/opportunities.ts';
import { readSessionSecret } from '#lib/server/session.ts';
import { requireViewer } from '#lib/server/viewer.ts';
import type { Actions, PageServerLoad } from './$types';

const isLicenceOut = (body: unknown) => isRecord(body) && isLicence(body.licence);
const isWeightOut = (body: unknown) =>
	isRecord(body) && (body.unit === 'kg' || body.unit === 'lb') && 'exit_weight' in body;

/**
 * Me: who you are and where your things live. Each summary is what the API answered; a
 * summary that could not be loaded is left out (null), never guessed.
 */
export const load: PageServerLoad = async ({ locals, url, cookies }) => {
	const viewer = requireViewer(locals.viewer, url);
	const secret = readSessionSecret(cookies);
	const api = createRequestApi();
	const [licence, weight, profile, plans, saved] = secret
		? await Promise.all([
				call<LicenceOut>(api, 'getLicence', { bearer: secret }, isLicenceOut),
				call<ExitWeightSettingOut>(api, 'getExitWeight', { bearer: secret }, isWeightOut),
				call<OwnProfileOut | null>(api, 'getOwnProfile', { bearer: secret }, () => true),
				listPlans(api, secret),
				listSaved(api, secret)
			])
		: [null, null, null, null, null];
	return {
		licence: licence?.ok ? licence.value.licence : null,
		exitWeight: weight?.ok ? weight.value : null,
		// undefined: not known; null: no public profile.
		profile: profile?.ok
			? profile.value
				? {
						handle: profile.value.handle,
						displayName: profile.value.display_name,
						discoverable: profile.value.discoverable
					}
				: null
			: undefined,
		plans: plans?.ok ? plans.value.length : null,
		saved: saved?.ok ? saved.value.length : null,
		account: {
			email: viewer.email,
			displayName: viewer.displayName,
			emailVerified: viewer.emailVerified
		}
	};
};

export const actions: Actions = {
	resend: async ({ locals, url, cookies }) => {
		requireViewer(locals.viewer, url);
		const secret = readSessionSecret(cookies);
		if (!secret) redirect(303, '/sign-in');
		const outcome = await resendVerification(createRequestApi(), secret);
		if (!outcome.ok) return fail(statusFor(outcome.reason), { form: 'resend', error: outcome.reason });
		return { form: 'resend', done: true };
	}
};
