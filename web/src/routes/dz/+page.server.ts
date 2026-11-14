import { isCountryCode } from '#lib/countries.ts';
import { dzView } from '#lib/dz-map.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { searchVenues } from '#lib/server/directory.ts';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ url }) => {
	const q = (url.searchParams.get('q') ?? '').trim().slice(0, 80);
	const rawCountry = (url.searchParams.get('country') ?? '').toUpperCase();
	const country = isCountryCode(rawCountry) ? rawCountry : '';
	const view = dzView(url.searchParams.get('view'));

	if (view === 'map') {
		// Nothing to load here: the map fetches its points from /dz/points, and only after the
		// visitor chooses "Show map". Without JavaScript the Map view points to the list.
		return { q, country, view, paged: false, result: null };
	}

	const cursor = (url.searchParams.get('cursor') ?? '').slice(0, 512);
	const outcome = await searchVenues(createRequestApi(), {
		q: q || undefined,
		country: country || undefined,
		cursor: cursor || undefined
	});
	return {
		q,
		country,
		view,
		paged: Boolean(cursor),
		result: outcome.ok
			? { ok: true as const, items: outcome.value.items, nextCursor: outcome.value.nextCursor }
			: { ok: false as const, reason: outcome.reason }
	};
};
