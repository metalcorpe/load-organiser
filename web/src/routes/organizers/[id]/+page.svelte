<script lang="ts">
	import ListingDetails from '#lib/components/ListingDetails.svelte';
	import ListingItem from '#lib/components/ListingItem.svelte';
	import { countryName } from '#lib/countries.ts';
	import { hostOf, listingMessage } from '#lib/listings.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const provider = $derived(data.provider);
	// What kind of organizer, and where: a plain description, never a title or qualification.
	const lede = $derived(
		[
			provider.kind === 'person' ? 'Individual organizer' : 'Organization',
			provider.country ? `based in ${countryName(provider.country)}` : null
		]
			.filter(Boolean)
			.join(', ')
	);
</script>

<svelte:head>
	<title>{provider.name} · Organizers · Load Organiser</title>
	<meta name="description" content="Upcoming skydiving events from {provider.name}." />
</svelte:head>

<p><a href="/">All events</a></p>
<h1>{provider.name}</h1>
<p class="lede">{lede}</p>

{#if provider.website_url}
	<p class="contact">
		<a class="button" href={provider.website_url} rel="external noopener noreferrer nofollow"
			>Visit website</a
		>
		<span class="hint">Opens <span class="wrap-anywhere">{hostOf(provider.website_url)}</span></span>
	</p>
{/if}

<h2>Upcoming events</h2>
{#if !data.listings.ok}
	<p class="form-error" role="alert">{listingMessage(data.listings.reason)}</p>
{:else if data.listings.items.length === 0}
	<p>No upcoming events from this organizer are listed.</p>
{:else}
	<ul class="results cards" aria-label="Upcoming events">
		{#each data.listings.items as item (item.id)}
			<li><ListingItem {item} /></li>
		{/each}
	</ul>
	{#if data.listings.more}<p class="hint">Showing the first 20.</p>{/if}
{/if}

<ListingDetails
	sourceUrl={provider.source_url}
	checkedOn={provider.checked_on}
	note="Listed from public information. The organizer does not run this page, and no qualifications or affiliations are checked."
/>
<p class="correction">
	<a
		href="/submit?kind=correction&target_kind=provider&target_id={provider.id}&title={encodeURIComponent(
			provider.name
		)}">Suggest a correction</a
	>
</p>

<style>
	.contact {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.5rem 1rem;
	}
</style>
