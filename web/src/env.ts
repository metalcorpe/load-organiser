import { defineEnvVars } from '@sveltejs/kit/env';
import { parseApiOrigin } from './lib/server/api/origin.ts';

export const variables = defineEnvVars({
	API_ORIGIN: {
		description:
			'Fixed FastAPI origin used by server-only loads (e.g. https://api.example.org). Private; never sent to browsers. Unset means API calls fail closed.',
		schema: parseApiOrigin
	}
});
