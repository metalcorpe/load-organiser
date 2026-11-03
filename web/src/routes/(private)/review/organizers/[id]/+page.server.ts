import { error, fail, redirect } from '@sveltejs/kit';
import type { ReviewerProviderOut, ReviewProviderPageOut } from '#lib/contracts/index.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { isUuid } from '#lib/server/api/transport.ts';
import { field } from '#lib/server/forms.ts';
import { call, failStatus, isPage } from '#lib/server/maintenance.ts';
import { requireReviewer } from '#lib/server/reviewer.ts';
import { echo, text, version } from '#lib/server/review-forms.ts';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	const secret = requireReviewer(event);
	const id = event.params.id;
	if (id !== 'new' && !isUuid(id)) error(404, 'Not found');
	const api = createRequestApi();
	const [provider, others] = await Promise.all([
		id === 'new'
			? Promise.resolve(null)
			: call<ReviewerProviderOut>(api, 'reviewProvider', { bearer: secret, id }),
		call<ReviewProviderPageOut>(
			api,
			'listReviewProviders',
			{ bearer: secret, query: { status: 'published', limit: '50' } },
			isPage
		)
	]);
	if (provider && !provider.ok) {
		if (provider.reason === 'not_found') error(404, 'Not found');
		error(503, 'The maintenance service is unavailable right now.');
	}
	return {
		provider: provider ? provider.value : null,
		mergeTargets: others.ok ? others.value.items.filter((p) => p.id !== id) : []
	};
};

function fields(data: FormData) {
	return {
		name: text(data, 'name', 200),
		kind: text(data, 'kind', 16),
		country: text(data, 'country', 2),
		website_url: text(data, 'website_url'),
		source_url: text(data, 'source_url'),
		source_note: text(data, 'source_note', 400),
		checked_on: text(data, 'checked_on', 10)
	};
}

export const actions: Actions = {
	save: async (event) => {
		const secret = requireReviewer(event);
		const data = await event.request.formData();
		const body = fields(data);
		if (!body.name || !body.kind)
			return fail(400, { form: 'save', error: 'missing', values: echo(data) });
		const api = createRequestApi();
		if (event.params.id === 'new') {
			const created = await call<ReviewerProviderOut>(api, 'createProvider', {
				bearer: secret,
				body: { ...body, publish: field(data, 'publish', { max: 4 }) === 'on' }
			});
			if (!created.ok) {
				return fail(failStatus(created), {
					form: 'save',
					error: created.reason,
					values: echo(data)
				});
			}
			redirect(303, `/review/organizers/${created.value.id}?saved=1`);
		}
		const updated = await call<ReviewerProviderOut>(api, 'updateProvider', {
			bearer: secret,
			id: event.params.id,
			body: { ...body, version: version(data) }
		});
		if (!updated.ok) {
			return fail(failStatus(updated), { form: 'save', error: updated.reason, values: echo(data) });
		}
		return { form: 'save', done: true };
	},

	status: async (event) => {
		const secret = requireReviewer(event);
		const data = await event.request.formData();
		const result = await call<ReviewerProviderOut>(createRequestApi(), 'setProviderStatus', {
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
		const result = await call<ReviewerProviderOut>(createRequestApi(), 'mergeProvider', {
			bearer: secret,
			id: event.params.id,
			body: { into, version: version(data) }
		});
		if (!result.ok) return fail(failStatus(result), { form: 'merge', error: result.reason });
		redirect(303, `/review/organizers/${into}?merged=1`);
	}
};
