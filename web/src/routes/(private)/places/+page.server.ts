import { fail, redirect } from '@sveltejs/kit';
import { isCountryCode } from '#lib/countries.ts';
import { directoryStatus } from '#lib/directory-messages.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { isUuid } from '#lib/server/api/transport.ts';
import {
	createPlace,
	deletePlace,
	listPlaces,
	searchVenues,
	updatePlace
} from '#lib/server/directory.ts';
import { field } from '#lib/server/forms.ts';
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
	const places = await listPlaces(api, secret);

	// Linking mode: search listed dropzones for one of the viewer's places.
	const linking = event.url.searchParams.get('link') ?? '';
	const q = (event.url.searchParams.get('q') ?? '').trim().slice(0, 80);
	let matches = null;
	if (isUuid(linking) && q) {
		const found = await searchVenues(api, { q, limit: 10 });
		matches = found.ok ? { ok: true as const, items: found.value.items } : { ok: false as const, reason: found.reason };
	}

	return {
		emailVerified: viewer.emailVerified,
		places: places.ok ? { ok: true as const, items: places.value } : { ok: false as const, reason: places.reason },
		linking: isUuid(linking) ? linking : null,
		q,
		matches
	};
};

function placeId(data: FormData): string | null {
	const id = field(data, 'id', { max: 64 });
	return isUuid(id) ? id : null;
}

export const actions: Actions = {
	create: async (event) => {
		const secret = secretFor(event);
		const data = await event.request.formData();
		const name = field(data, 'name', { max: 200, trim: true });
		const country = field(data, 'country', { max: 2 });
		if (!name || !isCountryCode(country)) return fail(400, { form: 'create', error: 'missing', name });
		const outcome = await createPlace(createRequestApi(), secret, { name, country });
		if (!outcome.ok) {
			return fail(directoryStatus(outcome.reason), { form: 'create', error: outcome.reason, name });
		}
		return { form: 'create', done: true };
	},

	rename: async (event) => {
		const secret = secretFor(event);
		const data = await event.request.formData();
		const id = placeId(data);
		const name = field(data, 'name', { max: 200, trim: true });
		const country = field(data, 'country', { max: 2 });
		if (!id) return fail(404, { form: 'rename', error: 'not_found' });
		if (!name || !isCountryCode(country)) return fail(400, { form: 'rename', id, error: 'missing' });
		const outcome = await updatePlace(createRequestApi(), secret, id, { name, country });
		if (!outcome.ok) return fail(directoryStatus(outcome.reason), { form: 'rename', id, error: outcome.reason });
		return { form: 'rename', id, done: true };
	},

	link: async (event) => {
		const secret = secretFor(event);
		const data = await event.request.formData();
		const id = placeId(data);
		const venueId = field(data, 'venue_id', { max: 64 });
		if (!id || !isUuid(venueId)) return fail(404, { form: 'link', error: 'not_found' });
		const outcome = await updatePlace(createRequestApi(), secret, id, { venue_id: venueId });
		if (!outcome.ok) return fail(directoryStatus(outcome.reason), { form: 'link', id, error: outcome.reason });
		redirect(303, '/places');
	},

	unlink: async (event) => {
		const secret = secretFor(event);
		const id = placeId(await event.request.formData());
		if (!id) return fail(404, { form: 'unlink', error: 'not_found' });
		const outcome = await updatePlace(createRequestApi(), secret, id, { venue_id: null });
		if (!outcome.ok) return fail(directoryStatus(outcome.reason), { form: 'unlink', id, error: outcome.reason });
		return { form: 'unlink', id, done: true };
	},

	remove: async (event) => {
		const secret = secretFor(event);
		const id = placeId(await event.request.formData());
		if (!id) return fail(404, { form: 'remove', error: 'not_found' });
		const outcome = await deletePlace(createRequestApi(), secret, id);
		if (!outcome.ok) return fail(directoryStatus(outcome.reason), { form: 'remove', id, error: outcome.reason });
		return { form: 'remove', done: true };
	}
};
