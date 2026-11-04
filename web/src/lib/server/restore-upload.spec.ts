import { describe, expect, it } from 'vitest';
import { RESTORE_MAX_BYTES, readRestoreUpload } from './restore-upload.ts';

async function post(form: FormData, length?: string): Promise<Request> {
	const probe = new Request('https://web.example/profile/data', { method: 'POST', body: form });
	const body = await probe.arrayBuffer();
	const headers = new Headers(probe.headers);
	headers.set('content-length', length ?? String(body.byteLength));
	return new Request('https://web.example/profile/data', { method: 'POST', body, headers });
}

function file(text: string): File {
	return new File([text], 'records.json', { type: 'application/json' });
}

describe('readRestoreUpload', () => {
	it('passes the file through byte for byte with the password', async () => {
		const form = new FormData();
		form.set('archive', file('{ "a" : 1 }'));
		form.set('password', 'pass phrase');
		const upload = await readRestoreUpload(await post(form), { needPassword: true });
		expect(upload.ok).toBe(true);
		if (upload.ok) {
			expect(new TextDecoder().decode(upload.bytes)).toBe('{ "a" : 1 }');
			expect(upload.password).toBe('pass phrase');
		}
	});

	it('refuses an oversized declaration before reading the body', async () => {
		const form = new FormData();
		form.set('archive', file('{}'));
		const upload = await readRestoreUpload(await post(form, String(RESTORE_MAX_BYTES * 2)), {
			needPassword: false
		});
		expect(upload).toEqual({ ok: false, error: 'archive_too_large', status: 413 });
	});

	it('needs a file, and a password to restore', async () => {
		const empty = new FormData();
		empty.set('password', 'x');
		expect(await readRestoreUpload(await post(empty), { needPassword: true })).toMatchObject({
			ok: false,
			error: 'file_required'
		});
		const noPassword = new FormData();
		noPassword.set('archive', file('{}'));
		expect(await readRestoreUpload(await post(noPassword), { needPassword: true })).toMatchObject({
			ok: false,
			error: 'password_required'
		});
		expect((await readRestoreUpload(await post(noPassword), { needPassword: false })).ok).toBe(
			true
		);
	});
});
