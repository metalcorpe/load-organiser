/**
 * Exact Origin check for unsafe methods (architecture A5). Runs in addition to
 * SvelteKit's own form CSRF check and also covers JSON routes, login and logout.
 */
const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS']);

export function isUnsafeMethod(method: string): boolean {
	return !SAFE_METHODS.has(method.toUpperCase());
}

/** Absent, `null` or mismatched origins are refused; so is everything when unconfigured. */
export function originAllowed(origin: string | null, appOrigin: string | undefined): boolean {
	return appOrigin !== undefined && origin !== null && origin === appOrigin;
}
