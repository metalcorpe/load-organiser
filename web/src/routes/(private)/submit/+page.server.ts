import { fail, redirect } from '@sveltejs/kit';
import type {
	OwnSubmissionOut as OwnSubmission,
	SubmissionIntakeOut as Intake
} from '#lib/contracts/index.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { isUuid } from '#lib/server/api/transport.ts';
import { field } from '#lib/server/forms.ts';
import { call, failStatus, isList, isRecord } from '#lib/server/maintenance.ts';
import { readSessionSecret } from '#lib/server/session.ts';
import { requireViewer } from '#lib/server/viewer.ts';
import type { Actions, PageServerLoad, RequestEvent } from './$types';
import { intakePaused } from '#lib/intake.ts';

const KINDS = ['suggest_venue', 'suggest_listing', 'correction', 'report', 'feedback'] as const;
const TARGETS = ['venue', 'provider', 'opportunity'] as const;

function secretFor(event: Pick<RequestEvent, 'locals' | 'url' | 'cookies'>): string {
	requireViewer(event.locals.viewer, event.url);
	const secret = readSessionSecret(event.cookies);
	if (!secret) redirect(303, '/sign-in');
	return secret;
}

function pick<T extends string>(raw: string | null, allowed: readonly T[]): T | null {
	return raw && (allowed as readonly string[]).includes(raw) ? (raw as T) : null;
}

export const load: PageServerLoad = async (event) => {
	const secret = secretFor(event);
	const viewer = requireViewer(event.locals.viewer, event.url);
	const params = event.url.searchParams;
	const targetKind = pick(params.get('target_kind'), TARGETS);
	const targetId = params.get('target_id');
	const api = createRequestApi();
	const [mine, intake] = await Promise.all([
		call<OwnSubmission[]>(api, 'listOwnSubmissions', { bearer: secret }, isList),
		call<Intake>(
			api,
			'getSubmissionIntake',
			{ bearer: secret },
			(v) => isRecord(v) && typeof v.open === 'boolean'
		)
	]);
	return {
		emailVerified: viewer.emailVerified,
		paused: intakePaused(intake),
		kind: pick(params.get('kind'), KINDS) ?? 'suggest_listing',
		target: targetKind && isUuid(targetId) ? { kind: targetKind, id: targetId } : null,
		title: (params.get('title') ?? '').slice(0, 160),
		// One key per rendered form: resubmitting the same form is not a duplicate.
		clientKey: crypto.randomUUID(),
		mine: mine.ok
			? { ok: true as const, items: mine.value }
			: { ok: false as const, reason: mine.reason }
	};
};

export const actions: Actions = {
	default: async (event) => {
		const secret = secretFor(event);
		const data = await event.request.formData();
		const kind = pick(field(data, 'kind', { max: 24 }), KINDS);
		const message = field(data, 'message', { max: 4000, trim: true });
		const sourceUrl = field(data, 'source_url', { max: 2048, trim: true });
		const clientKey = field(data, 'client_key', { max: 64 });
		const targetKind = pick(field(data, 'target_kind', { max: 16 }), TARGETS);
		const targetId = field(data, 'target_id', { max: 64 });
		const values = { message, source_url: sourceUrl, client_key: clientKey };
		if (!kind || !isUuid(clientKey)) return fail(400, { error: 'invalid_input', values });
		if (!message) return fail(400, { error: 'message_required', values });
		const outcome = await call<OwnSubmission>(createRequestApi(), 'createSubmission', {
			bearer: secret,
			body: {
				client_key: clientKey,
				kind,
				message,
				source_url: sourceUrl || null,
				target_kind: targetKind && isUuid(targetId) ? targetKind : null,
				target_id: targetKind && isUuid(targetId) ? targetId : null
			}
		});
		if (!outcome.ok) return fail(failStatus(outcome), { error: outcome.reason, values });
		redirect(303, '/submit?sent=1');
	}
};
