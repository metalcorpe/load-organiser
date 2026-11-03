import { error, redirect } from '@sveltejs/kit';
import { createRequestApi } from '#lib/server/api/client.ts';
import { isUuid } from '#lib/server/api/transport.ts';
import { getVenue } from '#lib/server/directory.ts';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ params }) => {
	if (!isUuid(params.id)) error(404, 'Not found');
	const outcome = await getVenue(createRequestApi(), params.id);
	if (!outcome.ok) {
		if (outcome.reason === 'not_found') error(404, 'Not found');
		error(503, 'The directory is unavailable right now. Try again later.');
	}
	// A reviewed merge: the old address permanently points at the surviving listing.
	if (outcome.value.replacedId) redirect(301, `/dz/${outcome.value.venue.id}`);
	return { venue: outcome.value.venue };
};
