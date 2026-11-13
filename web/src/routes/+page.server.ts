import { createRequestApi } from '#lib/server/api/client.ts';
import { listCoverageCountries, searchOpportunities } from '#lib/server/opportunities.ts';
import { datesOutOfOrder, parseFilters } from '#lib/listing-filters.ts';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ url }) => {
	const filters = parseFilters(url.searchParams);
	const cursor = (url.searchParams.get('cursor') ?? '').slice(0, 512);
	const api = createRequestApi();
	// A "to" before "from" is the visitor's mistake, not the service's: it is answered here,
	// without a search, and the page marks the date to correct. Every filter is kept as sent.
	const invalidDates = datesOutOfOrder(filters);
	const [outcome, coverage] = await Promise.all([
		invalidDates
			? null
			: searchOpportunities(api, {
					...Object.fromEntries(Object.entries(filters).filter(([, v]) => v)),
					cursor: cursor || undefined,
					limit: 20
				}),
		listCoverageCountries(api)
	]);
	// The API applies the same rule; its refusal is the same validation error.
	const invalid = invalidDates || (outcome && !outcome.ok && outcome.reason === 'dates_out_of_order');
	return {
		filters,
		// null: coverage unknown, so the filter offers every country rather than none.
		countries: coverage.ok ? coverage.value : null,
		paged: Boolean(cursor),
		cursor,
		result: invalid
			? { ok: false as const, kind: 'invalid' as const, reason: 'dates_out_of_order' }
			: outcome?.ok
				? {
						ok: true as const,
						items: outcome.value.items,
						nextCursor: outcome.value.nextCursor
					}
				: {
						ok: false as const,
						kind: 'failed' as const,
						reason: (outcome && !outcome.ok && outcome.reason) || 'unavailable'
					}
	};
};
