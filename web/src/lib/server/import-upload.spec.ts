import { describe, expect, it } from 'vitest';
import { IMPORT_MAX_BYTES, readImportUpload } from './import-upload.ts';

async function post(form: FormData, length?: string): Promise<Request> {
	const probe = new Request('https://web.example/records/import', {
		method: 'POST',
		body: form
	});
	const body = await probe.arrayBuffer();
	const headers = new Headers(probe.headers);
	headers.set('content-length', length ?? String(body.byteLength));
	return new Request('https://web.example/records/import', {
		method: 'POST',
		body,
		headers
	});
}

const csv = (text: string) => new File([text], 'logbook.csv', { type: 'text/csv' });

describe('readImportUpload', () => {
	it('passes the file through byte for byte with its choices as query values', async () => {
		const form = new FormData();
		form.set('file', csv('Date;Place\r\n12/03/2024;Farm\r\n'));
		form.set('date_order', 'mdy');
		form.set('unit', 'm');
		form.set('country', 'pt');
		form.set('col_notes', 'none');
		form.set('col_type', '3');
		form.set('col_place', 'auto');
		form.set('expected', 'f'.repeat(64));
		const upload = await readImportUpload(await post(form));
		expect(upload.ok).toBe(true);
		if (!upload.ok) return;
		expect(new TextDecoder().decode(upload.bytes)).toBe('Date;Place\r\n12/03/2024;Farm\r\n');
		expect(upload.choices).toEqual({
			date_order: 'mdy',
			unit: 'm',
			country: 'PT'
		});
		expect(upload.query).toEqual({
			date_order: 'mdy',
			unit: 'm',
			country: 'PT',
			col_notes: 'none',
			col_type: '3',
			expected: 'f'.repeat(64)
		});
	});

	it('reduces unexpected option values to the defaults and drops odd column values', async () => {
		const form = new FormData();
		form.set('file', csv('Date,Place\n'));
		form.set('date_order', 'yyyy');
		form.set('unit', 'furlongs');
		form.set('country', 'Portugal');
		form.set('col_date', '../1');
		form.set('expected', 'not-a-fingerprint');
		const upload = await readImportUpload(await post(form));
		expect(upload.ok && upload.query).toEqual({
			date_order: 'dmy',
			unit: 'ft',
			country: undefined
		});
	});

	it('needs a file and refuses one over 1 MiB', async () => {
		const empty = new FormData();
		empty.set('date_order', 'ymd');
		const missing = await readImportUpload(await post(empty));
		expect(missing).toMatchObject({
			ok: false,
			error: 'file_required',
			status: 400
		});
		expect(!missing.ok && missing.choices.date_order).toBe('ymd');

		const big = new FormData();
		big.set('file', csv('x'.repeat(IMPORT_MAX_BYTES + 1)));
		expect(await readImportUpload(await post(big))).toMatchObject({
			ok: false,
			error: 'file_too_large',
			status: 413
		});
		const declared = await readImportUpload(
			await post(new FormData(), String(IMPORT_MAX_BYTES * 2))
		);
		expect(declared).toMatchObject({
			ok: false,
			error: 'file_too_large',
			status: 413
		});
	});
});
