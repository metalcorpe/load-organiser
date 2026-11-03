import { error, fail, redirect } from '@sveltejs/kit';
import type {
	ReviewerOpportunityOut,
	ReviewProviderPageOut,
	ReviewVenuePageOut
} from '#lib/contracts/index.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { isUuid } from '#lib/server/api/transport.ts';
import { field } from '#lib/server/forms.ts';
import { call, failStatus, isPage } from '#lib/server/maintenance.ts';
import { requireReviewer } from '#lib/server/reviewer.ts';
import { echo, list, text, version } from '#lib/server/review-forms.ts';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	const secret = requireReviewer(event);
	const id = event.params.id;
	if (id !== 'new' && !isUuid(id)) error(404, 'Not found');
	const api = createRequestApi();
	const params = event.url.searchParams;
	const orgQ = (params.get('org_q') ?? '').trim().slice(0, 80);
	const dzQ = (params.get('dz_q') ?? '').trim().slice(0, 80);
	const [listing, providers, venues] = await Promise.all([
		id === 'new'
			? Promise.resolve(null)
			: call<ReviewerOpportunityOut>(api, 'reviewOpportunity', { bearer: secret, id }),
		call<ReviewProviderPageOut>(
			api,
			'listReviewProviders',
			{ bearer: secret, query: { q: orgQ || undefined, limit: '50' } },
			isPage
		),
		call<ReviewVenuePageOut>(
			api,
			'listReviewVenues',
			{ bearer: secret, query: { q: dzQ || undefined, status: 'listed', limit: '50' } },
			isPage
		)
	]);
	if (listing && !listing.ok) {
		if (listing.reason === 'not_found') error(404, 'Not found');
		error(503, 'The maintenance service is unavailable right now.');
	}
	let zones: string[] = [];
	try {
		zones = Intl.supportedValuesOf('timeZone').filter((z) => /^(Europe|Atlantic)\//.test(z));
	} catch {
		zones = [];
	}
	return {
		listing: listing ? listing.value : null,
		orgQ,
		dzQ,
		providers: providers.ok ? providers.value.items.filter((p) => p.status !== 'merged') : [],
		venues: venues.ok ? venues.value.items : [],
		zones
	};
};

function body(data: FormData) {
	const languages = (text(data, 'languages', 100) ?? '')
		.split(/[\s,]+/)
		.filter(Boolean)
		.slice(0, 8);
	const price = text(data, 'price_amount', 16);
	return {
		title: text(data, 'title', 400),
		category: text(data, 'category', 16),
		provider_id: text(data, 'provider_id', 64),
		venue_id: text(data, 'venue_id', 64),
		country: text(data, 'country', 2),
		location_note: text(data, 'location_note', 400),
		starts_on: text(data, 'starts_on', 10),
		ends_on: text(data, 'ends_on', 10),
		time_zone: text(data, 'time_zone', 64),
		disciplines: list(data, 'disciplines'),
		audience: list(data, 'audience'),
		languages,
		summary: text(data, 'summary', 4000),
		prerequisites: text(data, 'prerequisites', 4000),
		price_amount: price,
		price_currency: text(data, 'price_currency', 3)?.toUpperCase() ?? null,
		price_basis: text(data, 'price_basis', 16),
		price_note: text(data, 'price_note', 400),
		registration_url: text(data, 'registration_url'),
		source_url: text(data, 'source_url'),
		source_note: text(data, 'source_note', 400),
		checked_on: text(data, 'checked_on', 10)
	};
}

export const actions: Actions = {
	save: async (event) => {
		const secret = requireReviewer(event);
		const data = await event.request.formData();
		const values = body(data);
		if (!values.title || !values.category || !isUuid(values.provider_id) || !values.country) {
			return fail(400, { form: 'save', error: 'missing', values: echo(data) });
		}
		const api = createRequestApi();
		if (event.params.id === 'new') {
			const created = await call<ReviewerOpportunityOut>(api, 'createOpportunity', {
				bearer: secret,
				body: values
			});
			if (!created.ok) {
				return fail(failStatus(created), {
					form: 'save',
					error: created.reason,
					values: echo(data)
				});
			}
			redirect(303, `/review/listings/${created.value.id}?saved=1`);
		}
		const updated = await call<ReviewerOpportunityOut>(api, 'updateOpportunity', {
			bearer: secret,
			id: event.params.id,
			body: { ...values, version: version(data) }
		});
		if (!updated.ok) {
			return fail(failStatus(updated), { form: 'save', error: updated.reason, values: echo(data) });
		}
		return { form: 'save', done: true };
	},

	status: async (event) => {
		const secret = requireReviewer(event);
		const data = await event.request.formData();
		const result = await call<ReviewerOpportunityOut>(createRequestApi(), 'setOpportunityStatus', {
			bearer: secret,
			id: event.params.id,
			body: { status: field(data, 'status', { max: 16 }), version: version(data) }
		});
		if (!result.ok) return fail(failStatus(result), { form: 'status', error: result.reason });
		return { form: 'status', done: true };
	},

	duplicate: async (event) => {
		const secret = requireReviewer(event);
		const data = await event.request.formData();
		const of = field(data, 'of', { max: 64, trim: true });
		if (!isUuid(of)) return fail(400, { form: 'duplicate', error: 'missing' });
		const result = await call<ReviewerOpportunityOut>(
			createRequestApi(),
			'markOpportunityDuplicate',
			{ bearer: secret, id: event.params.id, body: { of, version: version(data) } }
		);
		if (!result.ok) return fail(failStatus(result), { form: 'duplicate', error: result.reason });
		redirect(303, `/review/listings/${of}?absorbed=1`);
	}
};
