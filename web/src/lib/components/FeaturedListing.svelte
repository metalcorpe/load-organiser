<script lang="ts">
	import type { OpportunityOut } from '#lib/contracts/index.ts';
	import TypeIcon from '#lib/components/TypeIcon.svelte';
	import { countryName } from '#lib/countries.ts';
	import { eventHref } from '#lib/listing-filters.ts';
	import { featuredLabel, formatPrice, formatRange } from '#lib/listings.ts';

	/**
	 * The board's navy card: the next multi-day boogie or camp (pickFeatured), shown once above
	 * the dated list and not repeated in it. The title leads; the dates follow in full, with the
	 * year, as one line of text.
	 */
	let { item }: { item: OpportunityOut } = $props();
	const place = $derived(item.venue ? item.venue.name : (item.location_note ?? ''));
	const price = $derived(formatPrice(item.price_amount, item.price_currency, item.price_basis));
	const label = $derived(featuredLabel(item.category));
</script>

<section class="featured type-{item.category}" aria-labelledby="featured-heading">
	<h2 id="featured-heading" class="visually-hidden">Highlighted: {label.toLowerCase()}</h2>
	<span class="type-pill"><TypeIcon category={item.category} />{label}</span>
	<a class="title" href={eventHref(item.id)}>{item.title}</a>
	<span class="dates">{formatRange(item.starts_on, item.ends_on)}</span>
	<span class="meta">
		{place ? `${place}, ` : ''}{countryName(item.country)}{price ? ` · ${price}` : ''}
	</span>
</section>

<style>
	.featured {
		position: relative;
		display: grid;
		gap: 0.45rem;
		justify-items: start;
		margin: 0.25rem 0 1rem;
		padding: 1rem 1.1rem 1.1rem;
		border-radius: 20px;
		background: var(--brand);
		color: var(--brand-fg);
	}

	.featured:focus-within {
		outline: 3px solid var(--focus);
		outline-offset: 2px;
	}

	.type-pill {
		margin-bottom: 0.15rem;
	}

	.title {
		font-family: var(--font-display);
		font-weight: 600;
		font-size: 1.5rem;
		line-height: 1.15;
		color: var(--brand-fg);
		text-decoration: none;
		overflow-wrap: anywhere;
	}

	/* The whole card is one tap target. */
	.title::after {
		content: '';
		position: absolute;
		inset: 0;
		border-radius: 20px;
	}

	.title:hover {
		text-decoration: underline;
		text-underline-offset: 0.15em;
	}

	.title:focus-visible {
		outline: none;
	}

	.dates {
		font-weight: 600;
	}

	.meta {
		color: var(--brand-muted);
		font-size: 0.9rem;
	}
</style>
