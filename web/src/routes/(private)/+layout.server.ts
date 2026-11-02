import { requireViewer } from '#lib/server/viewer.ts';
import type { LayoutServerLoad } from './$types';

// Required: a server load makes client-side navigation into the group request
// __data.json, which hooks.server.ts then denies. Without it, the client would
// render private pages without contacting the server. The guard here is defence
// in depth; private page loads must still call requireViewer themselves.
export const load: LayoutServerLoad = ({ locals, url }) => {
	requireViewer(locals.viewer, url);
	return {};
};
