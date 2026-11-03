/** Form helpers for the reviewer editors (#151). Empty optional fields become null. */
import { field } from './forms.ts';

export function text(data: FormData, name: string, max = 2048): string | null {
	const value = field(data, name, { max, trim: true });
	return value === '' ? null : value;
}

export function version(data: FormData): number | null {
	const raw = field(data, 'version', { max: 12 });
	const parsed = Number(raw);
	return raw && Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

export function list(data: FormData, name: string): string[] {
	return data
		.getAll(name)
		.filter((v): v is string => typeof v === 'string')
		.map((v) => v.slice(0, 32));
}

/**
 * Plain object of the submitted strings, to re-render the form after a refusal.
 * Repeated fields (checkbox groups) are joined with commas.
 */
export function echo(data: FormData): Record<string, string> {
	const out: Record<string, string> = {};
	for (const key of new Set(data.keys())) {
		if (key === 'version') continue;
		const values = data.getAll(key).filter((v): v is string => typeof v === 'string');
		out[key] = values.map((v) => v.slice(0, 4000)).join(',');
	}
	return out;
}
