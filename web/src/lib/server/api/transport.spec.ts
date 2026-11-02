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
});
