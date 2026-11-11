<script lang="ts">
	import '@fontsource/barlow-condensed/latin-700.css';
	import type { OpportunityOut } from '#lib/contracts/index.ts';
	import { countryName } from '#lib/countries.ts';
	import { CATEGORY_LABEL, dateStub, formatPrice, formatRange, statusLabel } from '#lib/listings.ts';

	let { item }: { item: OpportunityOut } = $props();
	const status = $derived(statusLabel(item.status, item.ended));
	const stub = $derived(dateStub(item.starts_on, item.ends_on));
	const place = $derived(item.venue ? item.venue.name : (item.location_note ?? ''));
	// The organizer only when it adds something the place name does not already say.
	const organizer = $derived(
		item.provider && !place.toLowerCase().includes(item.provider.name.toLowerCase())
			? item.provider.name
			: null
	);
	const price = $derived(formatPrice(item.price_amount, item.price_currency, item.price_basis));
</script>

<article class="listing" class:muted={item.status === 'cancelled' || item.ended}>
	<div class="stub" aria-hidden="true">
		{#if stub}
			<span class="month">{stub.month}</span>
			<span class="day">{stub.day}</span>
			{#if stub.until}<span class="until">{stub.until}</span>{/if}
		{:else}
			<span class="tba">TBA</span>
		{/if}
	</div>
	<div class="body">
		<a class="title" href="/events/{item.id}">{item.title}</a>
		<p class="when">
			<span class="badge">{CATEGORY_LABEL[item.category]}</span>
			{#if status}<span class="badge status">{status}</span>{/if}
			<span class="visually-hidden">{formatRange(item.starts_on, item.ends_on)}</span>
		</p>
		<p class="line">{place ? `${place}, ` : ''}{countryName(item.country)}</p>
		{#if organizer}<p class="line">By {organizer}</p>{/if}
		{#if price}<p class="line price">{price}</p>{/if}
	</div>
</article>

<style>
	.listing {
		position: relative;
		flex: 1 1 100%;
		display: grid;
		grid-template-columns: 4.25rem 1fr;
		gap: 0.9rem;
		align-items: start;
		padding: 0.85rem;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		background: var(--surface);
	}

	.listing:hover {
		border-color: var(--accent);
	}

	.listing:focus-within {
		outline: 3px solid var(--focus);
		outline-offset: 2px;
	}

	.muted .stub,
	.muted .title {
		opacity: 0.65;
	}

	/* The manifest-board stub: the one place the condensed face appears. */
	.stub {
		display: grid;
		justify-items: center;
		align-content: center;
		min-height: 4.25rem;
		padding: 0.35rem 0.2rem;
		border-radius: 8px;
		background: var(--accent-soft);
		color: var(--fg);
		font-family: 'Barlow Condensed', system-ui, sans-serif;
		font-weight: 700;
		line-height: 1;
		text-align: center;
	}

	.month {
		font-size: 0.95rem;
		color: var(--accent);
	}

	.day {
		font-size: 1.9rem;
		font-variant-numeric: tabular-nums;
	}

	.until {
		font-size: 0.95rem;
		color: var(--muted);
	}

	.tba {
		font-size: 1.2rem;
		color: var(--muted);
	}

	.body {
		display: grid;
		gap: 0.2rem;
		min-width: 0;
	}

	.title {
		font-weight: 650;
		font-size: 1.05rem;
		line-height: 1.3;
		color: var(--fg);
		text-decoration: none;
		overflow-wrap: anywhere;
	}

	/* The title link covers the whole card, so the card is one tap target. */
	.title::after {
		content: '';
		position: absolute;
		inset: 0;
		border-radius: var(--radius);
	}

	.title:focus-visible {
		outline: none;
	}

	p {
		margin: 0;
	}

	.when {
		display: flex;
		flex-wrap: wrap;
		gap: 0.35rem;
		margin: 0.15rem 0;
	}

	.line {
		color: var(--muted);
		font-size: 0.95rem;
		overflow-wrap: anywhere;
	}

	.price {
		color: var(--fg);
	}
</style>
