import { describe, expect, it } from 'vitest';
import type { ApiTransport, TransportResult } from './api/transport.ts';
import { getVenue, isVenueOut, searchVenues, updatePlace } from './directory.ts';

const VENUE = {
	id: '0b3e4f0c-1d2e-4f5a-8b6c-7d8e9f0a1b2c',
	name: 'Skydive Example',
	country: 'ES',
	locality: null,
	latitude: null,
	longitude: null,
	status: 'listed',
	aliases: [{ name: 'Old name', kind: 'former' }],
	source_url: 'https://example.org/dz',
	source_note: null,
	checked_on: '2026-11-01'
};

function fake(result: TransportResult): ApiTransport & { calls: unknown[] } {
	const calls: unknown[] = [];
	return {
		calls,
		async request(operation, options) {
			calls.push({ operation, options });
			return result;
		}
	};
}

const ok = (body: unknown, status = 200): TransportResult => ({ kind: 'response', status, body });

describe('directory client', () => {
	it('accepts only well-formed public venues', () => {
		expect(isVenueOut(VENUE)).toBe(true);
		expect(isVenueOut({ ...VENUE, status: 'draft' })).toBe(false);
		expect(isVenueOut({ ...VENUE, source_url: 'javascript:alert(1)' })).toBe(false);
		expect(isVenueOut({ ...VENUE, aliases: [{ name: 'x', kind: 'secret' }] })).toBe(false);
		expect(isVenueOut({ ...VENUE, latitude: Number.NaN })).toBe(false);
	});

	it('passes search filters as allowlisted query values', async () => {
		const api = fake(ok({ items: [VENUE], next_cursor: 'abc' }));
		const outcome = await searchVenues(api, { q: 'sky', country: 'ES', limit: 10 });
		expect(outcome).toEqual({ ok: true, value: { items: [VENUE], nextCursor: 'abc' } });
		expect(api.calls).toEqual([
			{
				operation: 'searchVenues',
				options: { query: { q: 'sky', country: 'ES', cursor: undefined, limit: '10' } }
			}
		]);
	});

	it('rejects malformed pages instead of rendering them', async () => {
		const outcome = await searchVenues(fake(ok({ items: [{ ...VENUE, id: 7 }] })), {});
		expect(outcome).toEqual({ ok: false, reason: 'unavailable' });
	});

	it('maps API problems to known reasons only', async () => {
		expect(await getVenue(fake(ok({ detail: 'not_found' }, 404)), VENUE.id)).toEqual({
			ok: false,
			reason: 'not_found'
		});
		expect(await getVenue(fake(ok({ detail: 'internal trace' }, 500)), VENUE.id)).toEqual({
			ok: false,
			reason: 'unavailable'
		});
		expect(await getVenue(fake({ kind: 'invalid_request' }), 'nope')).toEqual({
			ok: false,
			reason: 'not_found'
		});
		expect(
			await updatePlace(fake({ kind: 'timeout' }), 's', VENUE.id, { venue_id: null })
		).toEqual({ ok: false, reason: 'uncertain' });
		expect(
			await updatePlace(fake(ok({ detail: 'venue_not_listed' }, 422)), 's', VENUE.id, {
				venue_id: VENUE.id
			})
		).toEqual({ ok: false, reason: 'venue_not_listed' });
	});

	it('reports a merged venue so the page can redirect', async () => {
		const merged = await getVenue(
			fake(ok({ venue: VENUE, replaced_id: 'a1b2c3d4-0000-4000-8000-000000000000' })),
			'a1b2c3d4-0000-4000-8000-000000000000'
		);
		expect(merged).toEqual({
			ok: true,
			value: { venue: VENUE, replacedId: 'a1b2c3d4-0000-4000-8000-000000000000' }
		});
	});
});
