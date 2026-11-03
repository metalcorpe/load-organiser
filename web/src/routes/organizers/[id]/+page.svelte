<script lang="ts">
	import ListingItem from '#lib/components/ListingItem.svelte';
	import { countryName } from '#lib/countries.ts';
	import { formatDay, hostOf, listingMessage } from '#lib/listings.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const provider = $derived(data.provider);
</script>

<svelte:head>
	<title>{provider.name} · Organizers · Load Organiser</title>
	<meta name="description" content="{provider.name}. Source-backed organizer listing." />
</svelte:head>

<p><a href="/">All listings</a></p>
<h1>{provider.name}</h1>
<p class="lede">{provider.kind === 'person' ? 'Coach or individual organizer' : 'Organization'}</p>

<dl>
	{#if provider.country}
		<dt>Based in</dt>
		<dd>{countryName(provider.country)}</dd>
	{/if}
	{#if provider.website_url}
		<dt>Website</dt>
		<dd>
			<a href={provider.website_url} rel="external noopener noreferrer nofollow"
				>{hostOf(provider.website_url)}</a
			>
		</dd>
	{/if}
	<dt>Source</dt>
	<dd>
		<a href={provider.source_url} rel="external noopener noreferrer nofollow"
			>{hostOf(provider.source_url)}</a
		>
		{#if provider.source_note}<span class="hint">({provider.source_note})</span>{/if}
	</dd>
	<dt>Last checked</dt>
	<dd>{formatDay(provider.checked_on)}</dd>
</dl>

<p class="hint">
	Listed from public sources. This does not confirm qualifications, ratings or affiliations, and it
	does not mean the organizer manages this page.
</p>

<h2>Upcoming listings</h2>
{#if !data.listings.ok}
	<p class="form-error" role="alert">{listingMessage(data.listings.reason)}</p>
{:else if data.listings.items.length === 0}
	<p>No upcoming listings from this organizer are published here.</p>
{:else}
	<ul class="results" aria-label="Upcoming listings">
		{#each data.listings.items as item (item.id)}
			<li><ListingItem {item} /></li>
		{/each}
	</ul>
	{#if data.listings.more}<p class="hint">Showing the first 20.</p>{/if}
{/if}

<style>
	dl {
		display: grid;
		grid-template-columns: max-content 1fr;
		gap: 0.35rem 1rem;
		margin: 1rem 0;
	}

	dt {
		color: var(--muted);
	}

	dd {
		margin: 0;
		overflow-wrap: anywhere;
	}
</style>
