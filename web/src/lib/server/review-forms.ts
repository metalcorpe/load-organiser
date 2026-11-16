/** Form helpers for the reviewer editors (#151). Empty optional fields become null. */
import { PRICE_TIER_ROWS } from '#lib/listings.ts';
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

export interface PriceTierIn {
	label: string | null;
	amount: string | null;
	currency: string | null;
	basis: string | null;
	from_on: string | null;
	until_on: string | null;
	optional: boolean;
}

/**
 * The price list rows (`tier_label_0`, `tier_amount_0`, …) in order. A row with neither a
 * name nor an amount is an unused row and is left out; a half-filled one is sent as it is,
 * so the API's rule names what is missing rather than the row silently disappearing.
 */
export function priceTiers(data: FormData): PriceTierIn[] {
	const out: PriceTierIn[] = [];
	for (let i = 0; i < PRICE_TIER_ROWS; i++) {
		const label = text(data, `tier_label_${i}`, 120);
		const amount = text(data, `tier_amount_${i}`, 16);
		if (!label && !amount) continue;
		out.push({
			label,
			amount,
			currency: text(data, `tier_currency_${i}`, 3)?.toUpperCase() ?? null,
			basis: text(data, `tier_basis_${i}`, 16),
			from_on: text(data, `tier_from_${i}`, 10),
			until_on: text(data, `tier_until_${i}`, 10),
			optional: data.get(`tier_optional_${i}`) === 'on'
		});
	}
	return out;
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
