import { isCountryCode } from '#lib/countries.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { searchVenues } from '#lib/server/directory.ts';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ url }) => {
	const q = (url.searchParams.get('q') ?? '').trim().slice(0, 80);
	const rawCountry = (url.searchParams.get('country') ?? '').toUpperCase();
	const country = isCountryCode(rawCountry) ? rawCountry : '';
	const cursor = (url.searchParams.get('cursor') ?? '').slice(0, 512);

	const outcome = await searchVenues(createRequestApi(), {
		q: q || undefined,
		country: country || undefined,
		cursor: cursor || undefined
	});
	return {
		q,
		country,
		paged: Boolean(cursor),
		result: outcome.ok
			? { ok: true as const, items: outcome.value.items, nextCursor: outcome.value.nextCursor }
			: { ok: false as const, reason: outcome.reason }
	};
};
