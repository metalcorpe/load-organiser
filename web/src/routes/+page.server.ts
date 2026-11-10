import { createRequestApi } from '#lib/server/api/client.ts';
import { listCoverageCountries, searchOpportunities } from '#lib/server/opportunities.ts';
import { parseFilters } from '#lib/listing-filters.ts';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ url }) => {
	const filters = parseFilters(url.searchParams);
	const cursor = (url.searchParams.get('cursor') ?? '').slice(0, 512);
	const api = createRequestApi();
	const [outcome, coverage] = await Promise.all([
		searchOpportunities(api, {
			...Object.fromEntries(Object.entries(filters).filter(([, v]) => v)),
			cursor: cursor || undefined,
			limit: 20
		}),
		listCoverageCountries(api)
	]);
	return {
		filters,
		// null: coverage unknown, so the filter offers every country rather than none.
		countries: coverage.ok ? coverage.value : null,
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
