import { redirect } from '@sveltejs/kit';
import type { HistoryOut } from '#lib/contracts/index.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { isHistory } from '#lib/server/history.ts';
import { call } from '#lib/server/maintenance.ts';
import { readSessionSecret } from '#lib/server/session.ts';
import { requireViewer } from '#lib/server/viewer.ts';
import type { PageServerLoad } from './$types';

/** The hub's one summary line comes from the history totals; without them the page still works. */
export const load: PageServerLoad = async (event) => {
	requireViewer(event.locals.viewer, event.url);
	const secret = readSessionSecret(event.cookies);
	if (!secret) redirect(303, '/sign-in');
	const history = await call<HistoryOut>(
		createRequestApi(),
		'getHistory',
		{ bearer: secret },
		isHistory
	);
	if (!history.ok) return { summary: null };
	const { totals, last_jump_on } = history.value;
	return {
		summary: {
			recorded: totals.recorded,
			lifetime: totals.inconsistent ? null : totals.lifetime,
			prior: totals.prior_jumps,
			since: totals.recorded_since,
			lastJumpOn: last_jump_on
		}
	};
};
