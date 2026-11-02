import { redirect } from '@sveltejs/kit';
import { signInPath } from '#lib/safe-return.ts';

/** Minimal request-local identity for rendering. Real sessions arrive in #145. */
export interface Viewer {
	id: string;
}

/**
 * #144 has no account/session implementation, so every request is anonymous.
 * #145 replaces this with backend session validation; no cookie is trusted here.
 */
export function resolveViewer(): Viewer | null {
	return null;
}

export function isPrivateRoute(routeId: string | null): boolean {
	return routeId !== null && routeId.startsWith('/(private)');
}

/** Call from every private server load/endpoint before reading private data. */
export function requireViewer(viewer: Viewer | null, url: URL): Viewer {
	if (!viewer) redirect(303, signInPath(url));
	return viewer;
}
