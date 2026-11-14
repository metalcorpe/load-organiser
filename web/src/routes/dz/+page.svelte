<script lang="ts">
	import DropzoneMap from '#lib/components/DropzoneMap.svelte';
	import ExploreSwitch from '#lib/components/ExploreSwitch.svelte';
	import { COUNTRY_OPTIONS, countryName } from '#lib/countries.ts';
	import { directoryMessage } from '#lib/directory-messages.ts';
	import { dzHref } from '#lib/dz-map.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const filtered = $derived(Boolean(data.q || data.country));
	const listHref = $derived(dzHref({ q: data.q, country: data.country }));
	const mapHref = $derived(dzHref({ q: data.q, country: data.country, view: 'map' }));
	const href = (cursor?: string) => dzHref({ q: data.q, country: data.country, cursor });
</script>

<svelte:head>
	<title>Dropzones · Load Organiser</title>
	<meta
		name="description"
		content="Source-backed directory of skydiving dropzones. A listing is not an endorsement and does not mean the dropzone uses Load Organiser."
	/>
</svelte:head>

<ExploreSwitch />
<h1>Dropzones</h1>
<p class="lede">Dropzones from public sources. A listing is not an endorsement.</p>

<form method="GET" class="form search" role="search" data-sveltekit-keepfocus>
	<div class="field">
		<label for="q">Name, alias or former name</label>
		<input id="q" name="q" type="search" maxlength="80" defaultValue={data.q} autocomplete="off" />
	</div>
	<div class="field">
		<label for="country">Country</label>
		<select id="country" name="country">
			<option value="" selected={!data.country}>Any country</option>
			{#each COUNTRY_OPTIONS as option (option.code)}
				<option value={option.code} selected={option.code === data.country}>{option.name}</option>
			{/each}
		</select>
	</div>
	{#if data.view === 'map'}<input type="hidden" name="view" value="map" />{/if}
	<div class="form-actions">
		<button class="button" type="submit">Search</button>
	</div>
</form>

<!-- Two addresses, not a client-side toggle: each view can be shared and works without JS. -->
<nav class="views" aria-label="Show dropzones as">
	<a href={listHref} aria-current={data.view === 'list' ? 'page' : undefined}>List</a>
	<a href={mapHref} aria-current={data.view === 'map' ? 'page' : undefined}>Map</a>
</nav>

{#if data.view === 'map'}
	<DropzoneMap q={data.q} country={data.country} {listHref} />
{:else if data.result && !data.result.ok}
	<p class="form-error" role="alert">{directoryMessage(data.result.reason)}</p>
{:else if data.result && data.result.items.length === 0}
	<!-- No match is a quiet result under the search; an empty directory is the empty state. -->
	<section class={filtered ? 'empty-state quiet' : 'empty-state'} aria-labelledby="empty-heading">
		<h2 id="empty-heading">{filtered ? 'No listed dropzones match' : 'No dropzones are listed yet'}</h2>
		<p>
			{#if filtered}
				Try another spelling or country. Coverage is limited to reviewed, source-backed listings.
			{:else}
				Listings appear only after a source has been reviewed. Nothing here is a complete
				directory.
			{/if}
			Signed-in jumpers can keep a <a href="/places">private place</a> for any dropzone that is missing,
			or <a href="/submit?kind=suggest_venue">suggest it</a>.
		</p>
		{#if filtered}<p class="actions"><a class="button secondary" href="/dz">Clear search</a></p>{/if}
	</section>
{:else if data.result}
	<ul class="results rows grouped" aria-label="Dropzones">
		{#each data.result.items as venue (venue.id)}
			<li>
				<a class="title" href="/dz/{venue.id}">{venue.name}</a>
				<span class="meta">
					{venue.locality ? `${venue.locality}, ` : ''}{countryName(venue.country)}
				</span>
				{#if venue.status === 'closed'}<span class="tag">Closed</span>{/if}
				<span class="chevron" aria-hidden="true"></span>
			</li>
		{/each}
	</ul>
	<nav class="pager" aria-label="More results">
		{#if data.paged}
			<a href={href()}>First page</a>
		{/if}
		{#if data.result.nextCursor}
			<a href={href(data.result.nextCursor)} rel="next">More results</a>
		{/if}
	</nav>
{/if}

<style>
	h1 {
		margin: 0 0 0.25rem;
	}

	.lede {
		margin-bottom: 0.75rem;
	}

	.search {
		margin: 0 0 1rem;
	}

	/* List or Map: two plain links styled as a small segmented control. */
	.views {
		display: inline-flex;
		gap: 0.25rem;
		margin: 0 0 1rem;
		padding: 0.25rem;
		border-radius: 12px;
		background: var(--surface-soft);
		box-shadow: 0 0 0 1px var(--border);
	}

	.views a {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 5.5rem;
		min-height: 44px;
		padding: 0 1rem;
		border-radius: 9px;
		color: var(--muted);
		font-weight: 600;
		text-decoration: none;
	}

	.views a[aria-current='page'] {
		background: var(--surface);
		color: var(--fg);
		box-shadow: 0 0 0 1px var(--field-border);
	}

	.views a:not([aria-current='page']):hover {
		color: var(--fg);
		text-decoration: underline;
	}

	.views a:focus-visible {
		outline-offset: 1px;
	}

	/* One grouped list: a single outline and quiet rules between rows instead of a card per
	   dropzone. The name link still covers its row, and a chevron marks each row as one to open
	   (on touch there is no hover). Hover tints the row; focus rings it inside its own edges.
	   The selectors repeat .results.rows so they outrank the card rows in app.css. */
	.results.rows.grouped {
		gap: 0;
		border-radius: var(--radius);
		background: var(--surface);
		box-shadow: 0 0 0 1px var(--border);
	}

	.results.rows.grouped > li {
		padding-right: 2.5rem;
		border-radius: 0;
		background: none;
		box-shadow: none;
	}

	.results.rows.grouped > li + li {
		border-top: 1px solid var(--border);
	}

	.results.rows.grouped > li:first-child {
		border-radius: var(--radius) var(--radius) 0 0;
	}

	.results.rows.grouped > li:last-child {
		border-radius: 0 0 var(--radius) var(--radius);
	}

	.results.rows.grouped > li:only-child {
		border-radius: var(--radius);
	}

	.results.rows.grouped > li:has(> a.title):hover {
		background: var(--surface-soft);
		box-shadow: none;
	}

	.results.rows.grouped > li:hover > a.title {
		text-decoration: underline;
	}

	.results.rows.grouped > li:has(> a.title:focus-visible) {
		outline-offset: -3px;
	}

	.chevron {
		position: absolute;
		right: 1.1rem;
		top: 50%;
		width: 0.5rem;
		height: 0.5rem;
		border-right: 2px solid var(--muted);
		border-bottom: 2px solid var(--muted);
		transform: translateY(-50%) rotate(-45deg);
	}

	.results.rows.grouped > li:hover > .chevron {
		border-color: var(--accent);
	}

	.meta {
		color: var(--muted);
	}

	.tag {
		justify-self: start;
		border: 1px solid var(--border);
		border-radius: 999px;
		padding: 0 0.5rem;
		font-size: 0.85rem;
		color: var(--muted);
	}

	.pager {
		display: flex;
		gap: 1rem;
		margin: 1rem 0;
	}

	/* Larger screens: the search on one line, and each dropzone on one line, name first. The
	   search keeps a form's length; the list uses the frame. */
	@media (min-width: 48rem) {
		.search {
			grid-template-columns: minmax(0, 2fr) minmax(0, 1fr) auto;
			align-items: end;
			max-width: 48rem;
		}

		.results.rows.grouped > li {
			grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) 5rem;
			align-items: baseline;
			gap: 1rem;
		}

		.grouped .tag {
			justify-self: end;
		}
	}
</style>
