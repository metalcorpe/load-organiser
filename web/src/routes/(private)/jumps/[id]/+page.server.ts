import { error, fail, redirect } from '@sveltejs/kit';
import type { ComponentDetailOut, JumpDetailOut, SharingOut } from '#lib/contracts/index.ts';
import { isCountryCode } from '#lib/countries.ts';
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
	placesFor
} from '#lib/server/jump-page.ts';
import { call, failStatus } from '#lib/server/maintenance.ts';
import { echo, version } from '#lib/server/review-forms.ts';
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
	if (!isUuid(event.params.id)) error(404, 'Not found');
	const api = createRequestApi();
	const detail = await call<JumpDetailOut>(api, 'getJump', { bearer: secret, id: event.params.id });
	if (!detail.ok) {
		if (detail.reason === 'not_found') error(404, 'Not found');
		error(503, 'Your logbook is unavailable right now. Try again later.');
	}
	const jump = detail.value.jump;
	const [places, sharing, loading] = await Promise.all([
		placesFor(api, secret),
		call<SharingOut>(api, 'getJumpSharing', { bearer: secret, id: jump.id }),
		// The highest wing loading among the other jumps, for the edit form's note.
		loadingFor(api, secret, jump.id)
	]);
	const changing = event.url.searchParams.get('change') === '1';
	const override = await chosenLocation(api, secret, event.url, places ?? []);
	return {
		emailVerified: viewer.emailVerified,
		detail: detail.value,
		places: places ?? [],
		// Null when sharing could not be read; the page then only links to it.
		post: sharing.ok ? sharing.value.post : null,
		sharingOk: sharing.ok,
		changing,
		override,
		picker: changing ? await pickerData(api, event.url) : null,
		gear: await gearFor(api, secret, jump.components),
		loading,
		componentKey: crypto.randomUUID()
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
		redirect(303, `/jumps/${event.params.id}?place=${created.value.id}`);
	},

	save: async (event) => {
		const secret = secretFor(event);
		const data = await event.request.formData();
		// A refusal re-renders the typed values with the version they were based on, so
		// resending after an edit conflict conflicts again instead of overwriting.
		const based = version(data);
		const refuse = (status: number, error: string) =>
			fail(status, { form: 'save', error, values: echo(data), based });
		const parsed = jumpBody(data);
		if ('error' in parsed) return refuse(400, parsed.error);
		const extra = newComponent(data);
		if (extra === 'invalid') return refuse(400, 'label_required');
		const api = createRequestApi();
		const body = parsed.body;
		if (extra) {
			const component = await call<ComponentDetailOut>(api, 'createComponent', {
				bearer: secret,
				body: { client_key: extra.clientKey, kind: extra.kind, label: extra.label }
			});
			if (!component.ok) return refuse(failStatus(component), component.reason);
			body.component_ids = [...(body.component_ids as string[]), component.value.component.id];
		}
		const updated = await call<JumpDetailOut>(api, 'updateJump', {
			bearer: secret,
			id: event.params.id,
			body: { ...body, version: based }
		});
		if (!updated.ok) return refuse(failStatus(updated), updated.reason);
		redirect(303, `/jumps/${event.params.id}?saved=1`);
	},

	delete: async (event) => {
		const secret = secretFor(event);
		const data = await event.request.formData();
		if (field(data, 'confirm', { max: 4 }) !== 'on') {
			return fail(400, { form: 'delete', error: 'confirm_delete' });
		}
		const v = version(data);
		const result = await call<null>(createRequestApi(), 'deleteJump', {
			bearer: secret,
			id: event.params.id,
			query: { version: v ? String(v) : undefined }
		});
		if (!result.ok) return fail(failStatus(result), { form: 'delete', error: result.reason });
		redirect(303, '/jumps?deleted=1');
	}
};
