/**
 * Typed directory calls over the server-only transport (#148).
 *
 * Responses are shape-checked before reaching pages; failures are reduced to a
 * small reason code. Upstream bodies and URLs are never passed through.
 */
import type { PlaceOut, VenueOut, VenuePointOut, VenueRefOut } from '#lib/contracts/index.ts';
import type { ApiTransport, OperationId, RequestOptions } from './api/transport.ts';

export type DirectoryReason =
	| 'not_found'
	| 'not_authenticated'
	| 'email_unverified'
	| 'venue_not_listed'
	| 'place_limit_reached'
	| 'name_required'
	| 'name_too_long'
	| 'country_invalid'
	| 'cursor_invalid'
	| 'invalid_input'
	/** Timed out: a write may or may not have completed. */
	| 'uncertain'
	| 'unavailable';

export type DirectoryOutcome<T> = { ok: true; value: T } | { ok: false; reason: DirectoryReason };

const KNOWN = new Set<string>([
	'not_found',
	'not_authenticated',
	'email_unverified',
	'venue_not_listed',
	'place_limit_reached',
	'name_required',
	'name_too_long',
	'country_invalid',
	'cursor_invalid'
]);

export interface VenuePage {
	items: VenueOut[];
	nextCursor: string | null;
}

export interface VenuePoints {
	points: VenuePointOut[];
	/** More venues match than one page holds; the map shows the first page only. */
	truncated: boolean;
}

export interface VenueDetail {
	venue: VenueOut;
	replacedId: string | null;
}

async function call(
	api: ApiTransport,
	operation: OperationId,
	options: RequestOptions = {}
): Promise<DirectoryOutcome<unknown>> {
	const result = await api.request(operation, options);
	if (result.kind === 'invalid_request') return { ok: false, reason: 'not_found' };
	if (result.kind === 'timeout') return { ok: false, reason: 'uncertain' };
	if (result.kind !== 'response') return { ok: false, reason: 'unavailable' };
	if (result.status >= 200 && result.status < 300) return { ok: true, value: result.body };
	const detail =
		typeof result.body === 'object' && result.body !== null && 'detail' in result.body
			? (result.body as { detail: unknown }).detail
			: undefined;
	if (typeof detail === 'string' && KNOWN.has(detail)) {
		return { ok: false, reason: detail as DirectoryReason };
	}
	if (result.status === 401) return { ok: false, reason: 'not_authenticated' };
	if (result.status === 404) return { ok: false, reason: 'not_found' };
	if (result.status === 422 || result.status === 400) return { ok: false, reason: 'invalid_input' };
	return { ok: false, reason: 'unavailable' };
}

const isRecord = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null;
const isString = (v: unknown): v is string => typeof v === 'string';
const isNullableString = (v: unknown) => v === null || typeof v === 'string';
const isNullableNumber = (v: unknown) => v === null || (typeof v === 'number' && Number.isFinite(v));

export function isVenueOut(value: unknown): value is VenueOut {
	if (!isRecord(value)) return false;
	return (
		isString(value.id) &&
		isString(value.name) &&
		isString(value.country) &&
		isNullableString(value.locality) &&
		isNullableNumber(value.latitude) &&
		isNullableNumber(value.longitude) &&
		(value.status === 'listed' || value.status === 'closed') &&
		Array.isArray(value.aliases) &&
		value.aliases.every(
			(a) =>
				isRecord(a) &&
				isString(a.name) &&
				(a.kind === 'alternate' || a.kind === 'former' || a.kind === 'merged')
		) &&
		isString(value.source_url) &&
		/^https?:\/\//i.test(value.source_url) &&
		isNullableString(value.source_note) &&
		isString(value.checked_on)
	);
}

const within = (v: unknown, limit: number) =>
	typeof v === 'number' && Number.isFinite(v) && Math.abs(v) <= limit;

export function isVenuePoint(value: unknown): value is VenuePointOut {
	return (
		isRecord(value) &&
		isString(value.id) &&
		isString(value.name) &&
		isNullableString(value.locality) &&
		isString(value.country) &&
		within(value.lat, 90) &&
		within(value.lon, 180) &&
		typeof value.closed === 'boolean'
	);
}

function isVenueRef(value: unknown): value is VenueRefOut {
	return (
		isRecord(value) &&
		isString(value.id) &&
		isString(value.name) &&
		isString(value.country) &&
		(value.status === 'listed' || value.status === 'closed')
	);
}

export function isPlaceOut(value: unknown): value is PlaceOut {
	return (
		isRecord(value) &&
		isString(value.id) &&
		isString(value.name) &&
		isString(value.country) &&
		(value.venue === null || isVenueRef(value.venue)) &&
		isString(value.updated_at)
	);
}

function invalid<T>(): DirectoryOutcome<T> {
	return { ok: false, reason: 'unavailable' };
}

export async function searchVenues(
	api: ApiTransport,
	query: { q?: string; country?: string; cursor?: string; limit?: number }
): Promise<DirectoryOutcome<VenuePage>> {
	const outcome = await call(api, 'searchVenues', {
		query: {
			q: query.q,
			country: query.country,
			cursor: query.cursor,
			limit: query.limit === undefined ? undefined : String(query.limit)
		}
	});
	if (!outcome.ok) return outcome;
	const body = outcome.value;
	if (
		!isRecord(body) ||
		!Array.isArray(body.items) ||
		!body.items.every(isVenueOut) ||
		!isNullableString(body.next_cursor)
	) {
		return invalid();
	}
	return { ok: true, value: { items: body.items, nextCursor: body.next_cursor as string | null } };
}

/** One page of map points (the API's maximum, 1,000) for the same filters as the list. */
export async function listVenuePoints(
	api: ApiTransport,
	query: { q?: string; country?: string }
): Promise<DirectoryOutcome<VenuePoints>> {
	const outcome = await call(api, 'listVenuePoints', {
		query: { q: query.q, country: query.country, limit: '1000' }
	});
	if (!outcome.ok) return outcome;
	const body = outcome.value;
	if (
		!isRecord(body) ||
		!Array.isArray(body.items) ||
		!body.items.every(isVenuePoint) ||
		!isNullableString(body.next_cursor)
	) {
		return invalid();
	}
	return { ok: true, value: { points: body.items, truncated: body.next_cursor !== null } };
}

export async function getVenue(
	api: ApiTransport,
	id: string
): Promise<DirectoryOutcome<VenueDetail>> {
	const outcome = await call(api, 'getVenue', { id });
	if (!outcome.ok) return outcome;
	const body = outcome.value;
	if (!isRecord(body) || !isVenueOut(body.venue) || !isNullableString(body.replaced_id)) {
		return invalid();
	}
	return {
		ok: true,
		value: { venue: body.venue, replacedId: body.replaced_id as string | null }
	};
}

export async function listPlaces(
	api: ApiTransport,
	secret: string
): Promise<DirectoryOutcome<PlaceOut[]>> {
	const outcome = await call(api, 'listPlaces', { bearer: secret });
	if (!outcome.ok) return outcome;
	return Array.isArray(outcome.value) && outcome.value.every(isPlaceOut)
		? { ok: true, value: outcome.value }
		: invalid();
}

async function placeResult(outcome: DirectoryOutcome<unknown>): Promise<DirectoryOutcome<PlaceOut>> {
	if (!outcome.ok) return outcome;
	return isPlaceOut(outcome.value) ? { ok: true, value: outcome.value } : invalid();
}

export async function createPlace(
	api: ApiTransport,
	secret: string,
	input: { name: string; country: string }
): Promise<DirectoryOutcome<PlaceOut>> {
	return placeResult(await call(api, 'createPlace', { bearer: secret, body: input }));
}

export async function updatePlace(
	api: ApiTransport,
	secret: string,
	id: string,
	changes: { name?: string; country?: string; venue_id?: string | null }
): Promise<DirectoryOutcome<PlaceOut>> {
	return placeResult(await call(api, 'updatePlace', { bearer: secret, id, body: changes }));
}

export async function deletePlace(
	api: ApiTransport,
	secret: string,
	id: string
): Promise<DirectoryOutcome<null>> {
	const outcome = await call(api, 'deletePlace', { bearer: secret, id });
	return outcome.ok ? { ok: true, value: null } : outcome;
}
