import { createRequestApi } from '#lib/server/api/client.ts';
import { searchOpportunities } from '#lib/server/opportunities.ts';
import { parseFilters } from '#lib/listing-filters.ts';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ url }) => {
	const filters = parseFilters(url.searchParams);
	const cursor = (url.searchParams.get('cursor') ?? '').slice(0, 512);
	const outcome = await searchOpportunities(createRequestApi(), {
		...Object.fromEntries(Object.entries(filters).filter(([, v]) => v)),
		cursor: cursor || undefined,
		limit: 20
	});
	return {
		filters,
		paged: Boolean(cursor),
		result: outcome.ok
			? {
					ok: true as const,
					items: outcome.value.items,
					nextCursor: outcome.value.nextCursor
				}
			: { ok: false as const, reason: outcome.reason }
	};
};
