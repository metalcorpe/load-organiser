import { redirect } from '@sveltejs/kit';
import { createRequestApi } from '#lib/server/api/client.ts';
import { field } from '#lib/server/forms.ts';
import { readSessionSecret } from '#lib/server/session.ts';
import { requireViewer } from '#lib/server/viewer.ts';
import { dateParam } from '#lib/print.ts';
import type { RequestHandler } from './$types';

/**
 * The owner's logbook as a spreadsheet (CSV) download. A POST (same-origin form,
 * Origin checked by SvelteKit), so no link prefetch or crawler can spend the rate
 * limit. One API call returns the whole file (at most 2,000 jumps); it is passed on
 * with a byte-order mark so Excel reads it as UTF-8. The name holds no account detail.
 */
export const POST: RequestHandler = async ({ locals, url, cookies, request }) => {
	requireViewer(locals.viewer, url);
	const secret = readSessionSecret(cookies);
	if (!secret) redirect(303, '/sign-in');
	const data = await request.formData();
	const from = dateParam(field(data, 'from', { max: 10 }));
	const until = dateParam(field(data, 'until', { max: 10 }));
	const range = `${from ? `&from=${from}` : ''}${until ? `&until=${until}` : ''}`;
	if (from && until && from > until) redirect(303, `/records?spreadsheet=date_range_invalid${range}`);
	const result = await createRequestApi().request('exportSpreadsheet', {
		bearer: secret,
		query: { from_on: from || undefined, until_on: until || undefined }
	});
	if (result.kind !== 'response' || result.status !== 200 || typeof result.body !== 'string') {
		const reason =
			result.kind === 'response' && result.status === 429
				? 'too_many_attempts'
				: result.kind === 'response' && result.status === 422
					? 'date_range_invalid'
					: result.kind === 'timeout'
						? 'uncertain'
						: 'unavailable';
		redirect(303, `/records?spreadsheet=${reason}${range}`);
	}
	const day = new Date().toISOString().slice(0, 10);
	// The transport decodes the text and drops the API's byte-order mark; put it back.
	const body = result.body.startsWith('﻿') ? result.body : `﻿${result.body}`;
	return new Response(body, {
		headers: {
			'content-type': 'text/csv; charset=utf-8',
			'content-disposition': `attachment; filename="load-organiser-logbook-${day}.csv"`,
			'cache-control': 'no-store',
			'x-content-type-options': 'nosniff'
		}
	});
};
