import { redirect } from '@sveltejs/kit';
import type { JumpOut, PrintPageOut } from '#lib/contracts/index.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { call, isPage, isRecord } from '#lib/server/maintenance.ts';
import { readSessionSecret } from '#lib/server/session.ts';
import { requireViewer } from '#lib/server/viewer.ts';
import { MAX_PRINT_JUMPS, dateParam } from '#lib/print.ts';
import type { PageServerLoad } from './$types';

// 200 a request: the whole logbook (2,000) in at most 10 upstream calls, well inside
// the Workers subrequest limit.
const PER_REQUEST = 200;
const MAX_REQUESTS = MAX_PRINT_JUMPS / PER_REQUEST;

const isPrintPage = (body: unknown) =>
	isPage(body) && isRecord((body as PrintPageOut).brought_forward);

/** The owner's own jumps in a date range, oldest first, for printing. Read-only. */
export const load: PageServerLoad = async (event) => {
	const viewer = requireViewer(event.locals.viewer, event.url);
	const secret = readSessionSecret(event.cookies);
	if (!secret) redirect(303, '/sign-in');
	const params = event.url.searchParams;
	const from = dateParam(params.get('from'));
	const until = dateParam(params.get('until'));
	// Notes are private: printed only when asked for.
	const notes = params.get('notes') === 'yes';
	const options = { from, until, notes, owner: viewer.displayName ?? null };
	if (from && until && from > until) {
		return { options, result: { ok: false as const, reason: 'date_range_invalid' } };
	}

	const api = createRequestApi();
	const jumps: JumpOut[] = [];
	let before = { jumps: 0, freefall: 0 };
	let cursor: string | undefined;
	for (let request = 0; request < MAX_REQUESTS; request++) {
		const page = await call<PrintPageOut>(
			api,
			'listJumpsInOrder',
			{
				bearer: secret,
				query: {
					from_on: from || undefined,
					until_on: until || undefined,
					cursor,
					limit: String(PER_REQUEST)
				}
			},
			isPrintPage
		);
		if (!page.ok) return { options, result: { ok: false as const, reason: page.reason } };
		if (request === 0) {
			before = {
				jumps: page.value.brought_forward.jumps,
				freefall: page.value.brought_forward.freefall_seconds
			};
		}
		jumps.push(...page.value.items);
		cursor = page.value.next_cursor ?? undefined;
		if (!cursor) break;
	}
	return {
		options,
		result: { ok: true as const, jumps, before, incomplete: Boolean(cursor) }
	};
};
