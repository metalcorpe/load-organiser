<script lang="ts">
	import JumpCard from '#lib/components/JumpCard.svelte';
	import ListingDetails from '#lib/components/ListingDetails.svelte';
	import ListingItem from '#lib/components/ListingItem.svelte';
	import Notice from '#lib/components/Notice.svelte';
	import PrivacyLabel from '#lib/components/PrivacyLabel.svelte';
	import { formatDay, listingMessage } from '#lib/listings.ts';
	import { countryName } from '#lib/countries.ts';
	import { formatCoordinates, osmLink } from '#lib/dz-map.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const venue = $derived(data.venue);

	const KIND_LABEL = { former: 'Former name', alternate: 'Also known as', merged: 'Merged listing' };

	// One website action: with exactly one operator link it is "Visit website" and the name
	// above stays plain text; with several, each name links to its own site instead.
	const websites = $derived(venue.operators.filter((o) => o.url));
	const website = $derived(websites.length === 1 ? websites[0].url : null);
	const place = $derived([venue.locality, countryName(venue.country)].filter(Boolean).join(', '));
	const correctionHref = $derived(
		`/submit?kind=correction&target_kind=venue&target_id=${venue.id}&title=${encodeURIComponent(venue.name)}`
	);
</script>

<svelte:head>
	<title>{venue.name} · Dropzones · Load Organiser</title>
	<meta name="description" content="{venue.name}: skydiving dropzone in {place}." />
</svelte:head>

<p><a href="/dz">All dropzones</a></p>
<h1>{venue.name}</h1>
<p class="lede">{place}</p>

{#if venue.status === 'closed'}
	<Notice title="Closed" tone="warn">
		<p>This dropzone is listed as closed. Jumps logged here stay in logbooks.</p>
	</Notice>
{/if}

{#if data.mine}
	<!-- The signed-in reader's own logbook; never computed for guests. -->
	<section class="mine" aria-label="Your jumps here">
		<PrivacyLabel text="Only you can see this" />
		<p>
			{#if data.mine.count > 0}
				You logged <a href="/jumps?at=venue:{venue.id}"
					>{data.mine.count.toLocaleString('en-GB')} {data.mine.count === 1 ? 'jump' : 'jumps'}</a
				>
				here{#if data.mine.lastOn}, last on {formatDay(data.mine.lastOn)}{/if}.
			{:else}
				You have not logged a jump here yet.
			{/if}
		</p>
		<a class="button" href="/jumps/new?venue={venue.id}">Log a jump here</a>
	</section>
{/if}

<dl>
	{#if venue.operators.length}
		<dt>Run by</dt>
		<dd>
			{#each venue.operators as operator, i (operator.name)}{#if i}{', '}{/if}{#if operator.url && !website}<a
						href={operator.url}
						rel="external noopener noreferrer nofollow">{operator.name}</a
					>{:else}{operator.name}{/if}{/each}
		</dd>
	{/if}
	{#if venue.season}
		<dt>Season</dt>
		<dd>{venue.season}</dd>
	{/if}
	{#if venue.aircraft}
		<dt>Aircraft</dt>
		<dd>{venue.aircraft}</dd>
	{/if}
	{#if venue.latitude !== null && venue.longitude !== null}
		<dt>Coordinates</dt>
		<dd>
			{formatCoordinates(venue.latitude, venue.longitude)}
			<!-- A plain link: nothing from OpenStreetMap loads on this page. -->
			<br /><a href={osmLink(venue.latitude, venue.longitude)} rel="external noopener noreferrer"
				>Open in OpenStreetMap</a
			>
		</dd>
	{/if}
	{#each venue.aliases as alias (alias.kind + alias.name)}
		<dt>{KIND_LABEL[alias.kind]}</dt>
		<dd>{alias.name}</dd>
	{/each}
</dl>

{#if venue.status !== 'closed'}
	<section class="visit" aria-labelledby="visit-heading">
		<h2 id="visit-heading">Planning a visit?</h2>
		<p>Check opening dates and availability before travelling.</p>
		<p class="actions">
			{#if website}
				<a class="button" href={website} rel="external noopener noreferrer nofollow">Visit website</a>
			{/if}
			{#if data.viewer}
				<a class="button secondary" href="/plans?venue={venue.id}">Plan a visit</a>
			{/if}
			<a href={correctionHref}>Suggest a correction</a>
		</p>
	</section>
{/if}

<h2>Upcoming events here</h2>
{#if !data.listings.ok}
	<p class="form-error" role="alert">{listingMessage(data.listings.reason)}</p>
{:else if data.listings.items.length === 0}
	<p>No upcoming events listed here.</p>
{:else}
	<ul class="results cards" aria-label="Upcoming events here">
		{#each data.listings.items as item (item.id)}
			<li><ListingItem {item} /></li>
		{/each}
	</ul>
	{#if data.listings.more}<p class="hint">Showing the first 20.</p>{/if}
{/if}
<h2 id="shared-jumps">Shared jumps here</h2>
<p class="hint">
	Jumps people shared with this dropzone named, newest first.{data.viewer
		? ''
		: ' Sign in to see jumps shared with you.'}
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

<ListingDetails
	sourceUrl={venue.source_url}
	checkedOn={venue.checked_on}
	note="Listed from public information. The dropzone does not run this page."
/>
{#if venue.status === 'closed'}
	<p><a href={correctionHref}>Suggest a correction</a></p>
{/if}

<style>
	.mine {
		margin: 0.75rem 0 1rem;
		padding: 0.9rem 1rem;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		background: var(--surface);
	}

	.lede {
		margin: -0.25rem 0 0.75rem;
		color: var(--muted);
	}

	.visit {
		margin: 1.25rem 0;
		padding: 0.9rem 1rem;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		background: var(--surface);
	}

	.visit h2 {
		margin: 0 0 0.25rem;
		font-size: 1.1rem;
	}

	.visit p {
		margin: 0 0 0.5rem;
	}

	.actions {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.5rem 1rem;
	}

	.mine p {
		margin: 0.5rem 0 0.75rem;
	}

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
