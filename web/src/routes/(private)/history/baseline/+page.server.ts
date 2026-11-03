import { fail, redirect } from '@sveltejs/kit';
import type { BaselinePreviewOut, HistoryOut } from '#lib/contracts/index.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { baselineInput } from '#lib/server/baseline-form.ts';
import { field } from '#lib/server/forms.ts';
import { isHistory, isPreview } from '#lib/server/history.ts';
import { call, failStatus } from '#lib/server/maintenance.ts';
import { version } from '#lib/server/review-forms.ts';
import { readSessionSecret } from '#lib/server/session.ts';
import { requireViewer } from '#lib/server/viewer.ts';
import type { Actions, PageServerLoad, RequestEvent } from './$types';

function secretFor(event: Pick<RequestEvent, 'locals' | 'url' | 'cookies'>): string {
	requireViewer(event.locals.viewer, event.url);
	const secret = readSessionSecret(event.cookies);
	if (!secret) redirect(303, '/sign-in');
	return secret;
}

export const load: PageServerLoad = async (event) => {
	const viewer = requireViewer(event.locals.viewer, event.url);
	const secret = secretFor(event);
	const api = createRequestApi();
	const history = await call<HistoryOut>(api, 'getHistory', { bearer: secret }, isHistory);
	// A preview is a read: the proposed values travel in the query, together with the
	// version they were entered against, which the save then sends unchanged.
	const input = baselineInput(event.url.searchParams);
	let preview:
		| { ok: true; value: BaselinePreviewOut; prior_jumps: number; before_on: string }
		| { ok: false; error: string }
		| null = null;
	if (input && 'error' in input) {
		preview = { ok: false, error: input.error };
	} else if (input) {
		const result = await call<BaselinePreviewOut>(
			api,
			'previewBaseline',
			{
				bearer: secret,
				query: { prior_jumps: String(input.prior_jumps), before_on: input.before_on }
			},
			isPreview
		);
		preview = result.ok
			? { ok: true, value: result.value, ...input }
			: { ok: false, error: result.reason };
	}
	return {
		emailVerified: viewer.emailVerified,
		history: history.ok
			? { ok: true as const, ...history.value }
			: { ok: false as const, reason: history.reason },
		preview,
		based: input && !('error' in input) ? input.version : null,
		entered: {
			prior_jumps: event.url.searchParams.get('prior_jumps')?.slice(0, 16) ?? '',
			before_on: event.url.searchParams.get('before_on')?.slice(0, 10) ?? ''
		}
	};
};

export const actions: Actions = {
	save: async (event) => {
		const secret = secretFor(event);
		const input = baselineInput(await event.request.formData());
		if (!input) return fail(400, { form: 'save', error: 'missing' });
		if ('error' in input) return fail(400, { form: 'save', error: input.error });
		const saved = await call<HistoryOut>(
			createRequestApi(),
			'setBaseline',
			{ bearer: secret, body: input },
			isHistory
		);
		if (!saved.ok) return fail(failStatus(saved), { form: 'save', error: saved.reason });
		redirect(303, '/history?saved=1');
	},

	remove: async (event) => {
		const secret = secretFor(event);
		const data = await event.request.formData();
		if (field(data, 'confirm', { max: 4 }) !== 'on') {
			return fail(400, { form: 'remove', error: 'confirm_remove' });
		}
		const v = version(data);
		if (!v) return fail(400, { form: 'remove', error: 'edit_conflict' });
		const result = await call<null>(createRequestApi(), 'removeBaseline', {
			bearer: secret,
			query: { version: String(v) }
		});
		if (!result.ok) return fail(failStatus(result), { form: 'remove', error: result.reason });
		redirect(303, '/history?removed=1');
	}
};
