import { fail, redirect } from '@sveltejs/kit';
import type { OwnProfileOut } from '#lib/contracts/index.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { isUuid } from '#lib/server/api/transport.ts';
import { searchVenues } from '#lib/server/directory.ts';
import { field } from '#lib/server/forms.ts';
import { call, failStatus } from '#lib/server/maintenance.ts';
import { echo, version } from '#lib/server/review-forms.ts';
import { readSessionSecret } from '#lib/server/session.ts';
import { requireViewer } from '#lib/server/viewer.ts';
import { DISCIPLINES } from '#lib/social.ts';
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
	const own = await call<OwnProfileOut | null>(
		api,
		'getOwnProfile',
		{ bearer: secret },
		() => true
	);
	const q = (event.url.searchParams.get('q') ?? '').trim().slice(0, 80);
	const found = q ? await searchVenues(api, { q, limit: 10 }) : null;
	return {
		emailVerified: viewer.emailVerified,
		profileOk: own.ok,
		profile: own.ok ? own.value : null,
		q,
		venues: found === null ? null : found.ok ? found.value.items : []
	};
};

export const actions: Actions = {
	save: async (event) => {
		const secret = secretFor(event);
		const data = await event.request.formData();
		const values = echo(data);
		const home = field(data, 'home', { max: 64 });
		const disciplines = data
			.getAll('disciplines')
			.filter((v): v is string => typeof v === 'string')
			.filter((v) => (DISCIPLINES as readonly string[]).includes(v));
		const handle = field(data, 'handle', { max: 40, trim: true });
		const based = version(data);
		const result = await call<OwnProfileOut>(createRequestApi(), 'saveOwnProfile', {
			bearer: secret,
			body: {
				handle: handle || null,
				display_name: field(data, 'display_name', { max: 200 }),
				bio: field(data, 'bio', { max: 2000 }) || null,
				disciplines,
				home_venue_id: isUuid(home) ? home : null,
				discoverable: field(data, 'discoverable', { max: 4 }) === 'on',
				version: based
			}
		});
		if (!result.ok) {
			return fail(failStatus(result), { form: 'save', error: result.reason, values, based });
		}
		redirect(303, '/profile/public?saved=1');
	}
};
