import { fail, redirect } from '@sveltejs/kit';
import { listingStatus } from '#lib/listings.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { isUuid } from '#lib/server/api/transport.ts';
import { getVenue, listPlaces } from '#lib/server/directory.ts';
import { field } from '#lib/server/forms.ts';
import {
	createPlan,
	deletePlan,
	getOpportunity,
	listPlans,
	updatePlan
} from '#lib/server/opportunities.ts';
import { readSessionSecret } from '#lib/server/session.ts';
import { requireViewer } from '#lib/server/viewer.ts';
import type { Actions, PageServerLoad, RequestEvent } from './$types';

const DATE = /^\d{4}-\d{2}-\d{2}$/;

function secretFor(event: Pick<RequestEvent, 'locals' | 'url' | 'cookies'>): string {
	requireViewer(event.locals.viewer, event.url);
	const secret = readSessionSecret(event.cookies);
	if (!secret) redirect(303, '/sign-in');
	return secret;
}

/** Optional starting point for a new plan, from a listing or dropzone page. */
async function startingPoint(api: ReturnType<typeof createRequestApi>, url: URL) {
	const opportunity = url.searchParams.get('opportunity');
	if (isUuid(opportunity)) {
		const found = await getOpportunity(api, opportunity);
		if (found.ok) {
			const item = found.value.value;
			return {
				kind: 'opportunity' as const,
				id: item.id,
				title: item.title,
				startsOn: item.starts_on ?? '',
				endsOn: item.ends_on ?? ''
			};
		}
	}
	const venue = url.searchParams.get('venue');
	if (isUuid(venue)) {
		const found = await getVenue(api, venue);
		if (found.ok) {
			const dz = found.value.venue;
			return {
				kind: 'venue' as const,
				id: dz.id,
				title: dz.name,
				startsOn: '',
				endsOn: ''
			};
		}
	}
	return null;
}

export const load: PageServerLoad = async (event) => {
	const secret = secretFor(event);
	const viewer = requireViewer(event.locals.viewer, event.url);
	const api = createRequestApi();
	const [plans, places, start] = await Promise.all([
		listPlans(api, secret),
		listPlaces(api, secret),
		startingPoint(api, event.url)
	]);
	return {
		emailVerified: viewer.emailVerified,
		plans: plans.ok
			? { ok: true as const, items: plans.value }
			: { ok: false as const, reason: plans.reason },
		places: places.ok ? places.value.map((p) => ({ id: p.id, name: p.name })) : [],
		start
	};
};

function planFields(data: FormData) {
	const title = field(data, 'title', { max: 400, trim: true });
	const startsOn = field(data, 'starts_on', { max: 10 });
	const endsOn = field(data, 'ends_on', { max: 10 });
	const note = field(data, 'note', { max: 2000, trim: true });
	if (!title || !DATE.test(startsOn) || !DATE.test(endsOn)) return null;
	return { title, starts_on: startsOn, ends_on: endsOn, note: note || null };
}

export const actions: Actions = {
	create: async (event) => {
		const secret = secretFor(event);
		const data = await event.request.formData();
		const fields = planFields(data);
		if (!fields) return fail(400, { form: 'create', error: 'missing' });
		const link: Record<string, string> = {};
		for (const name of ['opportunity_id', 'venue_id', 'place_id'] as const) {
			const value = field(data, name, { max: 64 });
			if (value && isUuid(value)) link[name] = value;
		}
		const outcome = await createPlan(createRequestApi(), secret, {
			...fields,
			...link
		});
		if (!outcome.ok) {
			return fail(listingStatus(outcome.reason), {
				form: 'create',
				error: outcome.reason
			});
		}
		redirect(303, '/plans?created=1');
	},

	update: async (event) => {
		const secret = secretFor(event);
		const data = await event.request.formData();
		const id = field(data, 'id', { max: 64 });
		if (!isUuid(id)) return fail(404, { form: 'update', error: 'not_found' });
		const fields = planFields(data);
		if (!fields) return fail(400, { form: 'update', id, error: 'missing' });
		const outcome = await updatePlan(createRequestApi(), secret, id, fields);
		if (!outcome.ok) {
			return fail(listingStatus(outcome.reason), {
				form: 'update',
				id,
				error: outcome.reason
			});
		}
		return { form: 'update', id, done: true };
	},

	remove: async (event) => {
		const secret = secretFor(event);
		const id = field(await event.request.formData(), 'id', { max: 64 });
		if (!isUuid(id)) return fail(404, { form: 'remove', error: 'not_found' });
		const outcome = await deletePlan(createRequestApi(), secret, id);
		if (!outcome.ok) {
			return fail(listingStatus(outcome.reason), {
				form: 'remove',
				id,
				error: outcome.reason
			});
		}
		return { form: 'remove', done: true };
	}
};
