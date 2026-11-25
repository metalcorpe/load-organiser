import { redirect, type RequestEvent } from '@sveltejs/kit';
import { signInPath } from '#lib/safe-return.ts';
import { createRequestApi } from './api/client.ts';
import { getViewer, type Viewer } from './identity.ts';
import { clearSession, readSessionSecret } from './session.ts';
import { cacheable, sessionKey, viewerCache } from './viewer-cache.ts';

export type { Viewer } from './identity.ts';

export interface ViewerResolution {
	viewer: Viewer | null;
	/** A session cookie exists but the API could not confirm it (unreachable/timeout). */
	unconfirmed: boolean;
	/** The session digest, when a remembered confirmation was reused (viewer-cache.ts). */
	reusedKey?: string;
}

/**
 * Resolves the viewer for this request only, by asking the API to validate the
 * cookie's opaque secret. A rejected secret clears the cookie; an unreachable
 * API keeps it (the session may still be valid) but renders as signed out.
 *
 * A plain page or data load may reuse a confirmation from the last 30 seconds
 * (viewer-cache.ts); a form post or a session page always asks the API, and
 * forgets the remembered confirmation first, since it may change the session.
 */
export async function resolveViewer(
	event: Pick<RequestEvent, 'cookies' | 'request' | 'url'>
): Promise<ViewerResolution> {
	const secret = readSessionSecret(event.cookies);
	if (!secret) return { viewer: null, unconfirmed: false };

	const key = await sessionKey(secret);
	const reuse = cacheable(event.request.method, event.url.pathname);
	if (reuse) {
		const remembered = viewerCache.get(key);
		if (remembered) return { viewer: remembered, unconfirmed: false, reusedKey: key };
	} else {
		viewerCache.forget(key);
	}

	const outcome = await getViewer(createRequestApi(), secret);
	if (outcome.ok) {
		if (reuse) viewerCache.remember(key, outcome.value);
		return { viewer: outcome.value, unconfirmed: false };
	}
	viewerCache.forget(key);
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
