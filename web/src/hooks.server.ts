import type { Handle, HandleServerError } from '@sveltejs/kit/hooks';
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
	event.locals.viewer = resolveViewer();

	// Deny anonymous private page/endpoint requests before any load runs.
	// Client-side data requests are redirected by (private)/+layout.server.ts.
	if (isPrivateRoute(event.route.id) && !event.locals.viewer && !event.isDataRequest) {
		return withSecurityHeaders(
			new Response(null, { status: 303, headers: { location: signInPath(event.url) } })
		);
	}

	return withSecurityHeaders(await resolve(event));
};

export const handleError: HandleServerError = ({ kind, error }) => {
	if (kind === 'unknown') {
		// Log the error class only; messages may contain upstream details.
		console.error('Unhandled server error:', error instanceof Error ? error.name : typeof error);
		return { message: 'Something went wrong on our side.' };
	}
	// App/framework errors keep SvelteKit's status and safe message.
};
