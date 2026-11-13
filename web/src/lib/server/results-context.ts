/**
 * Keeps an event page's board search ("Back to results") through sign-in when it is too long
 * for the sign-in return path (512 characters, decoded: safe-return.ts).
 *
 * A short context travels in the URL as `results=` (listing-filters.ts eventHref). A longer
 * one is kept in a short-lived cookie scoped to that event's path, and the return path carries
 * only `ctx=<random id>`. On the way back the cookie is used only when its id matches, and the
 * value is validated again as a board search (resultsPath), so a stale, foreign, malformed or
 * expired cookie just means no "Back to results". The cookie holds only the board query
 * (filters and page cursor) that was already in the page's own address; no account data.
 * Server-only, so it works without JavaScript.
 */
import type { Cookies } from '@sveltejs/kit';
import { eventHref, resultsPath } from '#lib/listing-filters.ts';

const COOKIE = 'board_context';
const MAX_AGE_SECONDS = 30 * 60;
const ID = /^[A-Za-z0-9_-]{16}$/;

function newId(): string {
	const bytes = crypto.getRandomValues(new Uint8Array(12));
	return Buffer.from(bytes).toString('base64url');
}

function cookiePath(eventId: string): string {
	return `/events/${eventId}`;
}

/** The board search an event page shows "Back to results" for: from `results`, else `ctx`. */
export function recallResults(cookies: Cookies, url: URL): string | null {
	const direct = resultsPath(url.searchParams.get('results'));
	if (direct) return direct;
	const id = url.searchParams.get('ctx');
	if (!id || !ID.test(id)) return null;
	const stored = cookies.get(COOKIE);
	if (!stored) return null; // expired or never set here
	const separator = stored.indexOf('~');
	if (separator < 0 || stored.slice(0, separator) !== id) return null;
	return resultsPath(stored.slice(separator + 1));
}

export interface SignInReturns {
	/** Back to the event with the "sign in to save" intent. */
	save: string;
	/** Back to the event as it was (the header's Sign in). */
	plain: string;
}

/**
 * Return paths for signing in from an event page, keeping `results`. When it does not fit in
 * the URL, it is stored in the cookie and the paths carry its id instead.
 */
export function signInReturns(
	cookies: Cookies,
	eventId: string,
	results: string | null,
	/** As for the session cookie (session.ts cookieSecure). */
	secure: boolean
): SignInReturns {
	const save = eventHref(eventId, { save: true, results });
	const plain = eventHref(eventId, { results });
	if (!results || save.includes('results=')) return { save, plain };

	const id = newId();
	cookies.set(COOKIE, `${id}~${results}`, {
		path: cookiePath(eventId),
		httpOnly: true,
		secure,
		sameSite: 'lax',
		maxAge: MAX_AGE_SECONDS
	});
	const base = cookiePath(eventId);
	return { save: `${base}?save=1&ctx=${id}`, plain: `${base}?ctx=${id}` };
}
