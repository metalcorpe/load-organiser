import { error, fail, redirect } from '@sveltejs/kit';
import type { PostOut, SharingOut } from '#lib/contracts/index.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { isUuid } from '#lib/server/api/transport.ts';
import { field } from '#lib/server/forms.ts';
import { call, failStatus } from '#lib/server/maintenance.ts';
import { list, version } from '#lib/server/review-forms.ts';
import { readSessionSecret } from '#lib/server/session.ts';
import { requireViewer } from '#lib/server/viewer.ts';
import { SHARE_PARTS } from '#lib/posts.ts';
import type { Actions, PageServerLoad, RequestEvent } from './$types';

function secretFor(event: Pick<RequestEvent, 'locals' | 'url' | 'cookies'>): string {
	requireViewer(event.locals.viewer, event.url);
	const secret = readSessionSecret(event.cookies);
	if (!secret) redirect(303, '/sign-in');
	return secret;
}

const PARTS: readonly string[] = SHARE_PARTS.map((p) => p.value);

/** The choices in a share form, limited to known values. */
function choices(data: FormData) {
	const audience = field(data, 'audience', { max: 16 });
	return {
		shares: list(data, 'shares').filter((v) => PARTS.includes(v)),
		caption: field(data, 'caption', { max: 2000 }),
		link: field(data, 'link', { max: 2048, trim: true }),
		audience: audience === 'public' || audience === 'followers' ? audience : ''
	};
}

export const load: PageServerLoad = async (event) => {
	const viewer = requireViewer(event.locals.viewer, event.url);
	const secret = secretFor(event);
	if (!isUuid(event.params.id)) error(404, 'Not found');
	const sharing = await call<SharingOut>(createRequestApi(), 'getJumpSharing', {
		bearer: secret,
		id: event.params.id
	});
	if (!sharing.ok) {
		if (sharing.reason === 'not_found') error(404, 'Not found');
		error(503, 'Sharing is unavailable right now. Try again later.');
	}
	return { emailVerified: viewer.emailVerified, sharing: sharing.value };
};

export const actions: Actions = {
	// Nothing is sent: the page shows exactly what would be shared.
	preview: async (event) => {
		secretFor(event);
		const data = await event.request.formData();
		const chosen = choices(data);
		if (!chosen.audience) return fail(400, { form: 'share', error: 'audience_invalid', chosen });
		// The page reloads the jump; the preview shows, and Publish sends, that version.
		return { form: 'preview', chosen };
	},

	publish: async (event) => {
		const secret = secretFor(event);
		const data = await event.request.formData();
		const chosen = choices(data);
		const based = version(data);
		if (!chosen.audience || based === null) {
			return fail(400, { form: 'share', error: 'audience_invalid', chosen });
		}
		const result = await call<PostOut>(createRequestApi(), 'publishJump', {
			bearer: secret,
			id: event.params.id,
			body: {
				jump_version: based,
				shares: chosen.shares,
				caption: chosen.caption || null,
				link: chosen.link || null,
				audience: chosen.audience
			}
		});
		if (!result.ok)
			return fail(failStatus(result), { form: 'share', error: result.reason, chosen });
		redirect(303, `/jumps/${event.params.id}/share?published=1`);
	},

	audience: async (event) => {
		const secret = secretFor(event);
		const data = await event.request.formData();
		const post = field(data, 'post', { max: 36 });
		const audience = field(data, 'audience', { max: 16 });
		const v = version(data);
		if (!isUuid(post) || v === null) return fail(400, { form: 'audience', error: 'not_found' });
		const result = await call<null>(createRequestApi(), 'changePostAudience', {
			bearer: secret,
			id: post,
			body: { audience, version: v }
		});
		if (!result.ok) return fail(failStatus(result), { form: 'audience', error: result.reason });
		redirect(303, `/jumps/${event.params.id}/share?changed=1`);
	},

	unpublish: async (event) => {
		const secret = secretFor(event);
		const data = await event.request.formData();
		if (field(data, 'confirm', { max: 4 }) !== 'on') {
			return fail(400, { form: 'unpublish', error: 'confirm_unpublish' });
		}
		const post = field(data, 'post', { max: 36 });
		const v = version(data);
		if (!isUuid(post)) return fail(400, { form: 'unpublish', error: 'not_found' });
		const result = await call<null>(createRequestApi(), 'unpublishPost', {
			bearer: secret,
			id: post,
			query: { version: v ? String(v) : undefined }
		});
		if (!result.ok) return fail(failStatus(result), { form: 'unpublish', error: result.reason });
		redirect(303, `/jumps/${event.params.id}/share?unpublished=1`);
	}
};
