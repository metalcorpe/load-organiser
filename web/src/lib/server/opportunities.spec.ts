import { describe, expect, it } from 'vitest';
import type { ApiTransport, TransportResult } from './api/transport.ts';
import {
	getSaved,
	isOpportunityOut,
	saveOpportunity,
	searchOpportunities
} from './opportunities.ts';

const ID = '0b3e4f0c-1d2e-4f5a-8b6c-7d8e9f0a1b2c';
const LISTING = {
	id: ID,
	title: 'Winter boogie',
	category: 'boogie',
	status: 'published',
	ended: false,
	provider: { id: ID, name: 'Org', kind: 'organization' },
	venue: null,
	country: 'ES',
	location_note: 'Airfield',
	starts_on: '2026-12-04',
	ends_on: '2026-12-08',
	time_zone: 'Europe/Madrid',
	disciplines: ['belly'],
	audience: ['licensed'],
	languages: ['en'],
	summary: null,
	prerequisites: null,
	price_amount: null,
	price_currency: null,
	price_basis: null,
	price_note: null,
	registration_url: 'https://example.org/register',
	source_url: 'https://example.org/events',
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

describe('listing client', () => {
	it('accepts only well-formed public listings', () => {
		expect(isOpportunityOut(LISTING)).toBe(true);
		expect(isOpportunityOut({ ...LISTING, provider: null })).toBe(true);
		expect(isOpportunityOut({ ...LISTING, status: 'draft' })).toBe(false);
		expect(isOpportunityOut({ ...LISTING, registration_url: 'javascript:alert(1)' })).toBe(false);
		expect(isOpportunityOut({ ...LISTING, disciplines: ['swoop'] })).toBe(false);
		expect(isOpportunityOut({ ...LISTING, starts_on: '4 Dec' })).toBe(false);
	});

	it('passes only allowlisted filters and rejects malformed pages', async () => {
		const api = fake(ok({ items: [LISTING], next_cursor: null }));
		const page = await searchOpportunities(api, { country: 'ES', limit: 20 });
		expect(page).toEqual({ ok: true, value: { items: [LISTING], nextCursor: null } });
		expect(api.calls[0]).toMatchObject({
			operation: 'searchOpportunities',
			options: { query: { country: 'ES', limit: '20' } }
		});
		const bad = await searchOpportunities(fake(ok({ items: [{ id: ID }] })), {});
		expect(bad).toEqual({ ok: false, reason: 'unavailable' });
	});

	it('reports a missing bookmark as not saved, not as an error', async () => {
		const missing = await getSaved(fake(ok({ detail: 'not_found' }, 404)), 'secret', ID);
		expect(missing).toEqual({ ok: true, value: null });
		const down = await getSaved(fake({ kind: 'unreachable' }), 'secret', ID);
		expect(down).toEqual({ ok: false, reason: 'unavailable' });
	});

	it('keeps a timed-out save uncertain and maps known refusals', async () => {
		expect(await saveOpportunity(fake({ kind: 'timeout' }), 's', ID)).toEqual({
			ok: false,
			reason: 'uncertain'
		});
		expect(await saveOpportunity(fake(ok({ detail: 'email_unverified' }, 403)), 's', ID)).toEqual({
			ok: false,
			reason: 'email_unverified'
		});
	});
});
