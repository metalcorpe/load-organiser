import { redirect } from '@sveltejs/kit';
import type { OwnProfileOut, PostPageOut } from '#lib/contracts/index.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { isUuid } from '#lib/server/api/transport.ts';
import { call } from '#lib/server/maintenance.ts';
import { readSessionSecret } from '#lib/server/session.ts';
import { requireViewer } from '#lib/server/viewer.ts';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	requireViewer(event.locals.viewer, event.url);
	const secret = readSessionSecret(event.cookies);
	if (!secret) redirect(303, '/sign-in');
	const before = event.url.searchParams.get('before') ?? '';
	const api = createRequestApi();
	const [feed, own] = await Promise.all([
		call<PostPageOut>(api, 'getFeed', {
			bearer: secret,
			query: { before: isUuid(before) ? before : undefined }
		}),
		call<OwnProfileOut | null>(api, 'getOwnProfile', { bearer: secret }, () => true)
	]);
	return {
		feed: feed.ok ? feed.value : null,
		older: isUuid(before),
		hasProfile: own.ok ? own.value !== null : true
	};
};
