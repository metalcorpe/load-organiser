import { fail, redirect } from '@sveltejs/kit';
import type { ImportCheckOut, ImportOut, ImportResultOut } from '#lib/contracts/index.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { isUuid } from '#lib/server/api/transport.ts';
import { field } from '#lib/server/forms.ts';
import { readImportUpload } from '#lib/server/import-upload.ts';
import { call, failStatus, isList, type Refusal } from '#lib/server/maintenance.ts';
import { readSessionSecret } from '#lib/server/session.ts';
import { requireViewer } from '#lib/server/viewer.ts';
import type { Actions, PageServerLoad, RequestEvent } from './$types';

function secretFor(event: Pick<RequestEvent, 'locals' | 'url' | 'cookies'>): string {
	requireViewer(event.locals.viewer, event.url);
	const secret = readSessionSecret(event.cookies);
	if (!secret) redirect(303, '/sign-in');
	return secret;
}

/** Place names the API listed for `country_required` (plain text, bounded). */
function namesOf(refusal: Refusal): string[] {
	const names = 'body' in refusal ? refusal.body?.names : undefined;
	return Array.isArray(names)
		? names
				.filter((n): n is string => typeof n === 'string')
				.slice(0, 50)
				.map((n) => n.slice(0, 120))
		: [];
}

export const load: PageServerLoad = async (event) => {
	const viewer = requireViewer(event.locals.viewer, event.url);
	const secret = secretFor(event);
	const imports = await call<ImportOut[]>(
		createRequestApi(),
		'listJumpImports',
		{ bearer: secret },
		isList
	);
	return {
		emailVerified: viewer.emailVerified,
		imports: imports.ok
			? { ok: true as const, items: imports.value }
			: { ok: false as const, reason: imports.reason }
	};
};

export const actions: Actions = {
	check: async (event) => {
		const secret = secretFor(event);
		const upload = await readImportUpload(event.request);
		if (!upload.ok) {
			return fail(upload.status, {
				form: 'check',
				error: upload.error,
				choices: upload.choices
			});
		}
		const result = await call<ImportCheckOut>(createRequestApi(), 'checkJumpImport', {
			bearer: secret,
			rawBody: upload.bytes,
			query: upload.query
		});
		if (!result.ok) {
			return fail(failStatus(result), {
				form: 'check',
				error: result.reason,
				names: namesOf(result),
				choices: upload.choices
			});
		}
		return { form: 'check', check: result.value, choices: upload.choices };
	},

	import: async (event) => {
		const secret = secretFor(event);
		const upload = await readImportUpload(event.request);
		if (!upload.ok) {
			return fail(upload.status, {
				form: 'import',
				error: upload.error,
				choices: upload.choices
			});
		}
		const result = await call<ImportResultOut>(createRequestApi(), 'importJumps', {
			bearer: secret,
			rawBody: upload.bytes,
			query: upload.query
		});
		if (!result.ok) {
			return fail(failStatus(result), {
				form: 'import',
				error: result.reason,
				names: namesOf(result),
				choices: upload.choices
			});
		}
		return { form: 'import', result: result.value, choices: upload.choices };
	},

	undo: async (event) => {
		const secret = secretFor(event);
		const data = await event.request.formData();
		const id = field(data, 'id', { max: 64 });
		if (!isUuid(id)) return fail(400, { form: 'undo', id, error: 'not_found' });
		if (data.get('confirm') !== 'on') return fail(400, { form: 'undo', id, error: 'confirm_undo' });
		const result = await call<ImportOut>(createRequestApi(), 'undoJumpImport', {
			bearer: secret,
			id,
			body: { confirm: true }
		});
		if (!result.ok)
			return fail(failStatus(result), {
				form: 'undo',
				id,
				error: result.reason
			});
		return { form: 'undo', id, undone: result.value };
	}
};
