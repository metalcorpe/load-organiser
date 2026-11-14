/**
 * Plain helpers for the dropzone map (`/dz?view=map`) and the detail page's map link.
 * No Leaflet here: the map library is loaded only after the visitor chooses to show the map.
 */

export type DzView = 'list' | 'map';

export function dzView(raw: string | null): DzView {
	return raw === 'map' ? 'map' : 'list';
}

/** The directory address for these filters, as a shareable GET link. */
export function dzHref(options: {
	q?: string;
	country?: string;
	view?: DzView;
	cursor?: string;
}): string {
	const params = new URLSearchParams();
	if (options.q) params.set('q', options.q);
	if (options.country) params.set('country', options.country);
	if (options.view === 'map') params.set('view', 'map');
	if (options.cursor) params.set('cursor', options.cursor);
	const search = params.toString();
	return search ? `/dz?${search}` : '/dz';
}

/** OpenStreetMap's tile servers, the only third party the map contacts (CSP img-src). */
export const TILE_URL = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
export const TILE_REFERRER_POLICY = 'strict-origin';
export const TILE_ATTRIBUTION =
	'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

/** A link to the point on openstreetmap.org, zoomed to the airfield. Nothing is embedded. */
export function osmLink(latitude: number, longitude: number): string {
	const lat = String(latitude);
	const lon = String(longitude);
	return `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=13/${lat}/${lon}`;
}

/** "42.25857° N, 3.13700° W": hemispheres in words rather than signs. */
export function formatCoordinates(latitude: number, longitude: number): string {
	const part = (value: number, positive: string, negative: string) =>
		`${Math.abs(value).toFixed(5)}° ${value < 0 ? negative : positive}`;
	return `${part(latitude, 'N', 'S')}, ${part(longitude, 'E', 'W')}`;
}

/**
 * The visitor's choice to load map tiles, kept for this browser session only. Storage can be
 * missing or throw (private modes, blocked site data): then the map simply asks again.
 */
const CHOICE_KEY = 'organiser.dz-map';

export function mapChosen(storage: () => Storage | undefined): boolean {
	try {
		return storage()?.getItem(CHOICE_KEY) === 'shown';
	} catch {
		return false;
	}
}

export function rememberMapChoice(storage: () => Storage | undefined): void {
	try {
		storage()?.setItem(CHOICE_KEY, 'shown');
	} catch {
		// Not remembered; the map is still shown for this page.
	}
}
