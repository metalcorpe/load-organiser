import { fail, redirect } from '@sveltejs/kit';
import type { OwnProfileOut, PersonOut } from '#lib/contracts/index.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { isHandle, type OperationId } from '#lib/server/api/transport.ts';
import { field } from '#lib/server/forms.ts';
import { call, failStatus, isList } from '#lib/server/maintenance.ts';
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
	const list = async (operation: OperationId) => {
		const result = await call<PersonOut[]>(api, operation, { bearer: secret }, isList);
		return result.ok ? result.value : null;
	};
	const q = (event.url.searchParams.get('q') ?? '').trim().slice(0, 40);
	const [own, requests, followers, following, blocked, found] = await Promise.all([
		call<OwnProfileOut | null>(api, 'getOwnProfile', { bearer: secret }, () => true),
		list('listFollowRequests'),
		list('listFollowers'),
		list('listFollowing'),
		list('listBlocked'),
		q
			? call<PersonOut[]>(api, 'searchPeople', { bearer: secret, query: { q } }, isList)
			: Promise.resolve(null)
	]);
	return {
		emailVerified: viewer.emailVerified,
		profile: own.ok ? own.value : null,
		profileOk: own.ok,
		requests,
		followers,
		following,
		blocked,
		q,
		search:
			found === null
				? null
				: found.ok
					? { ok: true as const, items: found.value }
					: { ok: false as const, reason: found.reason }
	};
};

function act(form: string, operation: OperationId) {
	return async (event: RequestEvent) => {
		const secret = secretFor(event);
		const data = await event.request.formData();
		const handle = field(data, 'handle', { max: 40 });
		if (!isHandle(handle)) return fail(400, { form, error: 'not_found' });
		const result = await call(createRequestApi(), operation, { bearer: secret, handle });
		if (!result.ok) return fail(failStatus(result), { form, error: result.reason, handle });
		return { form, done: true, handle };
	};
}

const blockFollower = act('people', 'blockPerson');

export const actions: Actions = {
	block: async (event) => {
		const data = await event.request.clone().formData();
		if (field(data, 'confirm', { max: 4 }) !== 'on') {
			return fail(400, {
				form: 'people',
				error: 'confirm_block',
				handle: field(data, 'handle', { max: 40 })
			});
		}
		const outcome = await blockFollower(event);
		if ('done' in outcome) redirect(303, '/people?blocked=1');
		return outcome;
	},
	approve: act('requests', 'approveFollower'),
	reject: act('requests', 'rejectFollower'),
	remove: act('followers', 'removeFollower'),
	unblock: act('blocked', 'unblockPerson')
};
