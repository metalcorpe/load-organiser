import { describe, expect, it } from "vitest";
import { priceTiers } from "./review-forms.ts";

function form(entries: Record<string, string>): FormData {
	const data = new FormData();
	for (const [k, v] of Object.entries(entries)) data.append(k, v);
	return data;
}

describe("priceTiers", () => {
	it("reads filled rows in order and leaves unused rows out", () => {
		const data = form({
			tier_label_0: " Registration ",
			tier_amount_0: "80",
			tier_currency_0: "eur",
			tier_basis_0: "per_person",
			tier_until_0: "2026-11-14",
			tier_label_1: "",
			tier_amount_1: "",
			tier_label_2: "Load organising",
			tier_amount_2: "4.80",
			tier_currency_2: "EUR",
			tier_basis_2: "per_jump",
			tier_optional_2: "on",
		});
		expect(priceTiers(data)).toEqual([
			{
				label: "Registration",
				amount: "80",
				currency: "EUR",
				basis: "per_person",
				from_on: null,
				until_on: "2026-11-14",
				optional: false,
			},
			{
				label: "Load organising",
				amount: "4.80",
				currency: "EUR",
				basis: "per_jump",
				from_on: null,
				until_on: null,
				optional: true,
			},
		]);
	});

	it("sends a half-filled row for the API to name what is missing", () => {
		expect(priceTiers(form({ tier_amount_0: "95" }))).toEqual([
			{
				label: null,
				amount: "95",
				currency: null,
				basis: null,
				from_on: null,
				until_on: null,
				optional: false,
			},
		]);
	});

	it("is an empty list when no row is used, which clears a saved list", () => {
		expect(priceTiers(form({}))).toEqual([]);
	});
});
