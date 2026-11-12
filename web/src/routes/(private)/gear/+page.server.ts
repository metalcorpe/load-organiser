import { fail, redirect } from '@sveltejs/kit';
import type { ComponentSummaryOut, GearDueOut, RigOut } from '#lib/contracts/index.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { field } from '#lib/server/forms.ts';
import { call, failStatus, isList } from '#lib/server/maintenance.ts';
import { readSessionSecret } from '#lib/server/session.ts';
import { requireViewer } from '#lib/server/viewer.ts';
import { isUuid } from '#lib/server/api/transport.ts';
import type { Actions, PageServerLoad, RequestEvent } from './$types';

function secretFor(event: Pick<RequestEvent, 'locals' | 'url' | 'cookies'>): string {
	requireViewer(event.locals.viewer, event.url);
	const secret = readSessionSecret(event.cookies);
	if (!secret) redirect(303, '/sign-in');
	return secret;
}

export const load: PageServerLoad = async (event) => {
	const secret = secretFor(event);
	const viewer = requireViewer(event.locals.viewer, event.url);
	const archived = event.url.searchParams.get('archived') === '1';
	const api = createRequestApi();
	const [components, rigs, due] = await Promise.all([
		call<ComponentSummaryOut[]>(
			api,
			'listComponents',
			{ bearer: secret, query: { archived: archived ? 'true' : undefined } },
			isList
		),
		call<RigOut[]>(api, 'listRigs', { bearer: secret }, isList),
		// Dates coming due on current gear; not shown with the archived list.
		archived ? null : call<GearDueOut[]>(api, 'listGearDue', { bearer: secret }, isList)
	]);
	return {
		emailVerified: viewer.emailVerified,
		archived,
		rigKey: crypto.randomUUID(),
		components: components.ok
			? { ok: true as const, items: components.value }
			: { ok: false as const, reason: components.reason },
		rigs: rigs.ok
			? { ok: true as const, items: rigs.value }
			: { ok: false as const, reason: rigs.reason },
		due: due?.ok ? due.value : [],
		dueFailed: due ? !due.ok : false,
		// UTC day for the first render; the due list then uses the jumper's own day.
		today: new Date().toISOString().slice(0, 10)
	};
};

export const actions: Actions = {
	rig: async (event) => {
		const secret = secretFor(event);
		const data = await event.request.formData();
		const label = field(data, 'label', { max: 200, trim: true });
		const clientKey = field(data, 'client_key', { max: 64 });
		if (!label || !isUuid(clientKey)) return fail(400, { form: 'rig', error: 'label_required' });
		const result = await call<RigOut>(createRequestApi(), 'createRig', {
			bearer: secret,
			body: { client_key: clientKey, label }
		});
		if (!result.ok) return fail(failStatus(result), { form: 'rig', error: result.reason });
		redirect(303, '/gear?rig=1');
	},

	archiveRig: async (event) => {
		const secret = secretFor(event);
		const data = await event.request.formData();
		const id = field(data, 'id', { max: 64 });
		const version = Number(field(data, 'version', { max: 12 }));
		if (!isUuid(id)) return fail(404, { form: 'archiveRig', error: 'not_found' });
		const result = await call<RigOut>(createRequestApi(), 'updateRig', {
			bearer: secret,
			id,
			body: { archived: field(data, 'archived', { max: 5 }) === 'true', version: version || null }
		});
		if (!result.ok) return fail(failStatus(result), { form: 'archiveRig', error: result.reason });
		return { form: 'archiveRig', done: true };
	}
};
