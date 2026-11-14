import { error, fail, redirect } from '@sveltejs/kit';
import type { ReviewerVenueOut, ReviewVenuePageOut } from '#lib/contracts/index.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { isUuid } from '#lib/server/api/transport.ts';
import { field } from '#lib/server/forms.ts';
import { call, failStatus, isPage } from '#lib/server/maintenance.ts';
import { requireReviewer } from '#lib/server/reviewer.ts';
import { echo, text, version } from '#lib/server/review-forms.ts';
import { OPERATOR_ROWS, type VenueOperator } from '#lib/venue-details.ts';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	const secret = requireReviewer(event);
	const id = event.params.id;
	if (id !== 'new' && !isUuid(id)) error(404, 'Not found');
	const api = createRequestApi();
	const q = (event.url.searchParams.get('merge_q') ?? '').trim().slice(0, 80);
	const [venue, candidates] = await Promise.all([
		id === 'new'
			? Promise.resolve(null)
			: call<ReviewerVenueOut>(api, 'reviewVenue', { bearer: secret, id }),
		q
			? call<ReviewVenuePageOut>(
					api,
					'listReviewVenues',
					{ bearer: secret, query: { q, status: 'listed', limit: '20' } },
					isPage
				)
			: Promise.resolve(null)
	]);
	if (venue && !venue.ok) {
		if (venue.reason === 'not_found') error(404, 'Not found');
		error(503, 'The maintenance service is unavailable right now.');
	}
	return {
		venue: venue ? venue.value : null,
		mergeQ: q,
		mergeTargets: candidates?.ok ? candidates.value.items.filter((v) => v.id !== id) : []
	};
};

/** The operator rows in order; a row without a name is ignored. */
function operators(data: FormData): VenueOperator[] {
	const rows: VenueOperator[] = [];
	for (let i = 0; i < OPERATOR_ROWS; i++) {
		const name = text(data, `operator_name_${i}`, 200);
		if (name) rows.push({ name, url: text(data, `operator_url_${i}`) });
	}
	return rows;
}

function number(data: FormData, name: string): number | null {
	const raw = text(data, name, 24);
	if (raw === null) return null;
	const value = Number(raw);
	return Number.isFinite(value) ? value : null;
}

export const actions: Actions = {
	save: async (event) => {
		const secret = requireReviewer(event);
		const data = await event.request.formData();
		const body = {
			name: text(data, 'name', 200),
			country: text(data, 'country', 2),
			locality: text(data, 'locality', 200),
			latitude: number(data, 'latitude'),
			longitude: number(data, 'longitude'),
			source_url: text(data, 'source_url'),
			source_note: text(data, 'source_note', 400),
			checked_on: text(data, 'checked_on', 10),
			operators: operators(data),
			season: text(data, 'season', 240),
			aircraft: text(data, 'aircraft', 240)
		};
		if (!body.name || !body.country)
			return fail(400, { form: 'save', error: 'missing', values: echo(data) });
		const api = createRequestApi();
		if (event.params.id === 'new') {
			const created = await call<ReviewerVenueOut>(api, 'createVenue', {
				bearer: secret,
				body: { ...body, listed: field(data, 'listed', { max: 4 }) === 'on' }
			});
			if (!created.ok) {
				return fail(failStatus(created), {
					form: 'save',
					error: created.reason,
					values: echo(data)
				});
			}
			redirect(303, `/review/dropzones/${created.value.id}?saved=1`);
		}
		const updated = await call<ReviewerVenueOut>(api, 'updateVenue', {
			bearer: secret,
			id: event.params.id,
			body: { ...body, version: version(data) }
		});
		if (!updated.ok) {
			return fail(failStatus(updated), { form: 'save', error: updated.reason, values: echo(data) });
		}
		return { form: 'save', done: true };
	},

	alias: async (event) => {
		const secret = requireReviewer(event);
		const data = await event.request.formData();
		const name = text(data, 'name', 200);
		if (!name) return fail(400, { form: 'alias', error: 'missing' });
		const result = await call<ReviewerVenueOut>(createRequestApi(), 'addVenueAlias', {
			bearer: secret,
			id: event.params.id,
			body: { name, version: version(data) }
		});
		if (!result.ok) return fail(failStatus(result), { form: 'alias', error: result.reason });
		return { form: 'alias', done: true };
	},

	status: async (event) => {
		const secret = requireReviewer(event);
		const data = await event.request.formData();
		const result = await call<ReviewerVenueOut>(createRequestApi(), 'setVenueStatus', {
			bearer: secret,
			id: event.params.id,
			body: { status: field(data, 'status', { max: 16 }), version: version(data) }
		});
		if (!result.ok) return fail(failStatus(result), { form: 'status', error: result.reason });
		return { form: 'status', done: true };
	},

	merge: async (event) => {
		const secret = requireReviewer(event);
		const data = await event.request.formData();
		const into = field(data, 'into', { max: 64 });
		if (!isUuid(into)) return fail(400, { form: 'merge', error: 'missing' });
		const result = await call<ReviewerVenueOut>(createRequestApi(), 'mergeVenue', {
			bearer: secret,
			id: event.params.id,
			body: { into, version: version(data) }
		});
		if (!result.ok) return fail(failStatus(result), { form: 'merge', error: result.reason });
		redirect(303, `/review/dropzones/${into}?merged=1`);
	}
};
