import { redirect } from '@sveltejs/kit';
import type { HistoryOut } from '#lib/contracts/index.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { isHistory } from '#lib/server/history.ts';
import { call } from '#lib/server/maintenance.ts';
import { readSessionSecret } from '#lib/server/session.ts';
import { requireViewer } from '#lib/server/viewer.ts';
import type { PageServerLoad } from './$types';

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
	return {
		// UTC day for the first render; the currency status then uses the jumper's own day.
		today: new Date().toISOString().slice(0, 10),
		history: history.ok
			? { ok: true as const, ...history.value }
			: { ok: false as const, reason: history.reason }
	};
};
