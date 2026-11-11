<script lang="ts">
	import type { OpportunityOut } from '#lib/contracts/index.ts';
	import TypeIcon from '#lib/components/TypeIcon.svelte';
	import { countryName } from '#lib/countries.ts';
	import {
		CATEGORY_LABEL,
		dateStub,
		formatPrice,
		formatRange,
		spanDays,
		statusLabel
	} from '#lib/listings.ts';

	let { item }: { item: OpportunityOut } = $props();
	const status = $derived(statusLabel(item.status, item.ended));
	const stub = $derived(dateStub(item.starts_on, item.ends_on));
	const days = $derived(spanDays(item.starts_on, item.ends_on));
	const place = $derived(item.venue ? item.venue.name : (item.location_note ?? ''));
	// The organizer only when it adds something the place name does not already say.
	const organizer = $derived(
		item.provider && !place.toLowerCase().includes(item.provider.name.toLowerCase())
			? item.provider.name
			: null
	);
	const price = $derived(formatPrice(item.price_amount, item.price_currency, item.price_basis));
</script>

<article
	class="listing type-{item.category}"
	class:muted={item.status === 'cancelled' || item.ended}
>
	<div class="tile" aria-hidden="true">
		{#if stub}
			<span class="month">{stub.month}</span>
			<span class="day">{stub.day}</span>
		{:else}
			<span class="tba">TBA</span>
		{/if}
	</div>
	<div class="body">
		<p class="kind">
			<span class="type-tag"
				><TypeIcon category={item.category} />{CATEGORY_LABEL[item.category]}{days > 1
					? ` · ${days} days`
					: ''}</span
			>
			{#if status}<span class="badge status">{status}</span>{/if}
			<span class="visually-hidden">{formatRange(item.starts_on, item.ends_on)}</span>
		</p>
		<a class="title" href="/events/{item.id}">{item.title}</a>
		<p class="line">
			{place ? `${place}, ` : ''}{countryName(item.country)}{organizer ? ` · by ${organizer}` : ''}
		</p>
		{#if price}<p class="line price">{price}</p>{/if}
	</div>
</article>

<style>
	.listing {
		position: relative;
		flex: 1 1 100%;
		display: grid;
		grid-template-columns: 3.6rem 1fr;
		gap: 0.9rem;
		align-items: center;
		padding: 0.65rem;
		border-radius: var(--radius);
		background: var(--surface);
		box-shadow: 0 0 0 1px var(--border);
	}

	.listing:hover {
		box-shadow: 0 0 0 1px var(--accent);
	}

	.listing:focus-within {
		outline: 3px solid var(--focus);
		outline-offset: 2px;
	}

	/* Cancelled or ended: neutral colours instead of opacity, so text keeps its contrast. */
	.muted .tile {
		background: var(--surface-soft);
		color: var(--muted);
	}

	.muted .title {
		color: var(--muted);
	}

	/* The type's tint, carrying the start date. */
	.tile {
		display: grid;
		justify-items: center;
		align-content: center;
		min-height: 3.75rem;
		border-radius: 12px;
		background: var(--type-bg);
		color: var(--type-fg);
		line-height: 1;
	}

	.month {
		font-size: 0.78rem;
		font-weight: 600;
	}

	.day {
		font-family: var(--font-display);
		font-weight: 700;
		font-size: 1.6rem;
		font-variant-numeric: tabular-nums;
	}

	.tba {
		font-family: var(--font-display);
		font-weight: 700;
		font-size: 1rem;
	}

	.body {
		display: grid;
		gap: 0.2rem;
		min-width: 0;
	}

	p {
		margin: 0;
	}

	.kind {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.4rem;
	}

	.title {
		font-weight: 600;
		font-size: 1.02rem;
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

	.line {
		color: var(--muted);
		font-size: 0.9rem;
		overflow-wrap: anywhere;
	}

	.price {
		color: var(--fg);
	}
</style>
