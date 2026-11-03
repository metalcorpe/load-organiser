import { redirect } from '@sveltejs/kit';
import { createRequestApi } from '#lib/server/api/client.ts';
import { readSessionSecret } from '#lib/server/session.ts';
import { requireViewer } from '#lib/server/viewer.ts';
import type { RequestHandler } from './$types';

/**
 * The owner's export as a private download (#155). A POST (same-origin form, Origin
 * checked by SvelteKit), so no link prefetch or crawler can spend the rate limit.
 * The file is passed through unparsed; the name holds no account detail.
 */
export const POST: RequestHandler = async ({ locals, url, cookies }) => {
	requireViewer(locals.viewer, url);
	const secret = readSessionSecret(cookies);
	if (!secret) redirect(303, '/sign-in');
	const result = await createRequestApi().request('exportRecords', { bearer: secret });
	if (result.kind !== 'response' || result.status !== 200 || typeof result.body !== 'string') {
		const reason =
			result.kind === 'response' && result.status === 429
				? 'too_many_attempts'
				: result.kind === 'timeout'
					? 'uncertain'
					: 'unavailable';
		redirect(303, `/profile/data?export=${reason}`);
	}
	const day = new Date().toISOString().slice(0, 10);
	return new Response(result.body, {
		headers: {
			'content-type': 'application/json; charset=utf-8',
			'content-disposition': `attachment; filename="load-organiser-records-${day}.json"`,
			'cache-control': 'no-store',
			'x-content-type-options': 'nosniff'
		}
	});
};
