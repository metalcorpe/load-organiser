/**
 * Reads a restore upload (#155) without trusting it: the request is refused before
 * parsing when it declares more than the cap, and the file itself must fit 8 MiB.
 * The bytes are passed on unchanged; the API validates and fingerprints them.
 */
export const RESTORE_MAX_BYTES = 8 * 1024 * 1024;
// Multipart framing and the password field on top of the file itself.
const FORM_OVERHEAD_BYTES = 64 * 1024;

export type Upload =
	| { ok: true; bytes: Uint8Array<ArrayBuffer>; password: string }
	| { ok: false; error: string; status: number };

export async function readRestoreUpload(
	request: Request,
	{ needPassword }: { needPassword: boolean }
): Promise<Upload> {
	const declared = request.headers.get('content-length');
	if (declared === null || !/^\d{1,10}$/.test(declared)) {
		return { ok: false, error: 'file_required', status: 411 };
	}
	if (Number(declared) > RESTORE_MAX_BYTES + FORM_OVERHEAD_BYTES) {
		return { ok: false, error: 'archive_too_large', status: 413 };
	}
	const data = await request.formData();
	const file = data.get('archive');
	if (!(file instanceof File) || file.size === 0) {
		return { ok: false, error: 'file_required', status: 400 };
	}
	if (file.size > RESTORE_MAX_BYTES) return { ok: false, error: 'archive_too_large', status: 413 };
	const password = data.get('password');
	const secret = typeof password === 'string' ? password.slice(0, 1024) : '';
	if (needPassword && !secret) return { ok: false, error: 'password_required', status: 400 };
	return { ok: true, bytes: new Uint8Array(await file.arrayBuffer()), password: secret };
}
