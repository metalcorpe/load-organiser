const LOOPBACK_HOSTS = new Set(['127.0.0.1', 'localhost', '[::1]']);

/**
 * Validates the single fixed FastAPI origin the web server may call.
 * Returns `undefined` when unset (requests then fail closed as `not_configured`).
 * Plain http is only accepted for loopback hosts used in isolated local runs.
 */
export function parseApiOrigin(raw: string | undefined): string | undefined {
	return parseOrigin('API_ORIGIN', raw);
}

/**
 * The exact public origin of this web application (e.g. https://app.example.org).
 * Unsafe requests must carry this Origin. Unset means unsafe requests are refused.
 */
export function parseAppOrigin(raw: string | undefined): string | undefined {
	return parseOrigin('APP_ORIGIN', raw);
}

export function isLoopbackOrigin(origin: string): boolean {
	return LOOPBACK_HOSTS.has(new URL(origin).hostname);
}

function parseOrigin(name: string, raw: string | undefined): string | undefined {
	if (raw === undefined || raw.trim() === '') return undefined;

	let url: URL;
	try {
		url = new URL(raw);
	} catch {
		throw new Error(`${name} must be an absolute http(s) origin`);
	}

	if (url.protocol !== 'https:' && url.protocol !== 'http:') {
		throw new Error(`${name} must use https`);
	}
	if (url.protocol === 'http:' && !LOOPBACK_HOSTS.has(url.hostname)) {
		throw new Error(`${name} must use https unless it is a loopback address`);
	}
	if (url.username || url.password) {
		throw new Error(`${name} must not contain credentials`);
	}
	if (url.pathname !== '/' || url.search || url.hash) {
		throw new Error(`${name} must be an origin without path, query or fragment`);
	}
	return url.origin;
}
