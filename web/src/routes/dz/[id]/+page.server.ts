import { error, redirect } from '@sveltejs/kit';
import type { PostPageOut } from '#lib/contracts/index.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { isUuid } from '#lib/server/api/transport.ts';
import { getVenue } from '#lib/server/directory.ts';
import { call } from '#lib/server/maintenance.ts';
import { searchOpportunities } from '#lib/server/opportunities.ts';
import { readSessionSecret } from '#lib/server/session.ts';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params, locals, cookies, url }) => {
	if (!isUuid(params.id)) error(404, 'Not found');
	const api = createRequestApi();
	const outcome = await getVenue(api, params.id);
	if (!outcome.ok) {
		if (outcome.reason === 'not_found') error(404, 'Not found');
		error(503, 'The directory is unavailable right now. Try again later.');
	}
	// A reviewed merge: the old address permanently points at the surviving listing.
	if (outcome.value.replacedId) redirect(301, `/dz/${outcome.value.venue.id}`);
	const venue = outcome.value.venue;
	// Signed-in readers send their session so audience, follows and blocks apply;
	// guests see public posts only.
	const bearer = locals.viewer ? (readSessionSecret(cookies) ?? undefined) : undefined;
	const before = url.searchParams.get('before') ?? '';
	const [listings, posts] = await Promise.all([
		searchOpportunities(api, { venue: venue.id, limit: 20 }),
		call<PostPageOut>(api, 'listVenuePosts', {
			bearer,
			id: venue.id,
			query: { before: isUuid(before) ? before : undefined }
		})
	]);
	return {
		venue,
		listings: listings.ok
			? {
					ok: true as const,
					items: listings.value.items,
					more: Boolean(listings.value.nextCursor)
				}
			: { ok: false as const, reason: listings.reason },
		posts: posts.ok ? posts.value : null,
		olderPosts: isUuid(before)
	};
};
