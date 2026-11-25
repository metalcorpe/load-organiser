import type { Viewer } from './identity.ts';

/**
 * A confirmed session, remembered for a short time so a tab switch does not wait for the API
 * to confirm it again (owner request, 2026-11-25: faster tab switching).
 *
 * The trade-off, accepted by the owner: a session signed out, deleted or demoted elsewhere is
 * still shown as signed in by this server for up to TTL_MS. The API still checks the session
 * and the role on every call it serves, so no private data or reviewer action is reachable
 * with a session the API has ended. Only plain page and data loads use it (`cacheable`); every
 * form post asks the API and forgets the entry first, and the session pages always ask.
 *
 * Memory of one Worker isolate: not shared, and gone whenever Cloudflare recycles the isolate.
 * Entries are keyed by a SHA-256 digest of the secret, never the secret itself.
 */
export const TTL_MS = 30_000;
const MAX_ENTRIES = 500;

export class ViewerCache {
	readonly #entries = new Map<string, { viewer: Viewer; until: number }>();

	constructor(
		private readonly now: () => number = Date.now,
		private readonly max = MAX_ENTRIES
	) {}

	get(key: string): Viewer | undefined {
		const entry = this.#entries.get(key);
		if (!entry) return undefined;
		if (this.now() >= entry.until) {
			this.#entries.delete(key);
			return undefined;
		}
		return entry.viewer;
	}

	/** Never past the session's own expiry; a hit does not extend it. */
	remember(key: string, viewer: Viewer): void {
		const until = Math.min(this.now() + TTL_MS, Date.parse(viewer.sessionExpiresAt));
		this.#entries.delete(key);
		this.#entries.set(key, { viewer, until });
		while (this.#entries.size > this.max) {
			this.#entries.delete(this.#entries.keys().next().value as string);
		}
	}

	forget(key: string): void {
		this.#entries.delete(key);
	}
}

export const viewerCache = new ViewerCache();

export async function sessionKey(secret: string): Promise<string> {
	const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(secret));
	return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, '0')).join('');
}

/** Pages where the session itself changes: always asked of the API. */
const SESSION_PAGES = ['/sign-in', '/sign-out', '/register', '/verify-email', '/reset-password', '/forgot-password'];

export function cacheable(method: string, pathname: string): boolean {
	if (method !== 'GET' && method !== 'HEAD') return false;
	return !SESSION_PAGES.some((page) => pathname === page || pathname.startsWith(`${page}/`));
}
