import { createRequestApi } from '#lib/server/api/client.ts';
import { fetchHealth } from '#lib/server/api/health.ts';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async () => {
	return { health: await fetchHealth(createRequestApi()) };
};
