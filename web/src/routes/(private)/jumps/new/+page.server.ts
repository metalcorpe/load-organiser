import { fail, redirect } from '@sveltejs/kit';
import type { ComponentDetailOut, JumpDetailOut } from '#lib/contracts/index.ts';
import { isCountryCode } from '#lib/countries.ts';
import { nextJumpValues } from '#lib/jumps.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { isUuid } from '#lib/server/api/transport.ts';
import { createPlace } from '#lib/server/directory.ts';
import { field } from '#lib/server/forms.ts';
import { jumpBody, newComponent } from '#lib/server/jump-form.ts';
import {
	chosenLocation,
	gearFor,
	pickerData,
	placesFor,
	recentLocations
} from '#lib/server/jump-page.ts';
import { call, failStatus } from '#lib/server/maintenance.ts';
import { echo } from '#lib/server/review-forms.ts';
import { readSessionSecret } from '#lib/server/session.ts';
import { requireViewer } from '#lib/server/viewer.ts';
import type { Actions, PageServerLoad, RequestEvent } from './$types';

function secretFor(event: Pick<RequestEvent, 'locals' | 'url' | 'cookies'>): string {
	requireViewer(event.locals.viewer, event.url);
	const secret = readSessionSecret(event.cookies);
	if (!secret) redirect(303, '/sign-in');
	return secret;
}

export const load: PageServerLoad = async (event) => {
	const viewer = requireViewer(event.locals.viewer, event.url);
	const secret = secretFor(event);
	const api = createRequestApi();
	const places = await placesFor(api, secret);
	const chosen = await chosenLocation(api, secret, event.url, places ?? []);
	// "Log the next jump": start from one of the caller's own jumps. Another person's id
	// answers not found, exactly like a missing one, and then the form starts empty.
	const from = event.url.searchParams.get('from');
	const source =
		chosen && isUuid(from)
			? await call<JumpDetailOut>(api, 'getJump', { bearer: secret, id: from })
			: null;
	const prefill = source?.ok ? nextJumpValues(source.value.jump) : null;
	return {
		emailVerified: viewer.emailVerified,
		placesOk: places !== null,
		places: places ?? [],
		chosen,
		picker: chosen ? null : await pickerData(api, event.url),
		recent: chosen ? [] : await recentLocations(api, secret),
		gear: chosen ? await gearFor(api, secret) : { ok: true, items: [] },
		prefill,
		// One key per rendered form; a refused or unconfirmed send reuses it.
		keys: { jump: crypto.randomUUID(), component: crypto.randomUUID() }
	};
};

export const actions: Actions = {
	place: async (event) => {
		const secret = secretFor(event);
		const data = await event.request.formData();
		const name = field(data, 'name', { max: 200, trim: true });
		const country = field(data, 'country', { max: 2 });
		if (!name || !isCountryCode(country)) return fail(400, { form: 'place', error: 'missing' });
		const created = await createPlace(createRequestApi(), secret, { name, country });
		if (!created.ok) return fail(400, { form: 'place', error: created.reason });
		redirect(303, `/jumps/new?place=${created.value.id}`);
	},

	save: async (event) => {
		const secret = secretFor(event);
		const data = await event.request.formData();
		const values = echo(data);
		const parsed = jumpBody(data);
		if ('error' in parsed) return fail(400, { form: 'save', error: parsed.error, values });
		const clientKey = field(data, 'client_key', { max: 64 });
		const extra = newComponent(data);
		if (extra === 'invalid') return fail(400, { form: 'save', error: 'label_required', values });
		const api = createRequestApi();
		const body = parsed.body;
		if (extra) {
			// Retry-safe: the same key returns the component created by an earlier send.
			const component = await call<ComponentDetailOut>(api, 'createComponent', {
				bearer: secret,
				body: { client_key: extra.clientKey, kind: extra.kind, label: extra.label }
			});
			if (!component.ok) {
				return fail(failStatus(component), { form: 'save', error: component.reason, values });
			}
			body.component_ids = [...(body.component_ids as string[]), component.value.component.id];
		}
		const created = await call<JumpDetailOut>(api, 'createJump', {
			bearer: secret,
			body: {
				...body,
				client_key: clientKey,
				confirm_distinct: data.get('confirm_distinct') === '1'
			}
		});
		if (!created.ok) {
			const duplicateOf =
				created.reason === 'likely_duplicate' && typeof created.body?.duplicate_of === 'string'
					? created.body.duplicate_of
					: null;
			return fail(failStatus(created), {
				form: 'save',
				error: created.reason,
				duplicateOf,
				values
			});
		}
		redirect(303, `/jumps/${created.value.jump.id}?saved=1`);
	}
};
