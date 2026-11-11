<script lang="ts">
	import ExploreSwitch from '#lib/components/ExploreSwitch.svelte';
	import { page } from '$app/state';
	import FeaturedListing from '#lib/components/FeaturedListing.svelte';
	import ListingItem from '#lib/components/ListingItem.svelte';
	import Notice from '#lib/components/Notice.svelte';
	import { countryName, coverageOptions } from '#lib/countries.ts';
	import {
		AUDIENCE_VALUES,
		CATEGORY_VALUES,
		DISCIPLINE_VALUES,
		boardHref,
		hasFilters
	} from '#lib/listing-filters.ts';
	import {
		AUDIENCE_LABEL,
		CATEGORY_LABEL,
		DISCIPLINE_LABEL,
		formatDay,
		listingMessage,
		spanDays
	} from '#lib/listings.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const countryOptions = $derived(coverageOptions(data.countries, data.filters.country));
	const filtered = $derived(hasFilters(data.filters));
	// On the plain first page, the next multi-day boogie or camp gets the navy card and is not
	// repeated in the list.
	const featured = $derived(
		!filtered && !data.paged && data.result.ok && data.result.items.length > 1
			? (data.result.items.find(
					(i) =>
						(i.category === 'boogie' || i.category === 'camp') &&
						i.status === 'published' &&
						spanDays(i.starts_on, i.ends_on) > 1 &&
						// "Next big one" means not started yet (UTC date; good enough for a label).
						(i.starts_on ?? '') > new Date().toISOString().slice(0, 10)
				) ?? null)
			: null
	);
	const listed = $derived(
		data.result.ok ? data.result.items.filter((i) => i.id !== featured?.id) : []
	);
	// Each active filter (other than the search text) as a chip that removes just that filter.
	const chips = $derived(
		[
			['category', data.filters.category && CATEGORY_LABEL[data.filters.category]],
			['country', data.filters.country && countryName(data.filters.country)],
			['discipline', data.filters.discipline && DISCIPLINE_LABEL[data.filters.discipline]],
			['audience', data.filters.audience && AUDIENCE_LABEL[data.filters.audience]],
			['from', data.filters.from && `Ending on or after ${formatDay(data.filters.from)}`],
			['to', data.filters.to && `Starting by ${formatDay(data.filters.to)}`]
		]
			.filter(([, label]) => label)
			.map(([key, label]) => ({
				key: key as string,
				label: label as string,
				href: boardHref({ ...data.filters, [key as string]: '' })
			}))
	);
</script>

<svelte:head>
	<title>Events · Load Organiser</title>
	<meta
		name="description"
		content="Dated skydiving events, boogies, camps and courses in Europe, linked to their organizers' own pages."
	/>
</svelte:head>

<ExploreSwitch />
<h1>Events</h1>
<p class="lede">Dated events, boogies, camps and courses. Register on the organizer's site.</p>
{#if !data.viewer}
	<p class="join-line">
		Members also keep a private logbook, gear and history, and save events.
		<a href="/register">Join</a> or <a href="/sign-in?returnTo=%2F" data-sign-in>sign in</a>.
	</p>
{/if}

<!-- defaultValue keeps text typed before hydration; the key resets the fields when
     the URL's filters change (Clear filters, back/forward). -->
{#key page.url.search}
<form method="GET" class="board-search" role="search">
	<div class="search-row">
		<label class="visually-hidden" for="q">Title or organizer</label>
		<input
			id="q"
			name="q"
			type="search"
			maxlength="80"
			placeholder="Search titles or organizers"
			defaultValue={data.filters.q}
			autocomplete="off"
		/>
		<button class="button" type="submit">Search</button>
	</div>
	<details class="more">
		<summary class="disclosure">Filters{chips.length ? ` (${chips.length})` : ''}</summary>
		<div class="form filters">
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
						<option {value} selected={value === data.filters.discipline}
							>{DISCIPLINE_LABEL[value]}</option
						>
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
			</div>
		</div>
	</details>
</form>
{/key}

{#if chips.length}
	<ul class="chips" aria-label="Active filters">
		{#each chips as chip (chip.key)}
			<li>
				<a class="chip" href={chip.href} aria-label="Remove {chip.label}"
					>{chip.label}<span aria-hidden="true">×</span></a
				>
			</li>
		{/each}
		<li><a href="/">Clear filters</a></li>
	</ul>
{/if}

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
	{#if featured}
		<FeaturedListing item={featured} />
		<h2 class="list-heading">Coming up</h2>
	{/if}
	<ul class="results cards" aria-label="Listings">
		{#each listed as item (item.id)}
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

<p class="aside">Looking for a dropzone? <a href="/dz">Browse dropzones</a>.</p>

<style>
	.board-search {
		margin: 0.5rem 0 0.25rem;
	}

	.search-row {
		display: flex;
		gap: 0.5rem;
	}

	.search-row input {
		flex: 1;
		min-width: 0;
		min-height: 44px;
		padding: 0.5rem 0.75rem;
		border: 1px solid var(--field-border);
		border-radius: 9px;
		background: var(--field);
		color: var(--fg);
		font: inherit;
	}

	.more {
		margin-top: 0.25rem;
	}

	.filters {
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 12rem), 1fr));
		margin: 0.25rem 0 0;
		padding: 0.85rem;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		background: var(--surface);
	}

	.wide {
		grid-column: 1 / -1;
	}

	.chips {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.4rem 0.6rem;
		list-style: none;
		padding: 0;
		margin: 0 0 0.5rem;
	}

	.chip {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		min-height: 36px;
		padding: 0.2rem 0.7rem;
		border-radius: 999px;
		background: var(--accent-soft);
		color: var(--fg);
		font-size: 0.9rem;
		text-decoration: none;
	}

	.chip span[aria-hidden] {
		color: var(--accent);
		font-weight: 700;
	}

	.join-line {
		margin: -0.25rem 0 0.75rem;
		color: var(--muted);
	}

	.list-heading {
		font-size: 1.15rem;
		margin: 0 0 0.25rem;
	}

	.pager {
		display: flex;
		gap: 1rem;
		margin: 1rem 0;
	}

	.aside {
		color: var(--muted);
	}
</style>
