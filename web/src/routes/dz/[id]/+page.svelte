<script lang="ts">
	import Notice from '#lib/components/Notice.svelte';
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
