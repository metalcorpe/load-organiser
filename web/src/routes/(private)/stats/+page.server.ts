import { redirect } from '@sveltejs/kit';
import type { StatsOut } from '#lib/contracts/index.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { call, isRecord } from '#lib/server/maintenance.ts';
import { readSessionSecret } from '#lib/server/session.ts';
import { requireViewer } from '#lib/server/viewer.ts';
import { yearParam } from '#lib/stats.ts';
import type { PageServerLoad } from './$types';

const isStats = (body: unknown) =>
	isRecord(body) &&
	isRecord((body as StatsOut).total) &&
	Array.isArray((body as StatsOut).per_year) &&
	Array.isArray((body as StatsOut).by_type);

/** Statistics from the owner's own entries: one API call, whatever the logbook's size. */
export const load: PageServerLoad = async (event) => {
	requireViewer(event.locals.viewer, event.url);
	const secret = readSessionSecret(event.cookies);
	if (!secret) redirect(303, '/sign-in');
	const year = yearParam(event.url.searchParams.get('year'));
	const stats = await call<StatsOut>(
		createRequestApi(),
		'getStats',
		{ bearer: secret, query: { year: year || undefined } },
		isStats
	);
	return {
		year,
		stats: stats.ok
			? { ok: true as const, ...stats.value }
			: { ok: false as const, reason: stats.reason }
	};
};
