import type {
	ReviewOpportunityPageOut,
	ReviewProviderPageOut,
	ReviewSubmissionPageOut,
	ReviewVenuePageOut
} from '#lib/contracts/index.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { call, isPage, type Result } from '#lib/server/maintenance.ts';
import { requireReviewer } from '#lib/server/reviewer.ts';
import type { PageServerLoad } from './$types';

function section<T extends { items: unknown[]; next_cursor: string | null }>(result: Result<T>) {
	return result.ok
		? {
				ok: true as const,
				items: result.value.items as T['items'],
				more: Boolean(result.value.next_cursor)
			}
		: { ok: false as const, reason: result.reason };
}

export const load: PageServerLoad = async (event) => {
	const secret = requireReviewer(event);
	const api = createRequestApi();
	const q = (event.url.searchParams.get('q') ?? '').trim().slice(0, 80);
	const query = (extra: Record<string, string>) => ({
		bearer: secret,
		query: { limit: '50', q: q || undefined, ...extra }
	});
	const [dueListings, dueOrganizers, dueDropzones, drafts, inReview, submissions] =
		await Promise.all([
			call<ReviewOpportunityPageOut>(
				api,
				'listReviewOpportunities',
				query({ due: 'true' }),
				isPage
			),
			call<ReviewProviderPageOut>(api, 'listReviewProviders', query({ due: 'true' }), isPage),
			call<ReviewVenuePageOut>(api, 'listReviewVenues', query({ due: 'true' }), isPage),
			call<ReviewOpportunityPageOut>(
				api,
				'listReviewOpportunities',
				query({ status: 'draft' }),
				isPage
			),
			call<ReviewOpportunityPageOut>(
				api,
				'listReviewOpportunities',
				query({ status: 'review' }),
				isPage
			),
			call<ReviewSubmissionPageOut>(
				api,
				'listReviewSubmissions',
				{ bearer: secret, query: { status: 'open', limit: '50' } },
				isPage
			)
		]);
	// With a filter, also list every match regardless of status.
	const [listings, organizers, dropzones] = q
		? await Promise.all([
				call<ReviewOpportunityPageOut>(api, 'listReviewOpportunities', query({}), isPage),
				call<ReviewProviderPageOut>(api, 'listReviewProviders', query({}), isPage),
				call<ReviewVenuePageOut>(api, 'listReviewVenues', query({}), isPage)
			])
		: [null, null, null];
	return {
		q,
		matches:
			listings && organizers && dropzones
				? {
						listings: section(listings),
						organizers: section(organizers),
						dropzones: section(dropzones)
					}
				: null,
		dueListings: section(dueListings),
		dueOrganizers: section(dueOrganizers),
		dueDropzones: section(dueDropzones),
		drafts: section(drafts),
		inReview: section(inReview),
		submissions: section(submissions)
	};
};
