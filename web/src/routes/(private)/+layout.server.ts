import { requireViewer } from '#lib/server/viewer.ts';
import type { LayoutServerLoad } from './$types';

// Runs on client-side navigation into the group too, so anonymous data
// requests are redirected before any private page renders.
export const load: LayoutServerLoad = ({ locals, url }) => {
	requireViewer(locals.viewer, url);
	return {};
};
