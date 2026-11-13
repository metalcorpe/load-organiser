import { error, fail, redirect } from '@sveltejs/kit';
import { eventHref, resultsPath } from '#lib/listing-filters.ts';
import { listingStatus } from '#lib/listings.ts';
import { signInPath } from '#lib/safe-return.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { isUuid } from '#lib/server/api/transport.ts';
import {
	getOpportunity,
	getSaved,
	saveOpportunity,
	unsaveOpportunity
} from '#lib/server/opportunities.ts';
import { readSessionSecret } from '#lib/server/session.ts';
import type { Actions, PageServerLoad, RequestEvent } from './$types';

export const load: PageServerLoad = async ({ params, url, locals, cookies }) => {
	if (!isUuid(params.id)) error(404, 'Not found');
	const api = createRequestApi();
	const outcome = await getOpportunity(api, params.id);
	if (!outcome.ok) {
		if (outcome.reason === 'not_found') error(404, 'Not found');
		error(503, 'Listings are unavailable right now. Try again later.');
	}
	// A consolidated duplicate: the old address permanently points at the kept listing.
	if (outcome.value.replacedId) redirect(301, `/events/${outcome.value.value.id}${url.search}`);

	const item = outcome.value.value;
	const secret = locals.viewer ? readSessionSecret(cookies) : undefined;
	let saved: { known: boolean; savedAt: string | null } = {
		known: false,
		savedAt: null
	};
	if (secret) {
		const state = await getSaved(api, secret, item.id);
		saved = state.ok ? { known: true, savedAt: state.value?.saved_at ?? null } : saved;
	}
	return {
		item,
		saved,
		// The board search this was opened from ("Back to results"); null for a direct link.
		results: resultsPath(url.searchParams.get('results')),
		// Set after signing in from "Sign in to save": offer the save, do not perform it.
		saveIntent: url.searchParams.get('save') === '1'
	};
};

function secretFor(event: Pick<RequestEvent, 'locals' | 'url' | 'cookies' | 'params'>): string {
	const back = new URL(
		eventHref(event.params.id, {
			save: true,
			results: event.url.searchParams.get('results')
		}),
		event.url
	);
	if (!event.locals.viewer) redirect(303, signInPath(back));
	const secret = readSessionSecret(event.cookies);
	if (!secret) redirect(303, signInPath(back));
	return secret;
}

export const actions: Actions = {
	save: async (event) => {
		if (!isUuid(event.params.id)) return fail(404, { error: 'not_found' });
		const secret = secretFor(event);
		const outcome = await saveOpportunity(createRequestApi(), secret, event.params.id);
		if (!outcome.ok) return fail(listingStatus(outcome.reason), { error: outcome.reason });
		return { saved: true };
	},

	unsave: async (event) => {
		if (!isUuid(event.params.id)) return fail(404, { error: 'not_found' });
		const secret = secretFor(event);
		const outcome = await unsaveOpportunity(createRequestApi(), secret, event.params.id);
		if (!outcome.ok) return fail(listingStatus(outcome.reason), { error: outcome.reason });
		return { removed: true };
	}
};
