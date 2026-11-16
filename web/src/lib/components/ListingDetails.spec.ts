import { render } from 'svelte/server';
import { describe, expect, it } from 'vitest';
import ListingDetails from './ListingDetails.svelte';

describe('ListingDetails', () => {
	it('folds the source and the check date under one disclosure, labelled as what they are', () => {
		const { body } = render(ListingDetails, {
			props: { sourceUrl: 'https://example.org/dz/list', checkedOn: '2026-11-09', note: 'Listed from public information.' }
		});
		expect(body).toContain('<summary>Listing details</summary>');
		expect(body).toMatch(/<details class="listing-details[^"]*">/);
		expect(body).not.toMatch(/<details[^>]* open/);
		expect(body).toContain('href="https://example.org/dz/list"');
		expect(body).toContain('>example.org</a>');
		expect(body).toContain('Last checked against the source');
		expect(body).toContain('datetime="2026-11-09"');
		// A check against a source is not a verification by the place, and a source is not "official".
		expect(body).not.toMatch(/verified|confirmed|official/i);
	});

	it('shows only what is known', () => {
		const { body } = render(ListingDetails, { props: { sourceUrl: 'https://example.org/x' } });
		expect(body).toContain('>Source<');
		expect(body).not.toContain('Last checked');
	});

	it('renders nothing at all without provenance: no empty label, no empty disclosure', () => {
		const { body } = render(ListingDetails, { props: { note: 'Listed from public information.' } });
		expect(body).not.toContain('<details');
		expect(body).not.toContain('Listing details');
	});
});
