import { fail, redirect } from '@sveltejs/kit';
import type {
	ComponentDetailOut,
	JumpDetailOut,
	JumpNumberingOut,
	RecentAircraftOut
} from '#lib/contracts/index.ts';
import { isCountryCode } from '#lib/countries.ts';
import { nextJumpValues, numberHint, proposedNumber } from '#lib/jumps.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { isUuid } from '#lib/server/api/transport.ts';
import { createPlace } from '#lib/server/directory.ts';
import { field } from '#lib/server/forms.ts';
import { jumpBody, newComponent } from '#lib/server/jump-form.ts';
import {
	chosenLocation,
	gearFor,
	loadingFor,
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
	const sameDay = event.url.searchParams.get('day') === 'same';
	const prefill = source?.ok ? nextJumpValues(source.value.jump, { sameDay }) : null;
	// Without "Log the next jump", propose one after the highest number recorded (editable).
	// A jumper who never numbered a jump gets no proposal; a failed read just gives none.
	const numbering =
		chosen && !prefill
			? await call<JumpNumberingOut>(api, 'getJumpNumbering', { bearer: secret })
			: null;
	const highest = numbering?.ok ? numbering.value.highest : null;
	// Without "Log the next jump", the aircraft of the newest jump at this place that
	// recorded one (editable). One call; a failed read just leaves the field empty.
	const recent =
		chosen && !prefill
			? await call<RecentAircraftOut>(api, 'getRecentAircraft', {
					bearer: secret,
					query: {
						venue_id: chosen.venueId ?? undefined,
						place_id: chosen.placeId ?? undefined
					}
				})
			: null;
	const aircraft = recent?.ok ? recent.value.aircraft : null;
	// The usual exit weight and the highest wing loading so far, for the form's note.
	// One call; without an answer the form has no note.
	const loading = chosen ? await loadingFor(api, secret) : null;
	const next = proposedNumber(highest);
	const suggestion = next === null ? null : { number: String(next), hint: numberHint(highest) };
	return {
		emailVerified: viewer.emailVerified,
		placesOk: places !== null,
		places: places ?? [],
		chosen,
		picker: chosen ? null : await pickerData(api, event.url),
		recent: chosen ? [] : await recentLocations(api, secret),
		gear: chosen ? await gearFor(api, secret) : { ok: true, items: [] },
		prefill,
		suggestion,
		aircraft,
		loading,
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
