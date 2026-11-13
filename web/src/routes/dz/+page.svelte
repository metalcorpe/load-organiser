<script lang="ts">
	import ExploreSwitch from '#lib/components/ExploreSwitch.svelte';
	import Notice from '#lib/components/Notice.svelte';
	import { COUNTRY_OPTIONS, countryName } from '#lib/countries.ts';
	import { directoryMessage } from '#lib/directory-messages.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const filtered = $derived(Boolean(data.q || data.country));

	function href(cursor?: string): string {
		const params = new URLSearchParams();
		if (data.q) params.set('q', data.q);
		if (data.country) params.set('country', data.country);
		if (cursor) params.set('cursor', cursor);
		const search = params.toString();
		return search ? `/dz?${search}` : '/dz';
	}
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
	<div class="form-actions">
		<button class="button secondary" type="submit">Search</button>
	</div>
</form>

{#if !data.result.ok}
	<p class="form-error" role="alert">{directoryMessage(data.result.reason)}</p>
{:else if data.result.items.length === 0}
	<Notice title={filtered ? 'No listed dropzones match' : 'No dropzones are listed yet'} tone="warn">
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
	</Notice>
{:else}
	<ul class="results rows grouped" aria-label="Dropzones">
		{#each data.result.items as venue (venue.id)}
			<li>
				<a class="title" href="/dz/{venue.id}">{venue.name}</a>
				<span class="meta">
					{venue.locality ? `${venue.locality}, ` : ''}{countryName(venue.country)}
				</span>
				{#if venue.status === 'closed'}<span class="tag">Closed</span>{/if}
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

	/* One grouped list: a single outline and quiet rules between rows instead of a card per
	   dropzone. The name link still covers its row; hover tints the row, focus rings it inside. */
	.grouped {
		gap: 0;
		border-radius: var(--radius);
		background: var(--surface);
		box-shadow: 0 0 0 1px var(--border);
	}

	.grouped > li {
		border-radius: 0;
		background: none;
		box-shadow: none;
	}

	.grouped > li + li {
		border-top: 1px solid var(--border);
	}

	.grouped > li:first-child {
		border-radius: var(--radius) var(--radius) 0 0;
	}

	.grouped > li:last-child {
		border-radius: 0 0 var(--radius) var(--radius);
	}

	.grouped > li:only-child {
		border-radius: var(--radius);
	}

	.grouped > li:hover {
		background: var(--surface-soft);
		box-shadow: none;
	}

	.grouped > li:hover > a.title {
		text-decoration: underline;
	}

	.grouped > li:has(> a.title:focus-visible) {
		outline-offset: -3px;
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

	/* Larger screens: the search on one line, and each dropzone on one line, name first. */
	@media (min-width: 48rem) {
		.search {
			grid-template-columns: minmax(0, 2fr) minmax(0, 1fr) auto;
			align-items: end;
		}

		.grouped > li {
			grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) 5rem;
			align-items: baseline;
			gap: 1rem;
		}

		.grouped .tag {
			justify-self: end;
		}
	}
</style>
