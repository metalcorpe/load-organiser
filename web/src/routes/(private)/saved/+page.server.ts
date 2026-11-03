import { fail, redirect } from '@sveltejs/kit';
import { listingStatus } from '#lib/listings.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { isUuid } from '#lib/server/api/transport.ts';
import { field } from '#lib/server/forms.ts';
import { listSaved, unsaveOpportunity } from '#lib/server/opportunities.ts';
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
	const secret = secretFor(event);
	const saved = await listSaved(createRequestApi(), secret);
	return {
		saved: saved.ok
			? { ok: true as const, items: saved.value }
			: { ok: false as const, reason: saved.reason }
	};
};

export const actions: Actions = {
	remove: async (event) => {
		const secret = secretFor(event);
		const id = field(await event.request.formData(), 'id', { max: 64 });
		if (!isUuid(id)) return fail(404, { error: 'not_found' });
		const outcome = await unsaveOpportunity(createRequestApi(), secret, id);
		if (!outcome.ok) return fail(listingStatus(outcome.reason), { error: outcome.reason, id });
		return { removed: id };
	}
};
