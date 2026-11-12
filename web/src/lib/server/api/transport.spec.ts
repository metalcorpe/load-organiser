import { describe, expect, it, vi } from 'vitest';
import { createApiTransport, type FetchLike } from './transport.ts';

const ORIGIN = 'https://api.example.org';

function json(status: number, body: unknown, headers: Record<string, string> = {}): Response {
	return new Response(JSON.stringify(body), {
		status,
		headers: { 'content-type': 'application/json', ...headers }
	});
}

describe('createApiTransport', () => {
	it('fails closed without an origin and never calls fetch', async () => {
		const fetch = vi.fn<FetchLike>();
		const result = await createApiTransport({ fetch, origin: undefined }).request('getHealth');
		expect(result).toEqual({ kind: 'not_configured' });
		expect(fetch).not.toHaveBeenCalled();
	});

	it('calls only the allowlisted URL with GET, no credentials and manual redirects', async () => {
		const fetch = vi.fn<FetchLike>(async () => json(200, { ok: true }));
		const result = await createApiTransport({ fetch, origin: ORIGIN }).request('getHealth');

		expect(result).toEqual({ kind: 'response', status: 200, body: { ok: true } });
		expect(fetch).toHaveBeenCalledTimes(1);
		const [url, init] = fetch.mock.calls[0];
		expect(url).toBe('https://api.example.org/api/skydiver/v1/health');
		expect(init.method).toBe('GET');
		expect(init.redirect).toBe('manual');
		expect(init.credentials).toBeUndefined();
		expect(init.signal).toBeInstanceOf(AbortSignal);
		const headers = new Headers(init.headers);
		expect([...headers.keys()]).toEqual(['accept']);
	});

	it('reads a spreadsheet as text only where the operation expects CSV; errors stay JSON', async () => {
		const csv = () =>
			new Response('\ufeffDate,Place\r\n2026-10-10,Farm\r\n', {
				status: 200,
				headers: { 'content-type': 'text/csv; charset=utf-8' }
			});
		const fetch = vi.fn<FetchLike>(async () => csv());
		const api = createApiTransport({ fetch, origin: ORIGIN });
		const sheet = await api.request('exportSpreadsheet', { query: { from_on: '2026-10-01' } });
		expect(sheet).toEqual({ kind: 'response', status: 200, body: 'Date,Place\r\n2026-10-10,Farm\r\n' });
		const [url, init] = fetch.mock.calls[0];
		expect(url).toBe('https://api.example.org/api/skydiver/v1/records/spreadsheet?from_on=2026-10-01');
		expect(new Headers(init.headers).get('accept')).toBe('text/csv, application/json');
		// Any other operation refuses a CSV answer.
		expect(await api.request('getHealth')).toEqual({ kind: 'invalid_response' });
		fetch.mockImplementationOnce(async () =>
			json(429, { detail: 'too_many_attempts' }, { 'retry-after': '300' })
		);
		expect(await api.request('exportSpreadsheet')).toEqual({
			kind: 'response',
			status: 429,
			body: { detail: 'too_many_attempts' },
			retryAfter: 300
		});
	});

	it('sends a restore file byte for byte with the confirmation header', async () => {
		const fetch = vi.fn<FetchLike>(async () => json(200, { outcome: 'restored' }));
		const raw = new TextEncoder().encode('{ "format" : 1 }');
		await createApiTransport({ fetch, origin: ORIGIN }).request('restoreRecords', {
			bearer: 'secret',
			rawBody: raw,
			confirmPassword: 'pass phrase'
		});
		const [url, init] = fetch.mock.calls[0];
		expect(url).toBe('https://api.example.org/api/skydiver/v1/records/restore');
		expect(init.body).toBe(raw);
		const headers = new Headers(init.headers);
		expect(headers.get('content-type')).toBe('application/json');
		expect(headers.get('x-organiser-confirm-password')).toBe('pass phrase');
	});

	it('sends an import file as CSV with its choices in the allowlisted query only', async () => {
		const fetch = vi.fn<FetchLike>(async () => json(200, { outcome: 'imported' }));
		const api = createApiTransport({ fetch, origin: ORIGIN });
		const raw = new TextEncoder().encode('Date,Place\n2024-03-12,Farm\n');
		await api.request('importJumps', {
			bearer: 'secret',
			rawBody: raw,
			query: { country: 'PT', col_notes: 'none', expected: 'a'.repeat(64) }
		});
		const [url, init] = fetch.mock.calls[0];
		expect(url).toBe(
			`https://api.example.org/api/skydiver/v1/jumps/import?country=PT&col_notes=none&expected=${'a'.repeat(64)}`
		);
		expect(init.body).toBe(raw);
		expect(new Headers(init.headers).get('content-type')).toBe('text/csv');
		expect(
			await api.request('checkJumpImport', { rawBody: raw, query: { expected: 'x' } })
		).toEqual({ kind: 'invalid_request' });
	});

	it('passes an export through as text without parsing it', async () => {
		const file = '{"format":"load-organiser.personal-records","version":1}';
		const fetch = vi.fn<FetchLike>(
			async () => new Response(file, { headers: { 'content-type': 'application/json' } })
		);
		const result = await createApiTransport({ fetch, origin: ORIGIN }).request('exportRecords', {
			bearer: 'secret'
		});
		expect(result).toEqual({ kind: 'response', status: 200, body: file });
		const headers = new Headers(fetch.mock.calls[0][1].headers);
		expect(headers.has('x-organiser-confirm-password')).toBe(false);
	});

	it('accepts only a lowercase handle as a handle path parameter', async () => {
		const fetch = vi.fn<FetchLike>(async () => json(200, {}));
		const api = createApiTransport({ fetch, origin: ORIGIN });
		for (const handle of ['Sam', 'a/../b', 'ab', 'sam%2f', undefined]) {
			expect(await api.request('getPerson', { handle })).toEqual({ kind: 'invalid_request' });
		}
		expect(fetch).not.toHaveBeenCalled();
		await api.request('getPerson', { handle: 'sam_flyer' });
		expect(fetch.mock.calls[0][0]).toBe('https://api.example.org/api/skydiver/v1/people/sam_flyer');
		expect(await api.request('getHealth', { handle: 'sam_flyer' })).toEqual({
			kind: 'invalid_request'
		});
	});

	it('creates independent transports per request', () => {
		const a = createApiTransport({ fetch: vi.fn<FetchLike>(), origin: ORIGIN });
		const b = createApiTransport({ fetch: vi.fn<FetchLike>(), origin: ORIGIN });
		expect(a).not.toBe(b);
	});

	it('maps a network failure to unreachable', async () => {
		const fetch = vi.fn<FetchLike>(async () => {
			throw new TypeError('fetch failed: connect ECONNREFUSED 10.0.0.5');
		});
		const result = await createApiTransport({ fetch, origin: ORIGIN }).request('getHealth');
		expect(result).toEqual({ kind: 'unreachable' });
	});

	it('maps an aborted request to timeout', async () => {
		const fetch: FetchLike = (_url, init) =>
			new Promise((_resolve, reject) => {
				init.signal?.addEventListener('abort', () => reject(init.signal?.reason));
			});
		const result = await createApiTransport({ fetch, origin: ORIGIN, timeoutMs: 10 }).request(
			'getHealth'
		);
		expect(result).toEqual({ kind: 'timeout' });
	});

	it('does not follow redirects', async () => {
		const fetch = vi.fn<FetchLike>(
			async () => new Response(null, { status: 302, headers: { location: 'https://evil.example' } })
		);
		const result = await createApiTransport({ fetch, origin: ORIGIN }).request('getHealth');
		expect(result).toEqual({ kind: 'upstream_error', status: 302 });
	});

	it('reports non-JSON error responses by status only', async () => {
		const fetch = vi.fn<FetchLike>(
			async () => new Response('<html>stack trace</html>', { status: 502 })
		);
		const result = await createApiTransport({ fetch, origin: ORIGIN }).request('getHealth');
		expect(result).toEqual({ kind: 'upstream_error', status: 502 });
	});

	it('rejects malformed and oversized JSON', async () => {
		const malformed = vi.fn<FetchLike>(
			async () =>
				new Response('{not json', { status: 200, headers: { 'content-type': 'application/json' } })
		);
		expect(await createApiTransport({ fetch: malformed, origin: ORIGIN }).request('getHealth')).toEqual(
			{ kind: 'invalid_response' }
		);

		const big = vi.fn<FetchLike>(async () => json(200, { padding: 'x'.repeat(200) }));
		expect(
			await createApiTransport({ fetch: big, origin: ORIGIN, maxBodyBytes: 100 }).request('getHealth')
		).toEqual({ kind: 'invalid_response' });
	});

	it('rejects a declared oversize body without reading it', async () => {
		const cancel = vi.fn();
		const body = new ReadableStream<Uint8Array>({ pull: () => {}, cancel });
		const fetch = vi.fn<FetchLike>(
			async () =>
				new Response(body, {
					status: 200,
					headers: { 'content-type': 'application/json', 'content-length': '1000000' }
				})
		);
		expect(
			await createApiTransport({ fetch, origin: ORIGIN, maxBodyBytes: 100 }).request('getHealth')
		).toEqual({ kind: 'invalid_response' });
		expect(cancel).toHaveBeenCalled();
	});

	it('stops reading an undeclared stream once it exceeds the limit', async () => {
		let pulls = 0;
		const cancel = vi.fn();
		// Endless stream with no content-length: must be cut off, not buffered.
		const body = new ReadableStream<Uint8Array>({
			pull(controller) {
				pulls += 1;
				controller.enqueue(new Uint8Array(64).fill(0x20));
			},
			cancel
		});
		const fetch = vi.fn<FetchLike>(
			async () => new Response(body, { status: 200, headers: { 'content-type': 'application/json' } })
		);
		expect(
			await createApiTransport({ fetch, origin: ORIGIN, maxBodyBytes: 100 }).request('getHealth')
		).toEqual({ kind: 'invalid_response' });
		expect(cancel).toHaveBeenCalled();
		expect(pulls).toBeLessThan(10);
	});

	it('accepts a multi-chunk body within the limit', async () => {
		const encoded = new TextEncoder().encode(JSON.stringify({ ok: 'é' }));
		const body = new ReadableStream<Uint8Array>({
			start(controller) {
				// Split inside the multi-byte character to exercise reassembly.
				controller.enqueue(encoded.slice(0, encoded.length - 3));
				controller.enqueue(encoded.slice(encoded.length - 3));
				controller.close();
			}
		});
		const fetch = vi.fn<FetchLike>(
			async () => new Response(body, { status: 200, headers: { 'content-type': 'application/json' } })
		);
		expect(await createApiTransport({ fetch, origin: ORIGIN }).request('getHealth')).toEqual({
			kind: 'response',
			status: 200,
			body: { ok: 'é' }
		});
	});

	it('sends JSON bodies, bearer credentials and the proxy-keyed client address only', async () => {
		const fetch = vi.fn<FetchLike>(async () => json(201, { ok: true }));
		await createApiTransport({ fetch, origin: ORIGIN, proxyKey: 'k'.repeat(32) }).request(
			'createSession',
			{ body: { email: 'e' }, bearer: 'secret', clientIp: '203.0.113.9' }
		);
		const [url, init] = fetch.mock.calls[0];
		expect(url).toBe('https://api.example.org/api/skydiver/v1/auth/sessions');
		expect(init.method).toBe('POST');
		expect(init.body).toBe('{"email":"e"}');
		const headers = new Headers(init.headers);
		expect(headers.get('authorization')).toBe('Bearer secret');
		expect(headers.get('content-type')).toBe('application/json');
		expect(headers.get('x-organiser-client-ip')).toBe('203.0.113.9');
		expect(headers.get('x-organiser-proxy-key')).toBe('k'.repeat(32));
		expect(headers.has('cookie')).toBe(false);
	});

	it('sends the proxy key on every call, with or without a client address', async () => {
		const fetch = vi.fn<FetchLike>(async () => json(200, {}));
		await createApiTransport({ fetch, origin: ORIGIN, proxyKey: 'k'.repeat(32) }).request('getHealth');
		const headers = new Headers(fetch.mock.calls[0][1].headers);
		expect(headers.get('x-organiser-proxy-key')).toBe('k'.repeat(32));
		expect(headers.has('x-organiser-client-ip')).toBe(false);
	});

	it('omits the client address without a proxy key', async () => {
		const fetch = vi.fn<FetchLike>(async () => json(200, {}));
		await createApiTransport({ fetch, origin: ORIGIN }).request('getSession', {
			bearer: 's',
			clientIp: '203.0.113.9'
		});
		const headers = new Headers(fetch.mock.calls[0][1].headers);
		expect(headers.has('x-organiser-client-ip')).toBe(false);
	});

	it('handles 204 and Retry-After', async () => {
		const empty = vi.fn<FetchLike>(async () => new Response(null, { status: 204 }));
		expect(await createApiTransport({ fetch: empty, origin: ORIGIN }).request('deleteSession')).toEqual({
			kind: 'response',
			status: 204,
			body: null
		});
		const limited = vi.fn<FetchLike>(async () =>
			json(429, { detail: 'too_many_attempts' }, { 'retry-after': '900' })
		);
		expect(await createApiTransport({ fetch: limited, origin: ORIGIN }).request('createSession')).toEqual({
			kind: 'response',
			status: 429,
			body: { detail: 'too_many_attempts' },
			retryAfter: 900
		});
	});

	it('fills {id} only with a UUID and never contacts the API otherwise', async () => {
		const fetch = vi.fn<FetchLike>(async () => json(200, {}));
		const api = createApiTransport({ fetch, origin: ORIGIN });
		const id = '0B3E4F0C-1D2E-4F5A-8B6C-7D8E9F0A1B2C';
		await api.request('getVenue', { id });
		expect(fetch.mock.calls[0][0]).toBe(`${ORIGIN}/api/skydiver/v1/venues/${id.toLowerCase()}`);

		for (const bad of [undefined, '', '../health', 'x/../../auth/session', `${id}?q=1`, `${id}#x`]) {
			expect(await api.request('getVenue', { id: bad })).toEqual({ kind: 'invalid_request' });
		}
		// An id on an operation without `{id}` is refused rather than ignored.
		expect(await api.request('listPlaces', { id })).toEqual({ kind: 'invalid_request' });
		expect(fetch).toHaveBeenCalledTimes(1);
	});

	it('fills {sub} only with a UUID, and refuses it where the path has none', async () => {
		const fetch = vi.fn<FetchLike>(async () => new Response(null, { status: 204 }));
		const api = createApiTransport({ fetch, origin: ORIGIN });
		const id = '0b3e4f0c-1d2e-4f5a-8b6c-7d8e9f0a1b2c';
		const sub = '1b3e4f0c-1d2e-4f5a-8b6c-7d8e9f0a1b2c';
		await api.request('deleteServiceEntry', { id, sub });
		expect(fetch.mock.calls[0][0]).toBe(`${ORIGIN}/api/skydiver/v1/gear/components/${id}/service/${sub}`);
		for (const bad of [undefined, '../rigs', `${sub}/x`]) {
			expect(await api.request('deleteServiceEntry', { id, sub: bad })).toEqual({ kind: 'invalid_request' });
		}
		expect(await api.request('getComponent', { id, sub })).toEqual({ kind: 'invalid_request' });
		expect(fetch).toHaveBeenCalledTimes(1);
	});

	it('sends only allowlisted, encoded query parameters', async () => {
		const fetch = vi.fn<FetchLike>(async () => json(200, {}));
		const api = createApiTransport({ fetch, origin: ORIGIN });
		await api.request('searchVenues', {
			query: { q: 'a&b=c #d', country: 'ES', cursor: undefined, limit: '' }
		});
		expect(fetch.mock.calls[0][0]).toBe(
			`${ORIGIN}/api/skydiver/v1/venues?q=a%26b%3Dc+%23d&country=ES`
		);
		expect(await api.request('searchVenues', { query: { owner: 'x' } })).toEqual({
			kind: 'invalid_request'
		});
		expect(await api.request('getHealth', { query: { q: 'x' } })).toEqual({ kind: 'invalid_request' });
		expect(fetch).toHaveBeenCalledTimes(1);
	});
});
