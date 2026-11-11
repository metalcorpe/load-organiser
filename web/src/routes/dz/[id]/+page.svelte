<script lang="ts">
	import JumpCard from '#lib/components/JumpCard.svelte';
	import ListingItem from '#lib/components/ListingItem.svelte';
	import Notice from '#lib/components/Notice.svelte';
	import { listingMessage } from '#lib/listings.ts';
	import { countryName } from '#lib/countries.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const venue = $derived(data.venue);

	const KIND_LABEL = { former: 'Former name', alternate: 'Also known as', merged: 'Merged listing' };

	// A date-only value: format it as that calendar day, never shifted by a time zone.
	const checked = $derived(
		new Intl.DateTimeFormat('en-GB', { dateStyle: 'long', timeZone: 'UTC' }).format(
			new Date(`${venue.checked_on}T00:00:00Z`)
		)
	);
	const sourceHost = $derived(new URL(venue.source_url).hostname);
</script>

<svelte:head>
	<title>{venue.name} · Dropzones · Load Organiser</title>
	<meta
		name="description"
		content="{venue.name}, {countryName(venue.country)}. Source-backed directory listing."
	/>
</svelte:head>

<p><a href="/dz">All dropzones</a></p>
<h1>{venue.name}</h1>

{#if venue.status === 'closed'}
	<Notice title="Closed" tone="warn">
		<p>Kept as a historical listing so past records stay meaningful.</p>
	</Notice>
{/if}

<dl>
	<dt>Country</dt>
	<dd>{countryName(venue.country)}</dd>
	{#if venue.locality}
		<dt>Locality</dt>
		<dd>{venue.locality}</dd>
	{/if}
	{#if venue.latitude !== null && venue.longitude !== null}
		<dt>Coordinates</dt>
		<dd>{venue.latitude}, {venue.longitude}</dd>
	{/if}
	{#each venue.aliases as alias (alias.kind + alias.name)}
		<dt>{KIND_LABEL[alias.kind]}</dt>
		<dd>{alias.name}</dd>
	{/each}
	<dt>Source</dt>
	<dd>
		<a href={venue.source_url} rel="external noopener noreferrer nofollow">{sourceHost}</a>
		{#if venue.source_note}<span class="hint">({venue.source_note})</span>{/if}
	</dd>
	<dt>Last checked</dt>
	<dd>{checked}</dd>
</dl>

<p class="hint">
	This is a directory listing, maintained from the source above. It does not mean the dropzone
	endorses, operates with or has confirmed anything in Load Organiser, and jumps recorded here are
	the jumpers' own records.
</p>

<p>
	<a href="/submit?kind=correction&target_kind=venue&target_id={venue.id}&title={encodeURIComponent(venue.name)}"
		>Suggest a correction or report a problem</a
	>
</p>

<h2>Upcoming listings here</h2>
{#if !data.listings.ok}
	<p class="form-error" role="alert">{listingMessage(data.listings.reason)}</p>
{:else if data.listings.items.length === 0}
	<p>No upcoming listings at this dropzone are published here.</p>
{:else}
	<ul class="results cards" aria-label="Upcoming listings">
		{#each data.listings.items as item (item.id)}
			<li><ListingItem {item} /></li>
		{/each}
	</ul>
	{#if data.listings.more}<p class="hint">Showing the first 20.</p>{/if}
{/if}
{#if data.viewer}
	<p><a href="/plans?venue={venue.id}">Plan a private visit here</a></p>
{/if}

<h2 id="shared-jumps">Shared jumps here</h2>
<p class="hint">
	Jump summaries people chose to share with this dropzone named, newest publication first; each
	shows the date of the jump. Not a record of who is here now, and not a count of jumps.
	{data.viewer ? '' : 'Signed out, you see public posts only.'}
</p>
{#if data.posts === null}
	<p class="hint">Shared jumps are unavailable right now.</p>
{:else if data.posts.items.length === 0}
	<p>{data.olderPosts ? 'No older shared jumps here.' : 'No shared jumps here that you can see.'}</p>
{:else}
	<ul class="results" aria-label="Shared jumps here">
		{#each data.posts.items as post (post.id)}
			<li><JumpCard {post} /></li>
		{/each}
	</ul>
{/if}
{#if data.posts?.next_before}
	<p><a href="/dz/{venue.id}?before={data.posts.next_before}#shared-jumps">Older shared jumps</a></p>
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
