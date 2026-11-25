import { API_ORIGIN, API_PROXY_KEY } from '$app/env/private';
import { getRequestEvent } from '$app/server';
import { createApiTransport, type ApiTransport } from './transport.ts';

/**
 * Creates a transport for the current request only. Uses the platform `fetch`
 * rather than `event.fetch`, because SvelteKit's `event.fetch` forwards the
 * browser's cookie/authorization headers to same-site API origins; the API
 * must only ever receive credentials SvelteKit sets explicitly (#145).
 */
export function createRequestApi(): ApiTransport {
	return createApiTransport({
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
}
