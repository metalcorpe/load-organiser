<script lang="ts">
	import type { OpportunityOut } from '#lib/contracts/index.ts';
	import { countryName } from '#lib/countries.ts';
	import { CATEGORY_LABEL, formatRange, statusLabel } from '#lib/listings.ts';

	let { item }: { item: OpportunityOut } = $props();
	const status = $derived(statusLabel(item.status, item.ended));
	const place = $derived(item.venue ? item.venue.name : (item.location_note ?? ''));
</script>

<a class="title" href="/events/{item.id}">{item.title}</a>
<span class="meta">
	{CATEGORY_LABEL[item.category]} · {formatRange(item.starts_on, item.ends_on)}
</span>
<span class="meta">
	{place ? `${place}, ` : ''}{countryName(item.country)}{item.provider
		? ` · ${item.provider.name}`
		: ''}
</span>
{#if status}<span class="tag">{status}</span>{/if}

<style>
	.title {
		font-weight: 600;
		flex-basis: 100%;
		overflow-wrap: anywhere;
	}

	.meta {
		color: var(--muted);
		flex-basis: 100%;
		overflow-wrap: anywhere;
	}
</style>
