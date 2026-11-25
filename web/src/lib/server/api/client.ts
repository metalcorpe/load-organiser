import { API_ORIGIN, API_PROXY_KEY } from '$app/env/private';
import { getRequestEvent } from '$app/server';
import { isRedirect, redirect } from '@sveltejs/kit';
import { signInPath } from '#lib/safe-return.ts';
import { clearSession } from '../session.ts';
import { viewerCache } from '../viewer-cache.ts';
import { createApiTransport, type ApiTransport } from './transport.ts';

/**
 * Creates a transport for the current request only. Uses the platform `fetch`
 * rather than `event.fetch`, because SvelteKit's `event.fetch` forwards the
 * browser's cookie/authorization headers to same-site API origins; the API
 * must only ever receive credentials SvelteKit sets explicitly (#145).
 */
export function createRequestApi(): ApiTransport {
	const transport = createApiTransport({
		fetch: (input, init) => fetch(input, init),
		origin: API_ORIGIN,
		proxyKey: API_PROXY_KEY,
		// Collected for this request's Server-Timing header (hooks.server.ts).
		onTiming: (operation, ms) => {
			try {
				getRequestEvent().locals.timings?.push({ name: operation, ms });
			} catch {
				// Outside a request (tests, scripts): nothing to report to.
			}
		}
	});
	return {
		async request(operation, options) {
			const result = await transport.request(operation, options);
			if (result.kind === 'response' && result.status === 401 && options?.bearer) endStaleSession();
			return result;
		}
	};
}

/**
 * The API refused a session this request took from the viewer cache: it was ended elsewhere
 * (sign-out everywhere, a password reset, account deletion) within the last 30 seconds. Forget
 * it, clear the cookie and go to sign-in, as an unremembered session would have.
 */
function endStaleSession(): void {
	try {
		const event = getRequestEvent();
		const key = event.locals.reusedSessionKey;
		if (!key) return;
		event.locals.reusedSessionKey = undefined;
		viewerCache.forget(key);
		clearSession(event.cookies);
		redirect(303, signInPath(event.url));
	} catch (error) {
		if (isRedirect(error)) throw error;
		// Outside a request: nothing to end.
	}
}
