/**
 * Shared loading for the jump pages (#153): the chosen location, the location
 * picker and the viewer's gear. Reads only; the API remains the authority.
 */
import type {
	ComponentSummaryOut,
	LoadingContextOut,
	PlaceOut,
	VenueOut
} from '#lib/contracts/index.ts';
import { countryName } from '#lib/countries.ts';
import type { ApiTransport } from './api/transport.ts';
import { isUuid } from './api/transport.ts';
import { getVenue, listPlaces, searchVenues } from './directory.ts';
import { call, isList } from './maintenance.ts';

export type Chosen = {
	name: string;
	detail: string;
	venueId: string | null;
	placeId: string | null;
};

/** The location named by `?venue=` / `?place=`, or null if none or not usable. */
export async function chosenLocation(
	api: ApiTransport,
	secret: string,
	url: URL,
	places: PlaceOut[]
): Promise<Chosen | null> {
	const venue = url.searchParams.get('venue');
	const place = url.searchParams.get('place');
	if (isUuid(venue)) {
		const found = await getVenue(api, venue);
		if (!found.ok) return null;
		const v = found.value.venue;
		return {
			name: v.name,
			detail: `${v.locality ? `${v.locality}, ` : ''}${countryName(v.country)}${v.status === 'closed' ? ' · closed' : ''}`,
			venueId: v.id,
			placeId: null
		};
	}
	if (isUuid(place)) {
		const p = places.find((item) => item.id === place);
		return p
			? {
					name: p.name,
					detail: `${countryName(p.country)} · private place`,
					venueId: null,
					placeId: p.id
				}
			: null;
	}
	return null;
}

export async function pickerData(api: ApiTransport, url: URL) {
	const q = (url.searchParams.get('q') ?? '').trim().slice(0, 80);
	let matches: { ok: true; items: VenueOut[] } | { ok: false } | null = null;
	if (q) {
		const found = await searchVenues(api, { q, limit: 20 });
		matches = found.ok ? { ok: true, items: found.value.items } : { ok: false };
	}
	return { q, matches };
}

export async function placesFor(api: ApiTransport, secret: string): Promise<PlaceOut[] | null> {
	const places = await listPlaces(api, secret);
	return places.ok ? places.value : null;
}

/** Active components, plus any already linked to this jump even if archived. */
export async function gearFor(
	api: ApiTransport,
	secret: string,
	linked: {
		id: string;
		label: string;
		kind: string;
		archived: boolean;
		canopy_size_sqft?: number | null;
	}[] = []
) {
	const active = await call<ComponentSummaryOut[]>(
		api,
		'listComponents',
		{ bearer: secret },
		isList
	);
	type Item = {
		id: string;
		label: string;
		kind: string;
		archived: boolean;
		canopySize: number | null;
	};
	const items: Item[] = active.ok
		? active.value.map((s) => ({
				id: s.component.id,
				label: s.component.label,
				kind: s.component.kind,
				archived: false,
				canopySize: s.component.canopy_size_sqft ?? null
			}))
		: [];
	for (const item of linked) {
		if (items.some((i) => i.id === item.id)) continue;
		items.push({
			id: item.id,
			label: item.label,
			kind: item.kind,
			archived: item.archived,
			canopySize: item.canopy_size_sqft ?? null
		});
	}
	return { ok: active.ok, items };
}

/** The usual exit weight and the highest wing loading of the other jumps (one call). */
export async function loadingFor(
	api: ApiTransport,
	secret: string,
	exclude?: string
): Promise<{ usualGrams: number | null; unit: 'kg' | 'lb'; highest: number | null } | null> {
	const found = await call<LoadingContextOut>(api, 'getWingLoadingContext', {
		bearer: secret,
		query: { exclude }
	});
	if (!found.ok) return null;
	return {
		usualGrams: found.value.exit_weight?.grams ?? null,
		unit: found.value.unit,
		highest: found.value.highest
	};
}

export type RecentLocation = {
	kind: 'venue' | 'place';
	id: string;
	name: string;
	country: string | null;
};

/**
 * Where the viewer jumped most recently, newest first and without repeats: the
 * one-tap choices at the top of the picker. Empty on any error; the picker still works.
 */
export async function recentLocations(
	api: ApiTransport,
	secret: string,
	limit = 4
): Promise<RecentLocation[]> {
	const page = await call<{ items: unknown[] }>(
		api,
		'listJumps',
		{ bearer: secret, query: { limit: '30' } },
		(v): v is { items: unknown[] } =>
			typeof v === 'object' && v !== null && Array.isArray((v as { items?: unknown }).items)
	);
	if (!page.ok) return [];
	const seen = new Set<string>();
	const out: RecentLocation[] = [];
	for (const item of page.value.items) {
		const loc = (item as { location?: Record<string, unknown> }).location;
		if (!loc || (loc.kind !== 'venue' && loc.kind !== 'place')) continue;
		if (typeof loc.id !== 'string' || typeof loc.name !== 'string' || loc.closed === true) continue;
		const key = `${loc.kind}:${loc.id}`;
		if (seen.has(key)) continue;
		seen.add(key);
		out.push({
			kind: loc.kind,
			id: loc.id,
			name: loc.name,
			country: typeof loc.country === 'string' ? loc.country : null
		});
		if (out.length === limit) break;
	}
	return out;
}
