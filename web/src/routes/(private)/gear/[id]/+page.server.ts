import { error, fail, redirect } from '@sveltejs/kit';
import type { ComponentDetailOut, GearDueOut, RigOut, ServiceOut } from '#lib/contracts/index.ts';
import { CANOPY_KINDS, parseCanopySize, parseInterval, parseJumpLimit } from '#lib/gear.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { isUuid } from '#lib/server/api/transport.ts';
import { field } from '#lib/server/forms.ts';
import { call, failStatus, isList } from '#lib/server/maintenance.ts';
import { echo, text, version } from '#lib/server/review-forms.ts';
import { readSessionSecret } from '#lib/server/session.ts';
import { requireViewer } from '#lib/server/viewer.ts';
import type { Actions, PageServerLoad, RequestEvent } from './$types';

const DATE = /^\d{4}-\d{2}-\d{2}$/;

function secretFor(event: Pick<RequestEvent, 'locals' | 'url' | 'cookies'>): string {
	requireViewer(event.locals.viewer, event.url);
	const secret = readSessionSecret(event.cookies);
	if (!secret) redirect(303, '/sign-in');
	return secret;
}

export const load: PageServerLoad = async (event) => {
	const secret = secretFor(event);
	const viewer = requireViewer(event.locals.viewer, event.url);
	const id = event.params.id;
	if (id !== 'new' && !isUuid(id)) error(404, 'Not found');
	const api = createRequestApi();
	const [detail, rigs, due] = await Promise.all([
		id === 'new'
			? Promise.resolve(null)
			: call<ComponentDetailOut>(api, 'getComponent', { bearer: secret, id }),
		call<RigOut[]>(api, 'listRigs', { bearer: secret }, isList),
		// One owner-scoped list for all gear; this page shows this component's dates.
		id === 'new'
			? Promise.resolve(null)
			: call<GearDueOut[]>(api, 'listGearDue', { bearer: secret }, isList)
	]);
	if (detail && !detail.ok) {
		if (detail.reason === 'not_found') error(404, 'Not found');
		error(503, 'Gear is unavailable right now. Try again later.');
	}
	return {
		emailVerified: viewer.emailVerified,
		detail: detail ? detail.value : null,
		rigs: rigs.ok ? rigs.value.filter((r) => !r.archived) : [],
		due: due?.ok ? due.value.filter((d) => d.component.id === id) : [],
		// UTC day for the first render; the due list then uses the jumper's own day.
		today: new Date().toISOString().slice(0, 10),
		// One key per rendered form: resubmitting the same form is not a duplicate.
		createKey: crypto.randomUUID(),
		serviceKey: crypto.randomUUID()
	};
};

function componentFields(data: FormData) {
	return {
		kind: text(data, 'kind', 16),
		label: text(data, 'label', 200),
		manufacturer: text(data, 'manufacturer', 200),
		model: text(data, 'model', 200),
		// Serial whitespace inside the value is kept; the API trims only the edges.
		serial: field(data, 'serial', { max: 400 }) || null,
		manufactured: text(data, 'manufactured', 10),
		relation: text(data, 'relation', 16) ?? 'owned',
		acquisition_method: text(data, 'acquisition_method', 16),
		acquired: text(data, 'acquired', 10),
		notes: text(data, 'notes', 2000),
		// Only a reserve shows the interval field; anything else sends none (the default).
		repack_interval_days: parseInterval(field(data, 'repack_interval_days', { max: 8 })),
		end_of_life_on: text(data, 'end_of_life_on', 10),
		// All three together; empty number and label clear the limit.
		jump_limit: parseJumpLimit(field(data, 'jump_limit', { max: 12 })),
		jump_limit_label: text(data, 'jump_limit_label', 200),
		jump_limit_service_kind: text(data, 'jump_limit_service_kind', 16),
		// Only a main or reserve shows the size field; anything else sends none.
		canopy_size_sqft: parseCanopySize(field(data, 'canopy_size_sqft', { max: 12 }))
	};
}

export const actions: Actions = {
	save: async (event) => {
		const secret = secretFor(event);
		const data = await event.request.formData();
		const body = componentFields(data);
		if (body.relation !== 'owned') {
			body.acquisition_method = null;
			body.acquired = null;
		}
		// A refused edit re-renders with the version it was based on, so resending
		// after an edit conflict conflicts again instead of overwriting.
		const based = version(data);
		if (!body.kind || !body.label)
			return fail(400, { form: 'save', error: 'missing', values: echo(data), based });
		if (body.repack_interval_days === 'invalid')
			return fail(400, { form: 'save', error: 'repack_interval_invalid', values: echo(data), based });
		if (body.jump_limit === 'invalid')
			return fail(400, { form: 'save', error: 'jump_limit_invalid', values: echo(data), based });
		if (body.jump_limit === null && !body.jump_limit_label) body.jump_limit_service_kind = null;
		if (!CANOPY_KINDS.includes(body.kind)) body.canopy_size_sqft = null;
		if (body.canopy_size_sqft === 'invalid')
			return fail(400, { form: 'save', error: 'canopy_size_invalid', values: echo(data), based });
		if (body.end_of_life_on && !DATE.test(body.end_of_life_on))
			return fail(400, { form: 'save', error: 'end_of_life_invalid', values: echo(data), based });
		const api = createRequestApi();
		if (event.params.id === 'new') {
			const clientKey = field(data, 'client_key', { max: 64 });
			if (!isUuid(clientKey))
				return fail(400, { form: 'save', error: 'invalid_input', values: echo(data) });
			const created = await call<ComponentDetailOut>(api, 'createComponent', {
				bearer: secret,
				body: { ...body, client_key: clientKey }
			});
			if (!created.ok) {
				return fail(failStatus(created), {
					form: 'save',
					error: created.reason,
					values: echo(data)
				});
			}
			redirect(303, `/gear/${created.value.component.id}?saved=1`);
		}
		const updated = await call<ComponentDetailOut>(api, 'updateComponent', {
			bearer: secret,
			id: event.params.id,
			body: { ...body, version: based }
		});
		if (!updated.ok) {
			return fail(failStatus(updated), {
				form: 'save',
				error: updated.reason,
				values: echo(data),
				based
			});
		}
		return { form: 'save', done: true };
	},

	place: async (event) => {
		const secret = secretFor(event);
		const data = await event.request.formData();
		const rig = field(data, 'rig_id', { max: 64 });
		const on = field(data, 'on', { max: 10 });
		// 'none' takes it out of its rig; an unchosen move is not sent.
		if (!DATE.test(on) || (rig !== 'none' && !isUuid(rig)))
			return fail(400, { form: 'place', error: 'invalid_input' });
		const result = await call<ComponentDetailOut>(createRequestApi(), 'placeComponent', {
			bearer: secret,
			id: event.params.id,
			body: { rig_id: rig === 'none' ? null : rig, on, version: version(data) }
		});
		if (!result.ok) return fail(failStatus(result), { form: 'place', error: result.reason });
		return { form: 'place', done: true };
	},

	service: async (event) => {
		const secret = secretFor(event);
		const data = await event.request.formData();
		const clientKey = field(data, 'client_key', { max: 64 });
		const doneOn = field(data, 'done_on', { max: 10 });
		const dueOn = field(data, 'due_on', { max: 10 });
		if (!isUuid(clientKey) || !DATE.test(doneOn) || (dueOn && !DATE.test(dueOn))) {
			return fail(400, { form: 'service', error: 'service_incomplete', values: echo(data) });
		}
		const result = await call<ServiceOut>(createRequestApi(), 'addServiceEntry', {
			bearer: secret,
			id: event.params.id,
			body: {
				client_key: clientKey,
				kind: field(data, 'kind', { max: 16 }),
				done_on: doneOn,
				due_on: dueOn || null,
				performed_by: text(data, 'performed_by', 200),
				notes: text(data, 'notes', 2000)
			}
		});
		if (!result.ok) {
			return fail(failStatus(result), {
				form: 'service',
				error: result.reason,
				values: echo(data)
			});
		}
		redirect(303, `/gear/${event.params.id}?service=1`);
	},

	removeService: async (event) => {
		const secret = secretFor(event);
		const sub = field(await event.request.formData(), 'entry', { max: 64 });
		if (!isUuid(sub)) return fail(404, { form: 'removeService', error: 'not_found' });
		const result = await call<null>(createRequestApi(), 'deleteServiceEntry', {
			bearer: secret,
			id: event.params.id,
			sub
		});
		if (!result.ok)
			return fail(failStatus(result), { form: 'removeService', error: result.reason });
		return { form: 'removeService', done: true };
	},

	archive: async (event) => {
		const secret = secretFor(event);
		const data = await event.request.formData();
		const result = await call<ComponentDetailOut>(createRequestApi(), 'archiveComponent', {
			bearer: secret,
			id: event.params.id,
			body: { archived: field(data, 'archived', { max: 5 }) === 'true', version: version(data) }
		});
		if (!result.ok) return fail(failStatus(result), { form: 'archive', error: result.reason });
		return { form: 'archive', done: true };
	},

	delete: async (event) => {
		const secret = secretFor(event);
		const data = await event.request.formData();
		if (field(data, 'confirm', { max: 4 }) !== 'on') {
			return fail(400, { form: 'delete', error: 'confirm_delete' });
		}
		const v = version(data);
		const result = await call<null>(createRequestApi(), 'deleteComponent', {
			bearer: secret,
			id: event.params.id,
			query: { version: v ? String(v) : undefined }
		});
		if (!result.ok) return fail(failStatus(result), { form: 'delete', error: result.reason });
		redirect(303, '/gear?deleted=1');
	}
};
