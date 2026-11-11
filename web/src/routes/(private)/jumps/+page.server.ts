import { redirect } from '@sveltejs/kit';
import type { HistoryOut, JumpPageOut } from '#lib/contracts/index.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { isHistory } from '#lib/server/history.ts';
import { call, isPage } from '#lib/server/maintenance.ts';
import { readSessionSecret } from '#lib/server/session.ts';
import { requireViewer } from '#lib/server/viewer.ts';
import type { PageServerLoad } from './$types';

/** The Logbook home (design E): totals and one-tap logging on the first page, then the list. */
export const load: PageServerLoad = async (event) => {
	requireViewer(event.locals.viewer, event.url);
	const secret = readSessionSecret(event.cookies);
	if (!secret) redirect(303, '/sign-in');
	const cursor = (event.url.searchParams.get('cursor') ?? '').slice(0, 200) || undefined;
	const api = createRequestApi();
	const [page, history] = await Promise.all([
		call<JumpPageOut>(
			api,
			'listJumps',
			{ bearer: secret, query: { cursor, limit: '20' } },
			(body) => isPage(body) && typeof (body as JumpPageOut).recorded_total === 'number'
		),
		cursor ? null : call<HistoryOut>(api, 'getHistory', { bearer: secret }, isHistory)
	]);

	// Recent places come from the newest jumps on this page: distinct, newest first, open ones only.
	const recent: { kind: 'venue' | 'place'; id: string; name: string }[] = [];
	if (page.ok && !cursor) {
		const seen = new Set<string>();
		for (const jump of page.value.items) {
			const loc = jump.location;
			const key = `${loc.kind}:${loc.id}`;
			if (!loc.name || loc.closed || seen.has(key)) continue;
			seen.add(key);
			recent.push({ kind: loc.kind, id: loc.id, name: loc.name });
			if (recent.length === 3) break;
		}
	}

	const totals = history?.ok ? history.value.totals : null;
	return {
		page: page.ok
			? { ok: true as const, ...page.value }
			: { ok: false as const, reason: page.reason },
		older: Boolean(cursor),
		recent,
		summary:
			history?.ok && totals
				? {
						lifetime: totals.inconsistent ? null : totals.lifetime,
						lastJumpOn: history.value.last_jump_on
					}
				: null
	};
};
