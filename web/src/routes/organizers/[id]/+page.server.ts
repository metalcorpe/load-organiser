import { error, redirect } from '@sveltejs/kit';
import { createRequestApi } from '#lib/server/api/client.ts';
import { isUuid } from '#lib/server/api/transport.ts';
import { getProvider, searchOpportunities } from '#lib/server/opportunities.ts';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params }) => {
	if (!isUuid(params.id)) error(404, 'Not found');
	const api = createRequestApi();
	const outcome = await getProvider(api, params.id);
	if (!outcome.ok) {
		if (outcome.reason === 'not_found') error(404, 'Not found');
		error(503, 'Listings are unavailable right now. Try again later.');
	}
	if (outcome.value.replacedId) redirect(301, `/organizers/${outcome.value.value.id}`);
	const provider = outcome.value.value;
	const listings = await searchOpportunities(api, {
		provider: provider.id,
		limit: 20
	});
	return {
		provider,
		listings: listings.ok
			? {
					ok: true as const,
					items: listings.value.items,
					more: Boolean(listings.value.nextCursor)
				}
			: { ok: false as const, reason: listings.reason }
	};
};
