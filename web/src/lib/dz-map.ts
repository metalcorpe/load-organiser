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
/** Leaflet's credit as a plain link (its default prefix adds a flag icon). */
export const ATTRIBUTION_PREFIX = '<a href="https://leafletjs.com">Leaflet</a>';

export interface MapPoint {
	id: string;
	name: string;
	/** "Locality, Country", already formatted for reading. */
	place: string;
	lat: number;
	lon: number;
	closed: boolean;
}

export type Bounds = [[number, number], [number, number]];

/** The value at fraction `q` (0..1) of sorted numbers, by nearest rank. */
function quantile(sorted: number[], q: number): number {
	return sorted[Math.min(sorted.length - 1, Math.max(0, Math.round(q * (sorted.length - 1))))];
}

/**
 * Where the map starts. A search or country shows every match. Unfiltered, the far-off
 * dropzones (Iceland, the Canaries, eastern Türkiye...) would zoom the whole continent out, so
 * the view fits the central 90% of points by latitude and by longitude; the rest stay a pan
 * away. Null when there is nothing to fit.
 */
export function startBounds(points: MapPoint[], options: { filtered: boolean }): Bounds | null {
	if (points.length === 0) return null;
	const lats = points.map((p) => p.lat).sort((a, b) => a - b);
	const lons = points.map((p) => p.lon).sort((a, b) => a - b);
	const trim = !options.filtered && points.length >= 20 ? 0.05 : 0;
	return [
		[quantile(lats, trim), quantile(lons, trim)],
		[quantile(lats, 1 - trim), quantile(lons, 1 - trim)]
	];
}

/** A link to the point on openstreetmap.org, zoomed to the airfield. Nothing is embedded. */
export function osmLink(latitude: number, longitude: number): string {
	const lat = String(latitude);
	const lon = String(longitude);
	return `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=13/${lat}/${lon}`;
}

/**
 * "42.25857° N, 3.13700° W": hemispheres in words rather than signs. A value that rounds to
 * zero is the equator or the prime meridian, "0.00000°", with no hemisphere.
 */
export function formatCoordinates(latitude: number, longitude: number): string {
	const part = (value: number, positive: string, negative: string) => {
		const digits = Math.abs(value).toFixed(5);
		if (Number(digits) === 0) return `${digits}°`;
		return `${digits}° ${value < 0 ? negative : positive}`;
	};
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
