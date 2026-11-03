import type { Handle, HandleServerError } from '@sveltejs/kit/hooks';
import { APP_ORIGIN } from '$app/env/private';
import { isUnsafeMethod, originAllowed } from '#lib/server/origin-check.ts';
import { isPrivateRoute, resolveViewer } from '#lib/server/viewer.ts';
import { signInPath } from '#lib/safe-return.ts';

const SECURITY_HEADERS: Record<string, string> = {
	// Dynamic HTML/data/errors are never shared-cached (architecture A3).
	'cache-control': 'no-store',
	'referrer-policy': 'same-origin',
	'x-content-type-options': 'nosniff',
	'permissions-policy': 'geolocation=(), camera=(), microphone=()'
};

function withSecurityHeaders(response: Response): Response {
	for (const [name, value] of Object.entries(SECURITY_HEADERS)) {
		response.headers.set(name, value);
	}
	return response;
}

export const handle: Handle = async ({ event, resolve }) => {
	if (
		isUnsafeMethod(event.request.method) &&
		!originAllowed(event.request.headers.get('origin'), APP_ORIGIN)
	) {
		return withSecurityHeaders(
			new Response('Cross-origin request refused', {
				status: 403,
				headers: { 'content-type': 'text/plain; charset=utf-8' }
			})
		);
	}

	const resolution = await resolveViewer(event);
	event.locals.viewer = resolution.viewer;
	event.locals.sessionUnconfirmed = resolution.unconfirmed;

	// Deny anonymous private requests before any load runs. Page server loads run in
	// parallel with layout loads, so the (private) layout guard alone cannot stop a
	// page load; this hook is the enforcement point for both HTML and data requests.
	if (isPrivateRoute(event.route.id) && !event.locals.viewer) {
		const location = signInPath(event.url);
		return withSecurityHeaders(
			event.isDataRequest
				? // SvelteKit's client-navigation redirect payload (asserted by shell.e2e.ts).
					Response.json({ type: 'redirect', location })
				: new Response(null, { status: 303, headers: { location } })
		);
	}

	const response = withSecurityHeaders(await resolve(event));
	// Set centrally so every account-changing response, including action redirects, carries it.
	if (event.locals.clearSiteCache) response.headers.set('clear-site-data', '"cache"');
	return response;
};

export const handleError: HandleServerError = ({ kind, error }) => {
	if (kind === 'unknown') {
		// Log the error class only; messages may contain upstream details.
		console.error('Unhandled server error:', error instanceof Error ? error.name : typeof error);
		return { message: 'Something went wrong on our side.' };
	}
	// App/framework errors keep SvelteKit's status and safe message.
};
