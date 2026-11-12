/**
 * Reads a spreadsheet import form without trusting it: the request is refused before
 * parsing when it declares more than the cap, and the file itself must fit 1 MiB. The
 * bytes are passed on unchanged (the API reads and fingerprints them); the options and
 * column choices become allowlisted query values, and are echoed back to re-render the
 * form.
 */
import { IMPORT_FIELDS } from '#lib/imports.ts';

export const IMPORT_MAX_BYTES = 1024 * 1024;
// Multipart framing and the option fields on top of the file itself.
const FORM_OVERHEAD_BYTES = 64 * 1024;

export interface ImportChoices {
	date_order: 'dmy' | 'mdy' | 'ymd';
	unit: 'ft' | 'm';
	country: string;
}

export type ImportUpload =
	| {
			ok: true;
			bytes: Uint8Array<ArrayBuffer>;
			choices: ImportChoices;
			query: Record<string, string | undefined>;
	  }
	| { ok: false; error: string; status: number; choices: ImportChoices };

const DEFAULTS: ImportChoices = { date_order: 'dmy', unit: 'ft', country: '' };

function text(data: FormData, name: string): string {
	const value = data.get(name);
	return typeof value === 'string' ? value.slice(0, 100) : '';
}

/** The options as sent, each reduced to an allowed value. */
export function readChoices(data: FormData): ImportChoices {
	const order = text(data, 'date_order');
	const unit = text(data, 'unit');
	const country = text(data, 'country').toUpperCase();
	return {
		date_order: order === 'mdy' || order === 'ymd' ? order : 'dmy',
		unit: unit === 'm' ? 'm' : 'ft',
		country: /^[A-Z]{2}$/.test(country) ? country : ''
	};
}

/** Query values for the API: options, explicit column choices and the checked fingerprint. */
export function importQuery(
	data: FormData,
	choices: ImportChoices
): Record<string, string | undefined> {
	const query: Record<string, string | undefined> = {
		date_order: choices.date_order,
		unit: choices.unit,
		country: choices.country || undefined
	};
	for (const field of IMPORT_FIELDS) {
		const value = text(data, `col_${field}`);
		// "auto" or anything unexpected: let the API detect the column from its heading.
		if (value === 'none' || /^\d{1,3}$/.test(value)) query[`col_${field}`] = value;
	}
	const expected = text(data, 'expected');
	if (/^[0-9a-f]{64}$/.test(expected)) query.expected = expected;
	return query;
}

export async function readImportUpload(request: Request): Promise<ImportUpload> {
	const declared = request.headers.get('content-length');
	if (declared === null || !/^\d{1,10}$/.test(declared)) {
		return {
			ok: false,
			error: 'file_required',
			status: 411,
			choices: DEFAULTS
		};
	}
	if (Number(declared) > IMPORT_MAX_BYTES + FORM_OVERHEAD_BYTES) {
		return {
			ok: false,
			error: 'file_too_large',
			status: 413,
			choices: DEFAULTS
		};
	}
	const data = await request.formData();
	const choices = readChoices(data);
	const file = data.get('file');
	if (!(file instanceof File) || file.size === 0) {
		return { ok: false, error: 'file_required', status: 400, choices };
	}
	if (file.size > IMPORT_MAX_BYTES) {
		return { ok: false, error: 'file_too_large', status: 413, choices };
	}
	return {
		ok: true,
		bytes: new Uint8Array(await file.arrayBuffer()),
		choices,
		query: importQuery(data, choices)
	};
}
