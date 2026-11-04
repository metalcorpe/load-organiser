import { fail } from '@sveltejs/kit';
import type { ReportOut } from '#lib/contracts/index.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { isHandle, isUuid } from '#lib/server/api/transport.ts';
import { field } from '#lib/server/forms.ts';
import { call, failStatus, isList } from '#lib/server/maintenance.ts';
import { requireReviewer } from '#lib/server/reviewer.ts';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	const secret = requireReviewer(event);
	const status = event.url.searchParams.get('status') === 'closed' ? 'closed' : 'open';
	const reports = await call<ReportOut[]>(
		createRequestApi(),
		'listSocialReports',
		{ bearer: secret, query: { status } },
		isList
	);
	return {
		status,
		reports: reports.ok
			? { ok: true as const, items: reports.value }
			: { ok: false as const, reason: reports.reason }
	};
};

export const actions: Actions = {
	decide: async (event) => {
		const secret = requireReviewer(event);
		const data = await event.request.formData();
		const id = field(data, 'id', { max: 64 });
		if (!isUuid(id)) return fail(400, { form: 'decide', id, error: 'not_found' });
		const reason = field(data, 'reason', { max: 2000, trim: true });
		const result = await call(createRequestApi(), 'decideSocialReport', {
			bearer: secret,
			id,
			body: { decision: field(data, 'decision', { max: 24 }), reason: reason || null }
		});
		if (!result.ok) return fail(failStatus(result), { form: 'decide', id, error: result.reason });
		return { form: 'decide', id, done: true };
	},

	moderate: async (event) => {
		const secret = requireReviewer(event);
		const data = await event.request.formData();
		const handle = field(data, 'handle', { max: 40 });
		if (!isHandle(handle)) return fail(400, { form: 'moderate', handle, error: 'not_found' });
		const result = await call(createRequestApi(), 'moderateProfile', {
			bearer: secret,
			handle,
			body: {
				hidden: field(data, 'hidden', { max: 4 }) === 'on',
				publishing_restricted: field(data, 'restricted', { max: 4 }) === 'on',
				reason: field(data, 'reason', { max: 2000, trim: true })
			}
		});
		if (!result.ok) {
			return fail(failStatus(result), { form: 'moderate', handle, error: result.reason });
		}
		return { form: 'moderate', handle, done: true };
	}
};
