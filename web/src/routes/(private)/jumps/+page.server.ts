import { redirect } from '@sveltejs/kit';
import type { HistoryOut, JumpNumberingOut, JumpPageOut } from '#lib/contracts/index.ts';
import { hasJumpFilters, jumpsQuery, parseJumpFilters } from '#lib/jump-filters.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { numberingNotes } from '#lib/jumps.ts';
import { isHistory } from '#lib/server/history.ts';
import { call, isPage } from '#lib/server/maintenance.ts';
import { readSessionSecret } from '#lib/server/session.ts';
import { requireViewer } from '#lib/server/viewer.ts';
import type { PageServerLoad } from './$types';

/**
 * The Logbook home (design E): totals and one-tap logging on the first page, then the list.
 * Search and filters are a GET form: they live in the URL and the pages keep them.
 */
export const load: PageServerLoad = async (event) => {
	requireViewer(event.locals.viewer, event.url);
	const secret = readSessionSecret(event.cookies);
	if (!secret) redirect(303, '/sign-in');
	const cursor = (event.url.searchParams.get('cursor') ?? '').slice(0, 200) || undefined;
	const filters = parseJumpFilters(event.url.searchParams);
	const filtered = hasJumpFilters(filters);
	const api = createRequestApi();
	const [page, history, numbering] = await Promise.all([
		call<JumpPageOut>(
			api,
			'listJumps',
			{ bearer: secret, query: { cursor, limit: '20', ...jumpsQuery(filters) } },
			(body) => isPage(body) && typeof (body as JumpPageOut).recorded_total === 'number'
		),
		// Also the place choices of the filter form: every place with a recorded jump.
		call<HistoryOut>(api, 'getHistory', { bearer: secret }, isHistory),
		// Gaps and repeats in the jumper's own numbering: first, unfiltered page only.
		cursor || filtered
			? null
			: call<JumpNumberingOut>(api, 'getJumpNumbering', { bearer: secret })
	]);

	// Recent places come from the newest jumps on this page: distinct, newest first, open ones only.
	const recent: { kind: 'venue' | 'place'; id: string; name: string }[] = [];
	// The newest jump, when the first recent place is its place: the main button then
	// continues from it (gear, type, altitudes, next number), on the jumper's today.
	let continueFrom: string | null = null;
	if (page.ok && !cursor && !filtered) {
		const seen = new Set<string>();
		for (const jump of page.value.items) {
			const loc = jump.location;
			const key = `${loc.kind}:${loc.id}`;
			if (!loc.name || loc.closed || seen.has(key)) continue;
			seen.add(key);
			recent.push({ kind: loc.kind, id: loc.id, name: loc.name });
			if (recent.length === 3) break;
		}
		const newest = page.value.items[0];
		if (newest && recent[0] && newest.location.kind === recent[0].kind && newest.location.id === recent[0].id) {
			continueFrom = newest.id;
		}
	}

	const places = history.ok
		? history.value.by_location
				.map(({ location: loc }) => ({
					value: `${loc.kind}:${loc.id}`,
					label: `${loc.name ?? 'Dropzone no longer listed'}${loc.kind === 'place' ? ' (private place)' : ''}`
				}))
				.sort((a, b) => a.label.localeCompare(b.label, 'en-GB'))
		: [];
	const totals = history.ok ? history.value.totals : null;
	return {
		page: page.ok
			? { ok: true as const, ...page.value }
			: { ok: false as const, reason: page.reason },
		older: Boolean(cursor),
		filters,
		filtered,
		places,
		recent,
		continueFrom,
		numbering: numbering?.ok ? numberingNotes(numbering.value) : { notes: [], more: null },
		summary:
			history.ok && totals
				? {
						lifetime: totals.inconsistent ? null : totals.lifetime,
						lastJumpOn: history.value.last_jump_on
					}
				: null
	};
};
