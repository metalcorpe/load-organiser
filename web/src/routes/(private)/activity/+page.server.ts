import { redirect } from '@sveltejs/kit';
import type { OwnProfileOut, PersonOut, PostPageOut } from '#lib/contracts/index.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { isUuid } from '#lib/server/api/transport.ts';
import { call, isList } from '#lib/server/maintenance.ts';
import { signInPath } from '#lib/safe-return.ts';
import { readSessionSecret } from '#lib/server/session.ts';
import { requireViewer } from '#lib/server/viewer.ts';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	requireViewer(event.locals.viewer, event.url);
	const secret = readSessionSecret(event.cookies);
	if (!secret) redirect(303, '/sign-in');
	const before = event.url.searchParams.get('before') ?? '';
	const api = createRequestApi();
	const [feed, own, following] = await Promise.all([
		call<PostPageOut>(api, 'getFeed', {
			bearer: secret,
			query: { before: isUuid(before) ? before : undefined }
		}),
		call<OwnProfileOut | null>(api, 'getOwnProfile', { bearer: secret }, () => true),
		// The people you follow sit beside the feed. Their failure is shown there (null) and
		// never hides the feed.
		call<PersonOut[]>(api, 'listFollowing', { bearer: secret }, isList)
	]);
	// The session ended between the guard and the API call: sign in again.
	if (!feed.ok && feed.status === 401) redirect(303, signInPath(event.url));
	return {
		feed: feed.ok ? feed.value : null,
		older: isUuid(before),
		hasProfile: own.ok ? own.value !== null : true,
		// Waiting follow requests come with the viewer's own profile.
		requests: own.ok && own.value ? own.value.pending_requests : 0,
		following: following.ok ? following.value : null
	};
};
