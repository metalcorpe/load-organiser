<script lang="ts">
	import Disclosure from '#lib/components/Disclosure.svelte';
	import ExploreSwitch from '#lib/components/ExploreSwitch.svelte';
	import { afterNavigate } from '$app/navigation';
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
		groupByMonth,
		pickFeatured
	} from '#lib/listings.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const countryOptions = $derived(coverageOptions(data.countries, data.filters.country));
	const filtered = $derived(hasFilters(data.filters));
	// "To" before "From": the visitor's own mistake, answered in the filters (field marked,
	// panel open, every value kept), unlike a service failure, which is about the results.
	const dateError = $derived(!data.result.ok && data.result.kind === 'invalid');
	// With JavaScript, the date to correct takes focus after each search (a GET form navigates
	// client-side) and is scrolled near the top of the screen, so the field and the error
	// under it stay clear of the sticky "Show listings" button and the tab bar, even with
	// large text. Without it, `autofocus` focuses it on load.
	afterNavigate(() => {
		if (!dateError) return;
		const field = document.getElementById('to');
		if (!field) return;
		field.focus({ preventScroll: true });
		// The label, field and error together when they fit above the sticky parts; else
		// the field itself at the top, the error right under it.
		const wrapper = field.closest('.field') ?? field;
		const error = document.getElementById('dates-error') ?? field;
		const apply = document.querySelector('.board-search .apply');
		const nav = document.querySelector('nav[aria-label="Primary"]');
		const covered =
			(apply?.getBoundingClientRect().height ?? 0) +
			(nav && getComputedStyle(nav).position === 'fixed' ? nav.getBoundingClientRect().height : 0);
		const span = error.getBoundingClientRect().bottom - wrapper.getBoundingClientRect().top;
		(span + 24 <= innerHeight - covered ? wrapper : field).scrollIntoView({ block: 'start' });
	});
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
	// Under month headings by start month, so the date order reads at a glance. A month that runs
	// on to the next page starts that page with its heading again.
	const months = $derived(groupByMonth(listed));
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
<!-- One short introduction. For guests it ends with what an account adds; Join and Sign in
     are in the header. -->
<p class="lede intro">
	Boogies, camps, courses and other events in Europe. You register with the organizer{#if !data.viewer}<span
			class="account-note"
			>; an account lets you save events and keep a private logbook</span
		>{/if}.
</p>

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
		<button class="button secondary" type="submit">Search</button>
	</div>
	<!-- Disclosure: its open state is the server's, then the visitor's; nothing on the page
	     closes a panel the visitor opened. -->
	<Disclosure class="more" summaryClass="disclosure" open={dateError}>
		{#snippet summary()}Filters{chips.length ? ` (${chips.length})` : ''}{/snippet}
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
						<!-- svelte-ignore a11y_autofocus -->
						<input
							id="to"
							name="to"
							type="date"
							defaultValue={data.filters.to}
							aria-invalid={dateError ? 'true' : undefined}
							aria-describedby={dateError ? 'dates-error dates-hint' : 'dates-hint'}
							autofocus={dateError}
						/>
					</div>
				</div>
				<!-- Under both dates, full width: either date can be the one to change. -->
				{#if dateError}
					<p class="field-error" id="dates-error">
						“To” is before “From”. Choose a “To” date on or after
						{formatDay(data.filters.from)}, or an earlier “From” date.
					</p>
				{/if}
				<p class="hint" id="dates-hint">
					Shows every event that overlaps these dates, including ones that start earlier or end
					later.
				</p>
			</fieldset>
			<Disclosure class="secondary" open={moreActive > 0}>
				{#snippet summary()}Type, discipline and audience{moreActive ? ` (${moreActive})` : ''}{/snippet}
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
			</Disclosure>
			<!-- Stays in reach at the bottom of the screen while the panel is taller than it. -->
			<div class="form-actions apply" class:with-nav={Boolean(data.viewer)}>
				<button class="button" type="submit">Show listings</button>
			</div>
		</div>
	</Disclosure>
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

{#if !data.result.ok && data.result.kind === 'invalid'}
	<!-- Not an alert: the field itself carries the error and has focus. A pointer for anyone
	     who scrolls here, also without JavaScript. -->
	<p class="dates-note">
		No listings shown until the dates are corrected. <a href="#to">Correct the “To” date</a>
	</p>
{:else if !data.result.ok && data.result.kind === 'stale'}
	<!-- A page link that no longer works: start this search again from its first page. -->
	<p class="dates-note">
		This page link is out of date. <a href={boardHref(data.filters)}>Show the first page</a>
	</p>
{:else if !data.result.ok}
	<Notice title="Listings could not be loaded" tone="bad">
		<p role="alert">{listingMessage(data.result.reason)}</p>
		<p>Your search is kept. <a href={here} data-sveltekit-reload>Try again</a></p>
	</Notice>
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
	{/if}
	<section class="by-month" aria-label="Listings">
		<!-- Shown under the highlight; otherwise the page heading says it, so only screen readers get it. -->
		<h2 class="list-heading" class:visually-hidden={!featured}>
			{featured ? 'Other events, by date' : 'Events by date'}
		</h2>
		{#each months as month (month.key)}
			<h3 class="month" id="month-{month.key}">{month.label}</h3>
			<ul class="results cards" aria-labelledby="month-{month.key}">
				{#each month.items as item (item.id)}
					<li><ListingItem {item} results={here} /></li>
				{/each}
			</ul>
		{/each}
	</section>
	<nav class="pager" aria-label="More listings">
		{#if data.paged}<a href={boardHref(data.filters)}>First page</a>{/if}
		{#if data.result.nextCursor}
			<a href={boardHref(data.filters, data.result.nextCursor)} rel="next">More listings</a>
		{/if}
	</nav>
{/if}

<p class="aside">Looking for a dropzone? <a href="/dz">Browse dropzones</a>.</p>

<style>
	/* The heading and introduction sit close together so the first events show early on a phone. */
	h1 {
		margin: 0 0 0.25rem;
	}

	.intro {
		max-width: 44rem;
		margin: 0 0 0.75rem;
	}

	.account-note {
		font-size: 0.95em;
	}

	.board-search {
		margin: 0 0 0.25rem;
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

	/* The panels are rendered by Disclosure, hence :global inside the search form. */
	.board-search :global(details.more) {
		margin-top: 0.25rem;
	}

	.board-search :global(details.more[open]) {
		margin-bottom: 0.75rem;
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
	.board-search :global(details.secondary),
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

	/* Room above the date scrolled to after a "to before from" error. */
	.dates .field,
	.dates input {
		scroll-margin-top: 0.75rem;
	}

	.dates {
		display: grid;
		align-items: start;
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
		gap: 0.5rem 0.6rem;
		list-style: none;
		padding: 0;
		margin: 0 0 0.5rem;
	}

	/* Compact pills with a 44px tap target: the target reaches 4px above and below. */
	.chip {
		display: inline-flex;
		position: relative;
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

	.chip::after {
		content: '';
		position: absolute;
		inset: -4px 0;
	}

	.chips li > a:not(.chip) {
		display: inline-flex;
		align-items: center;
		min-height: 44px;
	}

	.chip span[aria-hidden] {
		color: var(--accent);
		font-weight: 700;
	}

	.dates-note {
		margin: 0.5rem 0 1rem;
		color: var(--muted);
	}

	.list-heading {
		font-size: 1.15rem;
		margin: 0 0 0.25rem;
	}

	/* Month headings: smaller than the list heading, a clear break between months. */
	.month {
		margin: 1rem 0 0.4rem;
		font-family: var(--font-display);
		font-size: 1rem;
		font-weight: 600;
	}

	.list-heading + .month {
		margin-top: 0.25rem;
	}

	.month + .results.cards {
		margin-top: 0;
	}

	.pager {
		display: flex;
		gap: 1rem;
		margin: 1rem 0;
	}

	.aside {
		color: var(--muted);
	}

	/* Large screens: the search keeps a readable length, the open filters lie in one band of
	   columns, and the events run in two columns. Cards fill row by row, so the reading order
	   (left, right, next row) is still the date order and the page order. */
	@media (min-width: 60rem) {
		.search-row {
			max-width: 44rem;
		}

		.filters {
			grid-template-columns: repeat(3, minmax(0, 1fr));
			align-items: start;
		}

		.when {
			grid-column: span 2;
		}

		.secondary-fields {
			grid-template-columns: repeat(3, minmax(0, 1fr));
		}

		.results.cards {
			grid-template-columns: repeat(2, minmax(0, 1fr));
		}

		.results.cards > li {
			display: grid;
		}
	}
</style>
