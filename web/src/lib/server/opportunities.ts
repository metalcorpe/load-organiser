/**
 * Typed listing, saved-item and visit-plan calls over the server-only transport (#150).
 *
 * Responses are shape-checked before reaching pages; failures are reduced to a
 * small reason code. Upstream bodies and URLs are never passed through.
 */
import type {
	OpportunityOut,
	PlanOut,
	ProviderOut,
	SavedOut,
	SavedStateOut
} from '#lib/contracts/index.ts';
import { isCountryCode } from '#lib/countries.ts';
import { AUDIENCE_VALUES, CATEGORY_VALUES, DISCIPLINE_VALUES } from '#lib/listing-filters.ts';
import type { ApiTransport, OperationId, RequestOptions } from './api/transport.ts';

export type ListingReason =
	| 'not_found'
	| 'not_authenticated'
	| 'email_unverified'
	| 'saved_limit_reached'
	| 'plan_limit_reached'
	| 'title_required'
	| 'title_too_long'
	| 'note_too_long'
	| 'dates_required'
	| 'dates_out_of_order'
	| 'dates_span_too_long'
	| 'plan_link_conflict'
	| 'opportunity_unavailable'
	| 'venue_not_listed'
	| 'place_unknown'
	| 'cursor_invalid'
	| 'invalid_input'
	/** Timed out: a write may or may not have completed. */
	| 'uncertain'
	| 'unavailable';

export type ListingOutcome<T> = { ok: true; value: T } | { ok: false; reason: ListingReason };

const KNOWN = new Set<string>([
	'not_found',
	'not_authenticated',
	'email_unverified',
	'saved_limit_reached',
	'plan_limit_reached',
	'title_required',
	'title_too_long',
	'note_too_long',
	'dates_required',
	'dates_out_of_order',
	'dates_span_too_long',
	'plan_link_conflict',
	'opportunity_unavailable',
	'venue_not_listed',
	'place_unknown',
	'cursor_invalid'
]);

async function call(
	api: ApiTransport,
	operation: OperationId,
	options: RequestOptions = {}
): Promise<ListingOutcome<{ status: number; body: unknown }>> {
	const result = await api.request(operation, options);
	if (result.kind === 'invalid_request') return { ok: false, reason: 'not_found' };
	if (result.kind === 'timeout') return { ok: false, reason: 'uncertain' };
	if (result.kind !== 'response') return { ok: false, reason: 'unavailable' };
	if (result.status >= 200 && result.status < 300) {
		return { ok: true, value: { status: result.status, body: result.body } };
	}
	const detail =
		typeof result.body === 'object' && result.body !== null && 'detail' in result.body
			? (result.body as { detail: unknown }).detail
			: undefined;
	if (typeof detail === 'string' && KNOWN.has(detail)) {
		return { ok: false, reason: detail as ListingReason };
	}
	if (result.status === 401) return { ok: false, reason: 'not_authenticated' };
	if (result.status === 404) return { ok: false, reason: 'not_found' };
	if (result.status === 422 || result.status === 400) return { ok: false, reason: 'invalid_input' };
	return { ok: false, reason: 'unavailable' };
}

// -- shape checks -------------------------------------------------------------

const isRecord = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null;
const isString = (v: unknown): v is string => typeof v === 'string';
const isNullableString = (v: unknown) => v === null || typeof v === 'string';
const isHttpUrl = (v: unknown) => isString(v) && /^https?:\/\//i.test(v);
const isDate = (v: unknown) => isString(v) && /^\d{4}-\d{2}-\d{2}$/.test(v);
const isNullableDate = (v: unknown) => v === null || isDate(v);
const oneOf =
	<T extends string>(...values: T[]) =>
	(v: unknown): v is T =>
		typeof v === 'string' && (values as string[]).includes(v);
const listOf = (check: (v: unknown) => boolean) => (v: unknown) =>
	Array.isArray(v) && v.every(check);

const isCategory = oneOf(...CATEGORY_VALUES);
const isDiscipline = oneOf(...DISCIPLINE_VALUES);
const isAudience = oneOf(...AUDIENCE_VALUES);
const isPublicStatus = oneOf('published', 'postponed', 'cancelled');
const isKind = oneOf('organization', 'person');

function isProviderRef(v: unknown): boolean {
	return v === null || (isRecord(v) && isString(v.id) && isString(v.name) && isKind(v.kind));
}

function isVenueRef(v: unknown): boolean {
	return (
		v === null ||
		(isRecord(v) &&
			isString(v.id) &&
			isString(v.name) &&
			isString(v.country) &&
			isNullableString(v.locality) &&
			typeof v.closed === 'boolean')
	);
}

export function isOpportunityOut(v: unknown): v is OpportunityOut {
	return (
		isRecord(v) &&
		isString(v.id) &&
		isString(v.title) &&
		isCategory(v.category) &&
		isPublicStatus(v.status) &&
		typeof v.ended === 'boolean' &&
		isProviderRef(v.provider) &&
		isVenueRef(v.venue) &&
		isString(v.country) &&
		isNullableString(v.location_note) &&
		isNullableDate(v.starts_on) &&
		isNullableDate(v.ends_on) &&
		isNullableString(v.time_zone) &&
		listOf(isDiscipline)(v.disciplines) &&
		listOf(isAudience)(v.audience) &&
		listOf(isString)(v.languages) &&
		isNullableString(v.summary) &&
		isNullableString(v.prerequisites) &&
		isNullableString(v.price_amount) &&
		isNullableString(v.price_currency) &&
		(v.price_basis === null || oneOf('per_person', 'per_jump', 'per_day')(v.price_basis)) &&
		isNullableString(v.price_note) &&
		isHttpUrl(v.registration_url) &&
		isHttpUrl(v.source_url) &&
		isNullableString(v.source_note) &&
		isDate(v.checked_on)
	);
}

export function isProviderOut(v: unknown): v is ProviderOut {
	return (
		isRecord(v) &&
		isString(v.id) &&
		isString(v.name) &&
		isKind(v.kind) &&
		isNullableString(v.country) &&
		(v.website_url === null || isHttpUrl(v.website_url)) &&
		isHttpUrl(v.source_url) &&
		isNullableString(v.source_note) &&
		isDate(v.checked_on)
	);
}

function isSavedState(v: unknown): v is SavedStateOut {
	return isRecord(v) && isString(v.opportunity_id) && isString(v.saved_at);
}

function isSavedOut(v: unknown): v is SavedOut {
	return (
		isSavedState(v) &&
		isString((v as Record<string, unknown>).title) &&
		((v as Record<string, unknown>).opportunity === null ||
			isOpportunityOut((v as Record<string, unknown>).opportunity))
	);
}

function isPlanOut(v: unknown): v is PlanOut {
	return (
		isRecord(v) &&
		isString(v.id) &&
		isString(v.title) &&
		isDate(v.starts_on) &&
		isDate(v.ends_on) &&
		isNullableString(v.note) &&
		isNullableString(v.opportunity_id) &&
		(v.opportunity === null || isOpportunityOut(v.opportunity)) &&
		isNullableString(v.venue_id) &&
		(v.venue === null ||
			(isRecord(v.venue) &&
				isString(v.venue.id) &&
				isString(v.venue.name) &&
				oneOf('listed', 'closed')(v.venue.status))) &&
		isNullableString(v.place_id) &&
		(v.place === null || (isRecord(v.place) && isString(v.place.id) && isString(v.place.name))) &&
		isString(v.updated_at)
	);
}

const invalid = <T>(): ListingOutcome<T> => ({
	ok: false,
	reason: 'unavailable'
});

// -- public listings ------------------------------------------------------------

export interface ListingQuery {
	q?: string;
	category?: string;
	country?: string;
	discipline?: string;
	audience?: string;
	provider?: string;
	venue?: string;
	from?: string;
	to?: string;
	cursor?: string;
	limit?: number;
}

export interface ListingPage {
	items: OpportunityOut[];
	nextCursor: string | null;
}

export async function searchOpportunities(
	api: ApiTransport,
	query: ListingQuery
): Promise<ListingOutcome<ListingPage>> {
	const { limit, ...rest } = query;
	const outcome = await call(api, 'searchOpportunities', {
		query: { ...rest, limit: limit === undefined ? undefined : String(limit) }
	});
	if (!outcome.ok) return outcome;
	const body = outcome.value.body;
	if (
		!isRecord(body) ||
		!listOf(isOpportunityOut)(body.items) ||
		!isNullableString(body.next_cursor)
	) {
		return invalid();
	}
	return {
		ok: true,
		value: {
			items: body.items as OpportunityOut[],
			nextCursor: body.next_cursor as string | null
		}
	};
}

export interface Resolved<T> {
	value: T;
	replacedId: string | null;
}

export async function getOpportunity(
	api: ApiTransport,
	id: string
): Promise<ListingOutcome<Resolved<OpportunityOut>>> {
	const outcome = await call(api, 'getOpportunity', { id });
	if (!outcome.ok) return outcome;
	const body = outcome.value.body;
	if (
		!isRecord(body) ||
		!isOpportunityOut(body.opportunity) ||
		!isNullableString(body.replaced_id)
	) {
		return invalid();
	}
	return {
		ok: true,
		value: {
			value: body.opportunity,
			replacedId: body.replaced_id as string | null
		}
	};
}

export async function getProvider(
	api: ApiTransport,
	id: string
): Promise<ListingOutcome<Resolved<ProviderOut>>> {
	const outcome = await call(api, 'getProvider', { id });
	if (!outcome.ok) return outcome;
	const body = outcome.value.body;
	if (!isRecord(body) || !isProviderOut(body.provider) || !isNullableString(body.replaced_id)) {
		return invalid();
	}
	return {
		ok: true,
		value: {
			value: body.provider,
			replacedId: body.replaced_id as string | null
		}
	};
}

// -- private saves ----------------------------------------------------------------

export async function listSaved(
	api: ApiTransport,
	secret: string
): Promise<ListingOutcome<SavedOut[]>> {
	const outcome = await call(api, 'listSaved', { bearer: secret });
	if (!outcome.ok) return outcome;
	return listOf(isSavedOut)(outcome.value.body)
		? { ok: true, value: outcome.value.body as SavedOut[] }
		: invalid();
}

/** Whether the viewer saved this listing; `null` when not saved. */
export async function getSaved(
	api: ApiTransport,
	secret: string,
	id: string
): Promise<ListingOutcome<SavedStateOut | null>> {
	const outcome = await call(api, 'getSaved', { bearer: secret, id });
	if (!outcome.ok) return outcome.reason === 'not_found' ? { ok: true, value: null } : outcome;
	return isSavedState(outcome.value.body) ? { ok: true, value: outcome.value.body } : invalid();
}

export async function saveOpportunity(
	api: ApiTransport,
	secret: string,
	id: string
): Promise<ListingOutcome<SavedStateOut>> {
	const outcome = await call(api, 'saveOpportunity', { bearer: secret, id });
	if (!outcome.ok) return outcome;
	return isSavedState(outcome.value.body) ? { ok: true, value: outcome.value.body } : invalid();
}

export async function unsaveOpportunity(
	api: ApiTransport,
	secret: string,
	id: string
): Promise<ListingOutcome<null>> {
	const outcome = await call(api, 'unsaveOpportunity', { bearer: secret, id });
	return outcome.ok ? { ok: true, value: null } : outcome;
}

// -- private visit plans ------------------------------------------------------------

export interface PlanInput {
	title?: string;
	starts_on?: string;
	ends_on?: string;
	note?: string | null;
	opportunity_id?: string | null;
	venue_id?: string | null;
	place_id?: string | null;
}

export async function listPlans(
	api: ApiTransport,
	secret: string
): Promise<ListingOutcome<PlanOut[]>> {
	const outcome = await call(api, 'listPlans', { bearer: secret });
	if (!outcome.ok) return outcome;
	return listOf(isPlanOut)(outcome.value.body)
		? { ok: true, value: outcome.value.body as PlanOut[] }
		: invalid();
}

function planResult(
	outcome: ListingOutcome<{ status: number; body: unknown }>
): ListingOutcome<PlanOut> {
	if (!outcome.ok) return outcome;
	return isPlanOut(outcome.value.body) ? { ok: true, value: outcome.value.body } : invalid();
}

export async function createPlan(
	api: ApiTransport,
	secret: string,
	input: PlanInput
): Promise<ListingOutcome<PlanOut>> {
	return planResult(await call(api, 'createPlan', { bearer: secret, body: input }));
}

export async function updatePlan(
	api: ApiTransport,
	secret: string,
	id: string,
	input: PlanInput
): Promise<ListingOutcome<PlanOut>> {
	return planResult(await call(api, 'updatePlan', { bearer: secret, id, body: input }));
}

export async function deletePlan(
	api: ApiTransport,
	secret: string,
	id: string
): Promise<ListingOutcome<null>> {
	const outcome = await call(api, 'deletePlan', { bearer: secret, id });
	return outcome.ok ? { ok: true, value: null } : outcome;
}

/** Countries with upcoming public listings (#162: the board shows actual coverage). */
export async function listCoverageCountries(api: ApiTransport): Promise<ListingOutcome<string[]>> {
	const result = await call(api, 'listOpportunityCountries');
	if (!result.ok) return result;
	const body = result.value.body;
	if (!isRecord(body) || !listOf(isString)(body.countries)) {
		return { ok: false, reason: 'unavailable' };
	}
	return { ok: true, value: (body.countries as string[]).filter(isCountryCode) };
}
