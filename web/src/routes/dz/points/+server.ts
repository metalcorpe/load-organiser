import { json } from '@sveltejs/kit';
import { isCountryCode } from '#lib/countries.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { listVenuePoints } from '#lib/server/directory.ts';
import type { RequestHandler } from './$types';

/**
 * Map points for /dz?view=map, fetched by the page only after the visitor presses "Show map",
 * so rendering the Map view (or the list) never loads them. Same filters as the list. Like
 * every dynamic response it is `no-store` (architecture A3: no shared caching yet).
 */
export const GET: RequestHandler = async ({ url }) => {
	const q = (url.searchParams.get('q') ?? '').trim().slice(0, 80);
	const rawCountry = (url.searchParams.get('country') ?? '').toUpperCase();
	const country = isCountryCode(rawCountry) ? rawCountry : '';
	const outcome = await listVenuePoints(createRequestApi(), {
		q: q || undefined,
		country: country || undefined
	});
	if (!outcome.ok) return json({ ok: false, reason: outcome.reason }, { status: 502 });
	return json({ ok: true, points: outcome.value.points, truncated: outcome.value.truncated });
};
