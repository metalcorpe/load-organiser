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
		pickFeatured
	} from '#lib/listings.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const countryOptions = $derived(coverageOptions(data.countries, data.filters.country));
	const filtered = $derived(hasFilters(data.filters));
	// This search (filters and page), carried into each event for "Back to results".
	const here = $derived(boardHref(data.filters, data.cursor || undefined));
	// On the plain first page, the next multi-day boogie or camp gets the navy card. It is taken
	// out of the dated list below rather than shown twice; the list's heading says so.
	// "Next" by UTC date: good enough for a label.
	const featured = $derived(
		!filtered && !data.paged && data.result.ok && data.result.items.length > 1
			? pickFeatured(data.result.items, new Date().toISOString().slice(0, 10))
			: null
	);
	const listed = $derived(
		data.result.ok ? data.result.items.filter((i) => i.id !== featured?.id) : []
	);
	// Type, discipline and audience fold away unless one of them is in use.
	const moreActive = $derived(
		[data.filters.category, data.filters.discipline, data.filters.audience].filter(Boolean).length
	);
	// Each active filter (other than the search text) as a chip that removes just that filter.
	// The dates keep the board's overlap rule: "from" = ending on or after, "to" = starting by.
	const chips = $derived(
		[
			['country', data.filters.country && countryName(data.filters.country)],
			['from', data.filters.from && `Available from ${formatDay(data.filters.from)}`],
			['to', data.filters.to && `Available until ${formatDay(data.filters.to)}`],
			['category', data.filters.category && CATEGORY_LABEL[data.filters.category]],
			['discipline', data.filters.discipline && DISCIPLINE_LABEL[data.filters.discipline]],
			['audience', data.filters.audience && AUDIENCE_LABEL[data.filters.audience]]
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
<p class="lede">Boogies, camps, courses and other events in Europe. You register with the organizer.</p>
{#if !data.viewer}
	<!-- Join and Sign in are in the header; this only says what an account adds. -->
	<p class="join-line">With an account you can save events and keep a private logbook.</p>
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
			<!-- Overlap, unchanged: "from" keeps events ending on or after it, "to" those starting
			     on or before it. -->
			<fieldset class="when">
				<legend>When are you available?</legend>
				<div class="dates">
					<div class="field">
						<label for="from">From</label>
						<input
							id="from"
							name="from"
							type="date"
							defaultValue={data.filters.from}
							aria-describedby="dates-hint"
						/>
					</div>
					<div class="field">
						<label for="to">To</label>
						<input
							id="to"
							name="to"
							type="date"
							defaultValue={data.filters.to}
							aria-describedby="dates-hint"
						/>
					</div>
				</div>
				<p class="hint" id="dates-hint">
					Shows every event that overlaps these dates, including ones that start earlier or end
					later.
				</p>
			</fieldset>
			<details class="secondary" open={moreActive > 0}>
				<summary>Type, discipline and audience{moreActive ? ` (${moreActive})` : ''}</summary>
				<div class="secondary-fields">
					<div class="field">
						<label for="category">Type</label>
						<select id="category" name="category">
							<option value="" selected={!data.filters.category}>Any type</option>
							{#each CATEGORY_VALUES as value (value)}
								<option {value} selected={value === data.filters.category}
									>{CATEGORY_LABEL[value]}</option
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
								<option {value} selected={value === data.filters.audience}
									>{AUDIENCE_LABEL[value]}</option
								>
							{/each}
						</select>
					</div>
				</div>
			</details>
			<!-- Stays in reach at the bottom of the screen while the panel is taller than it. -->
			<div class="form-actions apply" class:with-nav={Boolean(data.viewer)}>
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
		<h2 class="list-heading">Other events, by date</h2>
	{/if}
	<ul class="results cards" aria-label="Listings">
		{#each listed as item (item.id)}
			<li><ListingItem {item} results={here} /></li>
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

	.when,
	.secondary,
	.apply {
		grid-column: 1 / -1;
	}

	.when {
		display: grid;
		gap: 0.6rem;
		padding: 0;
		border: 0;
	}

	.when legend {
		padding: 0;
		margin-bottom: 0.4rem;
	}

	.dates {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 9.5rem), 1fr));
		gap: 0.75rem;
	}

	.secondary-fields {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 12rem), 1fr));
		gap: 1rem;
		padding-top: 0.25rem;
	}

	/* The apply button stays on screen while the open panel is taller than the screen; it
	   stops at the end of the panel, so it never sits over the results or the footer. */
	.apply {
		position: sticky;
		bottom: env(safe-area-inset-bottom);
		z-index: 1;
		margin: 0 -0.85rem -0.85rem;
		padding: 0.6rem 0.85rem;
		border-top: 1px solid var(--border);
		border-radius: 0 0 var(--radius) var(--radius);
		background: var(--surface);
	}

	/* Members' tab bar is fixed at the bottom on phones: sit just above it. */
	@media (max-width: 47.99rem) {
		.apply.with-nav {
			bottom: calc(var(--nav-height) + env(safe-area-inset-bottom));
		}
	}

	/* A field focused under the sticky button scrolls clear of it (and of the tab bar). */
	:global(html:has(.board-search details[open])) {
		scroll-padding-bottom: calc(var(--nav-height) + 5rem + env(safe-area-inset-bottom));
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
