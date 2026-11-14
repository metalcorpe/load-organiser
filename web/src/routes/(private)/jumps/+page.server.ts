import { fail, redirect } from '@sveltejs/kit';
import type {
	BatchPreviewOut,
	BatchResultOut,
	ComingUpOut,
	ComponentSummaryOut,
	GearDueOut,
	HistoryOut,
	JumpNumberingOut,
	JumpPageOut,
	LatestBatchStateOut,
	PlaceOut,
	UndoResultOut
} from '#lib/contracts/index.ts';
import { BATCH_MAX } from '#lib/jump-batch.ts';
import {
	hasJumpFilters,
	jumpsQuery,
	parseJumpFilters,
	type JumpFilters
} from '#lib/jump-filters.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { isUuid, type ApiTransport } from '#lib/server/api/transport.ts';
import { field } from '#lib/server/forms.ts';
import {
	batchChanges,
	batchEcho,
	chosenIds,
	chosenVersions
} from '#lib/server/jump-batch.ts';
import { numberingNotes } from '#lib/jumps.ts';
import { isHistory } from '#lib/server/history.ts';
import { call, failStatus, isList, isPage, isRecord } from '#lib/server/maintenance.ts';
import { readSessionSecret } from '#lib/server/session.ts';
import { requireViewer } from '#lib/server/viewer.ts';
import type { Actions, PageServerLoad, RequestEvent } from './$types';

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
	// "Select" mode: ticks on the rows and what to change; 50 a page to choose from.
	const select = event.url.searchParams.get('select') === '1';
	const api = createRequestApi();
	// The home extras (numbering notes, due gear, coming up, the latest change of many
	// jumps) load on the first, unfiltered page only; Select mode adds the gear and
	// private places to choose from. At most six API calls per load, none per item.
	const home = !cursor && !filtered && !select;
	const [page, history, numbering, due, coming, latest, gear, ownPlaces] = await Promise.all([
		call<JumpPageOut>(
			api,
			'listJumps',
			{
				bearer: secret,
				query: { cursor, limit: select ? '50' : '20', ...jumpsQuery(filters) }
			},
			(body) => isPage(body) && typeof (body as JumpPageOut).recorded_total === 'number'
		),
		// Also the place choices of the filter form: every place with a recorded jump.
		call<HistoryOut>(api, 'getHistory', { bearer: secret }, isHistory),
		// Gaps and repeats in the jumper's own numbering: first, unfiltered page only.
		home ? call<JumpNumberingOut>(api, 'getJumpNumbering', { bearer: secret }) : null,
		// Dates coming due on the jumper's gear: one owner-scoped call for all of it.
		home ? call<GearDueOut[]>(api, 'listGearDue', { bearer: secret }, isList) : null,
		// Saved listings and plans of the next 60 days: one owner-scoped call.
		home
			? call<ComingUpOut>(
					api,
					'getComingUp',
					{ bearer: secret },
					(body) => isRecord(body) && Array.isArray(body.items)
				)
			: null,
		// "Undo this change": the latest change of many jumps, while it can be undone.
		home || select
			? call<LatestBatchStateOut>(api, 'getLatestJumpBatch', { bearer: secret })
			: null,
		select ? call<ComponentSummaryOut[]>(api, 'listComponents', { bearer: secret }, isList) : null,
		select ? call<PlaceOut[]>(api, 'listPlaces', { bearer: secret }, isList) : null
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
	// Places a change of many jumps can set: every place with a jump, and every
	// private place (a listed dropzone without a jump yet is chosen on one jump first).
	const placeOptions = [...places];
	if (ownPlaces?.ok) {
		for (const p of ownPlaces.value) {
			const value = `place:${p.id}`;
			if (!placeOptions.some((o) => o.value === value)) {
				placeOptions.push({ value, label: `${p.name} (private place)` });
			}
		}
		placeOptions.sort((a, b) => a.label.localeCompare(b.label, 'en-GB'));
	}
	const batch = latest?.ok ? latest.value.latest : null;
	return {
		select,
		placeOptions,
		gear: gear?.ok
			? gear.value.map((s) => ({ id: s.component.id, label: s.component.label, kind: s.component.kind }))
			: [],
		gearOk: gear ? gear.ok : true,
		latestBatch: batch && batch.can_undo ? batch : null,
		page: page.ok
			? { ok: true as const, ...page.value }
			: { ok: false as const, reason: page.reason },
		older: Boolean(cursor),
		filters,
		filtered,
		places,
		// UTC day for the first render; the currency status then uses the jumper's own day.
		today: new Date().toISOString().slice(0, 10),
		recent,
		continueFrom,
		numbering: numbering?.ok ? numberingNotes(numbering.value) : { notes: [], more: null },
		// Everything not yet "later"; the page keeps what is due within 30 days of the jumper's day.
		due: due?.ok ? due.value.filter((d) => d.status !== 'later') : [],
		coming: coming?.ok ? coming.value.items : [],
		summary:
			history.ok && totals
				? {
						lifetime: totals.inconsistent ? null : totals.lifetime,
						// A declared prior count (B before D): acknowledged on a logbook with no entries.
						priorJumps: totals.prior_jumps,
						priorBefore: totals.before_on,
						lastJumpOn: history.value.last_jump_on,
						currency: history.value.currency,
						progress: history.value.progress ?? null
					}
				: null
	};
};

function secretFor(event: Pick<RequestEvent, 'locals' | 'url' | 'cookies'>): string {
	requireViewer(event.locals.viewer, event.url);
	const secret = readSessionSecret(event.cookies);
	if (!secret) redirect(303, '/sign-in');
	return secret;
}

/**
 * Every jump matching the filters, for "All matching jumps": pages of 50, at most
 * four calls (200 jumps). More than 200 is refused before anything is read further.
 */
async function matchingIds(
	api: ApiTransport,
	secret: string,
	filters: JumpFilters
): Promise<{ ids: string[] } | { error: string; status: number }> {
	const ids: string[] = [];
	let cursor: string | undefined;
	for (let calls = 0; calls < BATCH_MAX / 50; calls++) {
		const page = await call<JumpPageOut>(
			api,
			'listJumps',
			{ bearer: secret, query: { cursor, limit: '50', ...jumpsQuery(filters) } },
			isPage
		);
		if (!page.ok) return { error: page.reason, status: failStatus(page) };
		if (page.value.matched.jumps > BATCH_MAX) return { error: 'too_many_jumps', status: 400 };
		ids.push(...page.value.items.map((j) => j.id));
		if (!page.value.next_cursor) break;
		cursor = page.value.next_cursor;
	}
	return { ids };
}

export const actions: Actions = {
	/** Step 1: what the change would do. Writes nothing. */
	preview: async (event) => {
		const secret = secretFor(event);
		const data = await event.request.formData();
		const api = createRequestApi();
		const all = field(data, 'all', { max: 4 }) === '1';
		let ids = chosenIds(data);
		const refuse = (status: number, error: string) =>
			fail(status, { form: 'batch' as const, error, ids, all, choice: batchEcho(data) });
		if (all) {
			const found = await matchingIds(api, secret, parseJumpFilters(event.url.searchParams));
			if ('error' in found) return refuse(found.status, found.error);
			ids = found.ids;
		}
		if (ids.length === 0) return refuse(400, 'jumps_required');
		if (ids.length > BATCH_MAX) return refuse(400, 'too_many_jumps');
		const parsed = batchChanges(data);
		if ('error' in parsed) return refuse(400, parsed.error);
		const preview = await call<BatchPreviewOut>(api, 'previewJumpBatch', {
			bearer: secret,
			body: { jump_ids: ids, changes: parsed.changes }
		});
		if (!preview.ok) return refuse(failStatus(preview), preview.reason);
		return { form: 'batch' as const, preview: preview.value, ids, all, choice: parsed.form };
	},

	/** Step 2: change them, each only if unchanged since step 1. */
	apply: async (event) => {
		const secret = secretFor(event);
		const data = await event.request.formData();
		const jumps = chosenVersions(data);
		const refuse = (status: number, error: string) =>
			fail(status, { form: 'apply' as const, error });
		if (jumps.length === 0) return refuse(400, 'jumps_required');
		const parsed = batchChanges(data);
		if ('error' in parsed) return refuse(400, parsed.error);
		const result = await call<BatchResultOut>(createRequestApi(), 'applyJumpBatch', {
			bearer: secret,
			body: { jumps, changes: parsed.changes }
		});
		if (!result.ok) return refuse(failStatus(result), result.reason);
		const r = result.value;
		redirect(
			303,
			`/jumps?changed=${r.changed.length}&skipped=${r.skipped.length}&unchanged=${r.unchanged.length}`
		);
	},

	/** "Undo this change": only jumps untouched since are put back. */
	undo: async (event) => {
		const secret = secretFor(event);
		const data = await event.request.formData();
		const batchId = field(data, 'batch_id', { max: 64 });
		if (!isUuid(batchId)) return fail(400, { form: 'undo' as const, error: 'undo_unavailable' });
		const result = await call<UndoResultOut>(createRequestApi(), 'undoJumpBatch', {
			bearer: secret,
			body: { batch_id: batchId }
		});
		if (!result.ok) return fail(failStatus(result), { form: 'undo' as const, error: result.reason });
		redirect(
			303,
			`/jumps?restored=${result.value.restored.length}&not_restored=${result.value.skipped.length}`
		);
	}
};
