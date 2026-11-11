<script lang="ts">
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
		<button class="button" type="submit">Search</button>
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
	<ul class="results rows" aria-label="Dropzones">
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
	.search {
		margin-bottom: 1rem;
	}

	.results {
		list-style: none;
		padding: 0;
		margin: 0;
	}

	.results li {
		border-bottom: 1px solid var(--border);
		padding: 0.75rem 0;
		display: flex;
		flex-wrap: wrap;
		gap: 0.25rem 0.75rem;
		align-items: baseline;
	}

	.results a {
		font-weight: 600;
	}

	.meta {
		color: var(--muted);
	}

	.tag {
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
</style>
