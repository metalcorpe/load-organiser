import { redirect } from '@sveltejs/kit';
import type { JumpPageOut } from '#lib/contracts/index.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { call, isPage } from '#lib/server/maintenance.ts';
import { readSessionSecret } from '#lib/server/session.ts';
import { requireViewer } from '#lib/server/viewer.ts';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async (event) => {
	requireViewer(event.locals.viewer, event.url);
	const secret = readSessionSecret(event.cookies);
	if (!secret) redirect(303, '/sign-in');
	const cursor = (event.url.searchParams.get('cursor') ?? '').slice(0, 200) || undefined;
	const page = await call<JumpPageOut>(
		createRequestApi(),
		'listJumps',
		{ bearer: secret, query: { cursor, limit: '20' } },
		(body) => isPage(body) && typeof (body as JumpPageOut).recorded_total === 'number'
	);
	return {
		page: page.ok
			? { ok: true as const, ...page.value }
			: { ok: false as const, reason: page.reason },
		older: Boolean(cursor)
	};
};
