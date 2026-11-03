import { error, redirect } from '@sveltejs/kit';
import { readSessionSecret } from './session.ts';
import { requireViewer, type Viewer } from './viewer.ts';

/**
 * Reviewer pages: signed in and holding the reviewer role. Others get a plain 404
 * so the tools are not advertised; the API independently enforces the role.
 */
export function requireReviewer(event: {
	locals: { viewer: Viewer | null };
	url: URL;
	cookies: Parameters<typeof readSessionSecret>[0];
}): string {
	const viewer = requireViewer(event.locals.viewer, event.url);
	if (!viewer.reviewer) error(404, 'Not found');
	const secret = readSessionSecret(event.cookies);
	if (!secret) redirect(303, '/sign-in');
	return secret;
}
