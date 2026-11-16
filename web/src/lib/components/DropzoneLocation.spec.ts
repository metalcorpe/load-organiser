import { render } from "svelte/server";
import { describe, expect, it } from "vitest";
import DropzoneLocation from "./DropzoneLocation.svelte";

describe("DropzoneLocation", () => {
	it("leads with the place and a map link; the coordinates stay folded", () => {
		const { body } = render(DropzoneLocation, {
			props: {
				place: "Empuriabrava, Spain",
				latitude: 42.25857,
				longitude: 3.137,
			},
		});
		expect(body.indexOf("Empuriabrava, Spain")).toBeLessThan(
			body.indexOf("View on map"),
		);
		expect(body.indexOf("View on map")).toBeLessThan(
			body.indexOf("42.25857° N"),
		);
		expect(body).toContain(
			'href="https://www.openstreetmap.org/?mlat=42.25857&amp;mlon=3.137#map=13/42.25857/3.137"',
		);
		expect(body).toMatch(/<details class="coordinates[^"]*">/);
		expect(body).not.toMatch(/<details[^>]* open/);
		// The point is never presented as an entrance or landing area.
		expect(body).not.toMatch(/entrance|landing area|verified/i);
	});

	it("says plainly when there is no map point, and offers no map link", () => {
		const { body } = render(DropzoneLocation, { props: { place: "Spain" } });
		expect(body).toContain("No map location listed.");
		expect(body).not.toContain("View on map");
		expect(body).not.toContain("Coordinates");
	});

	it("renders no copy button on the server: it needs JavaScript and a clipboard", () => {
		const { body } = render(DropzoneLocation, {
			props: { place: "Spain", latitude: 40, longitude: -3 },
		});
		expect(body).not.toContain("Copy coordinates");
	});
});
