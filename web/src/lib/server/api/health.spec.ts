import { describe, expect, it } from 'vitest';
import { fetchHealth } from './health.ts';
import type { ApiTransport, TransportResult } from './transport.ts';

const transport = (result: TransportResult): ApiTransport => ({ request: async () => result });
const body = (state: 'ok' | 'unavailable') => ({
	status: state,
	database: state,
	checked_at: '2026-11-02T12:00:00Z'
});

describe('fetchHealth', () => {
	it('reports operational for a valid 200', async () => {
		expect(await fetchHealth(transport({ kind: 'response', status: 200, body: body('ok') }))).toEqual({
			kind: 'operational',
			checkedAt: '2026-11-02T12:00:00.000Z'
		});
	});

	it('reports degraded for the documented 503 body', async () => {
		expect(
			await fetchHealth(transport({ kind: 'response', status: 503, body: body('unavailable') }))
		).toEqual({ kind: 'degraded', checkedAt: '2026-11-02T12:00:00.000Z' });
	});

	it('rejects bodies that do not match the contract', async () => {
		for (const bad of [null, {}, { ...body('ok'), status: 'great' }, { ...body('ok'), checked_at: 'x' }]) {
			expect(await fetchHealth(transport({ kind: 'response', status: 200, body: bad }))).toEqual({
				kind: 'invalid_response'
			});
		}
	});

	it('reports a 503 with a non-contract body as an upstream outage', async () => {
		expect(
			await fetchHealth(transport({ kind: 'response', status: 503, body: { detail: 'proxy' } }))
		).toEqual({ kind: 'upstream_error', status: 503 });
	});

	it('passes through other statuses and transport failures without details', async () => {
		expect(await fetchHealth(transport({ kind: 'response', status: 500, body: { detail: 'x' } }))).toEqual(
			{ kind: 'upstream_error', status: 500 }
		);
		expect(await fetchHealth(transport({ kind: 'timeout' }))).toEqual({ kind: 'timeout' });
	});
});
