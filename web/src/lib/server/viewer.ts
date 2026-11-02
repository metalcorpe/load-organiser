import { redirect, type RequestEvent } from '@sveltejs/kit';
import { signInPath } from '#lib/safe-return.ts';
import { createRequestApi } from './api/client.ts';
import { getViewer, type Viewer } from './identity.ts';
import { clearSession, readSessionSecret } from './session.ts';

export type { Viewer } from './identity.ts';

export interface ViewerResolution {
	viewer: Viewer | null;
	/** A session cookie exists but the API could not confirm it (unreachable/timeout). */
	unconfirmed: boolean;
}

/**
 * Resolves the viewer for this request only, by asking the API to validate the
 * cookie's opaque secret. A rejected secret clears the cookie; an unreachable
 * API keeps it (the session may still be valid) but renders as signed out.
 */
export async function resolveViewer(
	event: Pick<RequestEvent, 'cookies'>
): Promise<ViewerResolution> {
	const secret = readSessionSecret(event.cookies);
	if (!secret) return { viewer: null, unconfirmed: false };

	const outcome = await getViewer(createRequestApi(), secret);
	if (outcome.ok) return { viewer: outcome.value, unconfirmed: false };
	if (outcome.reason === 'not_authenticated') {
		clearSession(event.cookies);
		return { viewer: null, unconfirmed: false };
	}
	return { viewer: null, unconfirmed: true };
}

export function isPrivateRoute(routeId: string | null): boolean {
	return routeId !== null && routeId.startsWith('/(private)');
}

/** Call from every private server load/endpoint before reading private data. */
export function requireViewer(viewer: Viewer | null, url: URL): Viewer {
	if (!viewer) redirect(303, signInPath(url));
	return viewer;
}
