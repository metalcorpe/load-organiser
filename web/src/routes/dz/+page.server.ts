import { isCountryCode } from '#lib/countries.ts';
import { dzView } from '#lib/dz-map.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { listVenuePoints, searchVenues } from '#lib/server/directory.ts';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ url }) => {
	const q = (url.searchParams.get('q') ?? '').trim().slice(0, 80);
	const rawCountry = (url.searchParams.get('country') ?? '').toUpperCase();
	const country = isCountryCode(rawCountry) ? rawCountry : '';
	const view = dzView(url.searchParams.get('view'));

	if (view === 'map') {
		// The same search as the list, as map points. Loading them sends nothing to a third
		// party: tiles are requested by the browser only after the visitor chooses the map.
		const outcome = await listVenuePoints(createRequestApi(), {
			q: q || undefined,
			country: country || undefined
		});
		return {
			q,
			country,
			view,
			paged: false,
			result: null,
			map: outcome.ok
				? { ok: true as const, points: outcome.value.points, truncated: outcome.value.truncated }
				: { ok: false as const, reason: outcome.reason }
		};
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
			: { ok: false as const, reason: outcome.reason },
		map: null
	};
};
