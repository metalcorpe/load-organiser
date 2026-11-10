<script lang="ts">
	import { page } from '$app/state';
	import ListingItem from '#lib/components/ListingItem.svelte';
	import Notice from '#lib/components/Notice.svelte';
	import { coverageOptions } from '#lib/countries.ts';
	import {
		AUDIENCE_VALUES,
		CATEGORY_VALUES,
		DISCIPLINE_VALUES,
		boardHref,
		hasFilters
	} from '#lib/listing-filters.ts';
	import { AUDIENCE_LABEL, CATEGORY_LABEL, DISCIPLINE_LABEL, listingMessage } from '#lib/listings.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const countryOptions = $derived(coverageOptions(data.countries, data.filters.country));
	const filtered = $derived(hasFilters(data.filters));
</script>

<svelte:head>
	<title>Discover · Load Organiser</title>
	<meta
		name="description"
		content="Dated skydiving events, boogies, camps and courses in Europe, linked to their organizers' own pages."
	/>
</svelte:head>

<h1>Discover</h1>
<p class="lede">
	Dated skydiving events, boogies, camps and courses, each linked to its organizer's own page.
	Listings come from reviewed sources; registration and availability are always with the organizer.
</p>

<!-- defaultValue keeps text typed before hydration; the key resets the fields when
     the URL's filters change (Clear filters, back/forward). -->
{#key page.url.search}
<form method="GET" class="form filters" role="search">
	<div class="field wide">
		<label for="q">Title or organizer</label>
		<input id="q" name="q" type="search" maxlength="80" defaultValue={data.filters.q} autocomplete="off" />
	</div>
	<div class="field">
		<label for="category">Type</label>
		<select id="category" name="category">
			<option value="" selected={!data.filters.category}>Any type</option>
			{#each CATEGORY_VALUES as value (value)}
				<option {value} selected={value === data.filters.category}>{CATEGORY_LABEL[value]}</option>
			{/each}
		</select>
	</div>
	<div class="field">
		<label for="country">Country</label>
		<select id="country" name="country">
			<option value="" selected={!data.filters.country}>Any country</option>
			{#each countryOptions as option (option.code)}
				<option value={option.code} selected={option.code === data.filters.country}
					>{option.name}</option
				>
			{/each}
		</select>
	</div>
	<div class="field">
		<label for="discipline">Discipline</label>
		<select id="discipline" name="discipline">
			<option value="" selected={!data.filters.discipline}>Any discipline</option>
			{#each DISCIPLINE_VALUES as value (value)}
				<option {value} selected={value === data.filters.discipline}>{DISCIPLINE_LABEL[value]}</option>
			{/each}
		</select>
	</div>
	<div class="field">
		<label for="audience">Intended for</label>
		<select id="audience" name="audience">
			<option value="" selected={!data.filters.audience}>Anyone</option>
			{#each AUDIENCE_VALUES as value (value)}
				<option {value} selected={value === data.filters.audience}>{AUDIENCE_LABEL[value]}</option>
			{/each}
		</select>
	</div>
	<div class="field">
		<label for="from">Ending on or after</label>
		<input id="from" name="from" type="date" defaultValue={data.filters.from} />
	</div>
	<div class="field">
		<label for="to">Starting on or before</label>
		<input id="to" name="to" type="date" defaultValue={data.filters.to} />
	</div>
	<div class="form-actions wide">
		<button class="button" type="submit">Show listings</button>
		{#if filtered}<a href="/">Clear filters</a>{/if}
	</div>
</form>
{/key}

{#if !data.result.ok}
	<p class="form-error" role="alert">{listingMessage(data.result.reason)}</p>
{:else if data.result.items.length === 0}
	<Notice title={filtered ? 'No listings match' : 'No listings published yet'} tone="warn">
		<p>
			{#if filtered}
				Nothing upcoming matches these filters. Coverage is limited to reviewed, source-backed
				listings, so this does not mean nothing is happening.
			{:else}
				Listings appear only after a source has been reviewed. Nothing here represents real
				availability.
			{/if}
		</p>
		<p>
			{#if filtered}<a href="/">Clear filters</a> · {/if}<a href="/submit?kind=suggest_listing"
				>Suggest a listing</a
			>
		</p>
	</Notice>
{:else}
	<ul class="results" aria-label="Listings">
		{#each data.result.items as item (item.id)}
			<li><ListingItem {item} /></li>
		{/each}
	</ul>
	<nav class="pager" aria-label="More listings">
		{#if data.paged}<a href={boardHref(data.filters)}>First page</a>{/if}
		{#if data.result.nextCursor}
			<a href={boardHref(data.filters, data.result.nextCursor)} rel="next">More listings</a>
		{/if}
	</nav>
{/if}

<p>
	Looking for a dropzone? Browse the <a href="/dz">dropzone directory</a> of source-backed listings.
</p>

<style>
	.filters {
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 12rem), 1fr));
		margin-bottom: 1rem;
	}

	.wide {
		grid-column: 1 / -1;
	}

	.pager {
		display: flex;
		gap: 1rem;
		margin: 1rem 0;
	}
</style>
