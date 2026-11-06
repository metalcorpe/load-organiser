import { error, fail, redirect } from '@sveltejs/kit';
import type { PostPageOut, ProfileViewOut } from '#lib/contracts/index.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { isHandle, isUuid } from '#lib/server/api/transport.ts';
import { field } from '#lib/server/forms.ts';
import { call, failStatus } from '#lib/server/maintenance.ts';
import { readSessionSecret } from '#lib/server/session.ts';
import { requireViewer } from '#lib/server/viewer.ts';
import type { Actions, PageServerLoad, RequestEvent } from './$types';

/** Signed-in viewers send their session (blocks and follows apply); others are anonymous. */
function optionalSecret(event: Pick<RequestEvent, 'locals' | 'cookies'>): string | undefined {
	return event.locals.viewer ? (readSessionSecret(event.cookies) ?? undefined) : undefined;
}

function secretFor(event: Pick<RequestEvent, 'locals' | 'url' | 'cookies'>): string {
	requireViewer(event.locals.viewer, event.url);
	const secret = readSessionSecret(event.cookies);
	if (!secret) redirect(303, '/sign-in');
	return secret;
}

export const load: PageServerLoad = async (event) => {
	const handle = event.params.handle.toLowerCase();
	if (!isHandle(handle)) error(404, 'This profile is not available.');
	if (handle !== event.params.handle) redirect(301, `/people/${handle}`);
	const api = createRequestApi();
	const bearer = optionalSecret(event);
	const before = event.url.searchParams.get('before') ?? '';
	const [person, posts] = await Promise.all([
		call<ProfileViewOut>(api, 'getPerson', { bearer, handle }),
		call<PostPageOut>(api, 'listPersonPosts', {
			bearer,
			handle,
			query: { before: isUuid(before) ? before : undefined }
		})
	]);
	if (!person.ok) {
		// One answer for missing, hidden, blocked and not discoverable.
		if (person.reason === 'not_found') error(404, 'This profile is not available.');
		error(503, 'Profiles are unavailable right now. Try again later.');
	}
	return {
		person: person.value,
		// Each post is checked again by the API; a failure only hides the list.
		posts: posts.ok ? posts.value : null,
		older: isUuid(before),
		signedIn: Boolean(event.locals.viewer),
		emailVerified: event.locals.viewer?.emailVerified ?? false
	};
};

async function act(
	event: RequestEvent,
	form: string,
	operation: 'followPerson' | 'unfollowPerson' | 'blockPerson'
) {
	const secret = secretFor(event);
	const result = await call(createRequestApi(), operation, {
		bearer: secret,
		handle: event.params.handle
	});
	if (!result.ok) return fail(failStatus(result), { form, error: result.reason });
	return { form, done: true };
}

export const actions: Actions = {
	follow: (event) => act(event, 'follow', 'followPerson'),
	unfollow: (event) => act(event, 'follow', 'unfollowPerson'),

	block: async (event) => {
		const data = await event.request.formData();
		if (field(data, 'confirm', { max: 4 }) !== 'on') {
			return fail(400, { form: 'block', error: 'confirm_block' });
		}
		const outcome = await act(event, 'block', 'blockPerson');
		if ('done' in outcome) redirect(303, '/people?blocked=1');
		return outcome;
	},

	report: async (event) => {
		const secret = secretFor(event);
		const data = await event.request.formData();
		const reason = field(data, 'reason', { max: 16 });
		const note = field(data, 'note', { max: 4000, trim: true });
		if (!reason) return fail(400, { form: 'report', error: 'reason_invalid' });
		const result = await call(createRequestApi(), 'reportPerson', {
			bearer: secret,
			handle: event.params.handle,
			body: { reason, note: note || null }
		});
		if (!result.ok) return fail(failStatus(result), { form: 'report', error: result.reason });
		return { form: 'report', done: true };
	}
};
