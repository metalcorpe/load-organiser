import { fail } from '@sveltejs/kit';
import type { ReviewSubmissionOut, ReviewSubmissionPageOut } from '#lib/contracts/index.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { isUuid } from '#lib/server/api/transport.ts';
import { field } from '#lib/server/forms.ts';
import { call, failStatus, isPage } from '#lib/server/maintenance.ts';
import { requireReviewer } from '#lib/server/reviewer.ts';
import type { Actions, PageServerLoad } from './$types';

const STATUSES = ['open', 'accepted', 'declined'] as const;

export const load: PageServerLoad = async (event) => {
	const secret = requireReviewer(event);
	const raw = event.url.searchParams.get('status') ?? 'open';
	const status = (STATUSES as readonly string[]).includes(raw) ? raw : 'open';
	const cursor = (event.url.searchParams.get('cursor') ?? '').slice(0, 512);
	const page = await call<ReviewSubmissionPageOut>(
		createRequestApi(),
		'listReviewSubmissions',
		{ bearer: secret, query: { status, cursor: cursor || undefined, limit: '50' } },
		isPage
	);
	return {
		status,
		page: page.ok
			? { ok: true as const, items: page.value.items, nextCursor: page.value.next_cursor }
			: { ok: false as const, reason: page.reason }
	};
};

export const actions: Actions = {
	resolve: async (event) => {
		const secret = requireReviewer(event);
		const data = await event.request.formData();
		const id = field(data, 'id', { max: 64 });
		const outcome = field(data, 'outcome', { max: 16 });
		const note = field(data, 'note', { max: 1000, trim: true });
		const version = Number(field(data, 'version', { max: 12 }));
		if (!isUuid(id) || !['accepted', 'declined'].includes(outcome) || !Number.isInteger(version)) {
			return fail(400, { id, error: 'invalid_input' });
		}
		const result = await call<ReviewSubmissionOut>(createRequestApi(), 'resolveSubmission', {
			bearer: secret,
			id,
			body: { status: outcome, note: note || null, version }
		});
		if (!result.ok) return fail(failStatus(result), { id, error: result.reason });
		return { id, done: outcome };
	}
};
