import { defineEnvVars } from '@sveltejs/kit/env';
import { parseApiOrigin, parseAppOrigin } from './lib/server/api/origin.ts';
import { parseCookieMode, parseProxyKey } from './lib/server/session-config.ts';

export const variables = defineEnvVars({
	API_ORIGIN: {
		description:
			'Fixed FastAPI origin used by server-only loads (e.g. https://api.example.org). Private; never sent to browsers. Unset means API calls fail closed.',
		schema: parseApiOrigin
	},
	APP_ORIGIN: {
		description:
			'Exact public origin of this web app. Unsafe requests (POST/PUT/PATCH/DELETE) must carry it as Origin. Unset means they are refused.',
		schema: parseAppOrigin
	},
	SESSION_COOKIE_MODE: {
		description:
			"'secure' (default): __Host- Secure HttpOnly cookie. 'localhost-dev': non-Secure cookie for a loopback APP_ORIGIN only.",
		schema: parseCookieMode
	},
	API_PROXY_KEY: {
		description:
			'Shared secret (32+ chars) that lets the API trust the client address this server forwards for throttling. Private.',
		schema: parseProxyKey
	}
});
