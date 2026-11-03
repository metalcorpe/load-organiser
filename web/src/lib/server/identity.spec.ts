import { describe, expect, it } from 'vitest';
import type { ApiTransport, TransportResult } from './api/transport.ts';
import { getViewer, signIn, signOut } from './identity.ts';

const SECRET = 'a'.repeat(43);
const VIEWER = {
	account_id: '00000000-0000-4000-8000-000000000001',
	person_id: '00000000-0000-4000-8000-000000000002',
	email: 'jumper@example.com',
	display_name: null,
	email_verified: false,
	session_expires_at: '2026-11-09T12:00:00Z',
	roles: []
};

function api(result: TransportResult, seen: unknown[] = []): ApiTransport {
	return {
		request: async (operation, options) => {
			seen.push({ operation, options });
			return result;
		}
	};
}

describe('identity calls', () => {
	it('maps a session response to a viewer without exposing other fields', async () => {
		const seen: unknown[] = [];
		const outcome = await signIn(
			api(
				{ kind: 'response', status: 201, body: { session_secret: SECRET, viewer: VIEWER } },
				seen
			),
			{ email: 'jumper@example.com', password: 'p' },
			'203.0.113.9'
		);
		expect(outcome).toEqual({
			ok: true,
			value: {
				secret: SECRET,
				viewer: {
					accountId: VIEWER.account_id,
					personId: VIEWER.person_id,
					email: VIEWER.email,
					displayName: null,
					emailVerified: false,
					sessionExpiresAt: '2026-11-09T12:00:00.000Z',
					reviewer: false
				}
			}
		});
		expect(seen).toEqual([
			{
				operation: 'createSession',
				options: { body: { email: 'jumper@example.com', password: 'p' }, clientIp: '203.0.113.9' }
			}
		]);
	});

	it('rejects malformed secrets and viewers from upstream', async () => {
		const bad = await signIn(
			api({ kind: 'response', status: 201, body: { session_secret: 'short', viewer: VIEWER } }),
			{ email: 'e', password: 'p' },
			'ip'
		);
		expect(bad).toEqual({ ok: false, reason: 'unavailable' });
		const noViewer = await getViewer(api({ kind: 'response', status: 200, body: {} }), SECRET);
		expect(noViewer).toEqual({ ok: false, reason: 'unavailable' });
	});

	it('maps problem codes, throttling and transport failures', async () => {
		expect(
			await getViewer(
				api({ kind: 'response', status: 401, body: { detail: 'not_authenticated' } }),
				SECRET
			)
		).toEqual({ ok: false, reason: 'not_authenticated' });
		expect(
			await signIn(
				api({
					kind: 'response',
					status: 429,
					body: { detail: 'too_many_attempts' },
					retryAfter: 900
				}),
				{ email: 'e', password: 'p' },
				'ip'
			)
		).toEqual({ ok: false, reason: 'too_many_attempts', retryAfter: 900 });
		expect(await signOut(api({ kind: 'timeout' }), SECRET)).toEqual({
			ok: false,
			reason: 'uncertain'
		});
		expect(await signOut(api({ kind: 'unreachable' }), SECRET)).toEqual({
			ok: false,
			reason: 'unavailable'
		});
		// Unknown upstream detail text is never passed through.
		expect(
			await getViewer(
				api({ kind: 'response', status: 500, body: { detail: 'SQL trace…' } }),
				SECRET
			)
		).toEqual({ ok: false, reason: 'unavailable' });
	});
});
