import { error, fail, redirect } from '@sveltejs/kit';
import type { PostOut } from '#lib/contracts/index.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { isUuid } from '#lib/server/api/transport.ts';
import { field } from '#lib/server/forms.ts';
import { call, failStatus } from '#lib/server/maintenance.ts';
import { readSessionSecret } from '#lib/server/session.ts';
import { requireViewer } from '#lib/server/viewer.ts';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	if (!isUuid(event.params.id)) error(404, 'This post is not available.');
	// Signed-in readers send their session so follows and blocks apply.
	const bearer = event.locals.viewer ? (readSessionSecret(event.cookies) ?? undefined) : undefined;
	const post = await call<PostOut>(createRequestApi(), 'getPost', { bearer, id: event.params.id });
	if (!post.ok) {
		// One answer for missing, unpublished, withdrawn, follower-only and blocked.
		if (post.reason === 'not_found') error(404, 'This post is not available.');
		error(503, 'Posts are unavailable right now. Try again later.');
	}
	return {
		post: post.value,
		signedIn: Boolean(event.locals.viewer),
		emailVerified: event.locals.viewer?.emailVerified ?? false
	};
};

export const actions: Actions = {
	report: async (event) => {
		requireViewer(event.locals.viewer, event.url);
		const secret = readSessionSecret(event.cookies);
		if (!secret) redirect(303, '/sign-in');
		const data = await event.request.formData();
		const reason = field(data, 'reason', { max: 16 });
		const note = field(data, 'note', { max: 4000, trim: true });
		if (!reason) return fail(400, { form: 'report', error: 'reason_invalid' });
		const result = await call(createRequestApi(), 'reportPost', {
			bearer: secret,
			id: event.params.id,
			body: { reason, note: note || null }
		});
		if (!result.ok) return fail(failStatus(result), { form: 'report', error: result.reason });
		return { form: 'report', done: true };
	}
};
