import { fail, redirect } from '@sveltejs/kit';
import type { RecordsOut, RestoreCheckOut, RestoreOut } from '#lib/contracts/index.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { call, failStatus, type Refusal } from '#lib/server/maintenance.ts';
import { readRestoreUpload } from '#lib/server/restore-upload.ts';
import { readSessionSecret } from '#lib/server/session.ts';
import { requireViewer } from '#lib/server/viewer.ts';
import type { Actions, PageServerLoad, RequestEvent } from './$types';

function secretFor(event: Pick<RequestEvent, 'locals' | 'url' | 'cookies'>): string {
	requireViewer(event.locals.viewer, event.url);
	const secret = readSessionSecret(event.cookies);
	if (!secret) redirect(303, '/sign-in');
	return secret;
}

/** Where an archive failed (position and rule code only; the API sends no content). */
function problemOf(refusal: Refusal): string | null {
	const problem = 'body' in refusal ? refusal.body?.problem : undefined;
	return typeof problem === 'string' && /^[\w.[\]]{1,200}$/.test(problem) ? problem : null;
}

export const load: PageServerLoad = async (event) => {
	const viewer = requireViewer(event.locals.viewer, event.url);
	const secret = secretFor(event);
	const records = await call<RecordsOut>(createRequestApi(), 'getRecords', { bearer: secret });
	return {
		emailVerified: viewer.emailVerified,
		records: records.ok
			? { ok: true as const, ...records.value }
			: { ok: false as const, reason: records.reason },
		exportRefused: event.url.searchParams.get('export')?.slice(0, 40) ?? null
	};
};

export const actions: Actions = {
	check: async (event) => {
		const secret = secretFor(event);
		const upload = await readRestoreUpload(event.request, { needPassword: false });
		if (!upload.ok) return fail(upload.status, { form: 'check', error: upload.error });
		const result = await call<RestoreCheckOut>(createRequestApi(), 'checkRestore', {
			bearer: secret,
			rawBody: upload.bytes
		});
		if (!result.ok) {
			return fail(failStatus(result), {
				form: 'check',
				error: result.reason,
				problem: problemOf(result)
			});
		}
		return { form: 'check', check: result.value };
	},

	restore: async (event) => {
		const secret = secretFor(event);
		const upload = await readRestoreUpload(event.request, { needPassword: true });
		if (!upload.ok) return fail(upload.status, { form: 'restore', error: upload.error });
		const result = await call<RestoreOut>(createRequestApi(), 'restoreRecords', {
			bearer: secret,
			rawBody: upload.bytes,
			confirmPassword: upload.password,
			clientIp: event.getClientAddress()
		});
		if (!result.ok) {
			return fail(failStatus(result), {
				form: 'restore',
				error: result.reason,
				problem: problemOf(result)
			});
		}
		return { form: 'restore', result: result.value };
	}
};
