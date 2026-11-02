const PLACEHOLDER_ORIGIN = 'https://return.invalid';

/**
 * Returns a same-origin relative path (path + query) or `null`.
 * Rejects absolute/protocol-relative URLs, backslash tricks and control characters.
 */
export function safeReturnPath(raw: string | null | undefined): string | null {
	if (!raw || raw.length > 512) return null;
	if (!raw.startsWith('/') || raw.startsWith('//')) return null;
	// eslint-disable-next-line no-control-regex
	if (/[\u0000-\u001f\u007f\\]/.test(raw)) return null;

	let url: URL;
	try {
		url = new URL(raw, PLACEHOLDER_ORIGIN);
	} catch {
		return null;
	}
	if (url.origin !== PLACEHOLDER_ORIGIN) return null;
	return `${url.pathname}${url.search}`;
}

export function signInPath(from: URL): string {
	const target = safeReturnPath(`${from.pathname}${from.search}`);
	return target && target !== '/' ? `/sign-in?returnTo=${encodeURIComponent(target)}` : '/sign-in';
}
