<script lang="ts">
	import { formatDay, formatRange } from '#lib/listings.ts';
	import { reviewMessage } from '#lib/review-messages.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const checked = (value: string | null) => (value ? `checked ${formatDay(value)}` : 'never checked');
</script>

<svelte:head>
	<title>Maintenance · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<h1>Maintenance</h1>
<p class="lede">
	Reviewer tools. Every change is recorded with your account. Due checks follow the operating
	cadence: listings starting within 30 days weekly, postponed listings weekly, dropzones and
	organizers every 60 days.
</p>

<p class="actions">
	<a class="button" href="/review/listings/new">New listing</a>
	<a class="button secondary" href="/review/organizers/new">New organizer</a>
	<a class="button secondary" href="/review/dropzones/new">New dropzone</a>
	<a href="/review/submissions">Submissions</a>
	<a href="/review/social">Profile reports</a>
</p>

<form method="GET" class="form search" role="search">
	<div class="field">
		<label for="q">Filter by name or title</label>
		<input id="q" name="q" type="search" maxlength="80" defaultValue={data.q} />
	</div>
	<div class="form-actions"><button class="button secondary" type="submit">Filter</button></div>
</form>

{#snippet failed(reason: string)}
	<p class="form-error" role="alert">{reviewMessage(reason)}</p>
{/snippet}

{#if data.matches}
	<h2>Matching “{data.q}”</h2>
	{#each [['listings', data.matches.listings], ['organizers', data.matches.organizers], ['dropzones', data.matches.dropzones]] as const as [kind, group] (kind)}
		{#if !group.ok}
			{@render failed(group.reason)}
		{:else}
			<ul class="results rows" aria-label="Matching {kind}">
				{#each group.items as item (item.id)}
					<li>
						<a class="title" href="/review/{kind}/{item.id}">{'title' in item ? item.title : item.name}</a>
						<span class="meta">{kind.slice(0, -1)} · {item.status}</span>
					</li>
				{:else}
					<li><span class="meta">No {kind}.</span></li>
				{/each}
			</ul>
		{/if}
	{/each}
{/if}

<h2>Open submissions</h2>
{#if !data.submissions.ok}
	{@render failed(data.submissions.reason)}
{:else if data.submissions.items.length === 0}
	<p>None waiting.</p>
{:else}
	<p>
		<a href="/review/submissions">{data.submissions.items.length}{data.submissions.more ? '+' : ''} waiting</a>
	</p>
{/if}

<h2>Listings due a check</h2>
{#if !data.dueListings.ok}
	{@render failed(data.dueListings.reason)}
{:else if data.dueListings.items.length === 0}
	<p>Nothing due.</p>
{:else}
	<ul class="results rows" aria-label="Listings due a check">
		{#each data.dueListings.items as item (item.id)}
			<li>
				<a class="title" href="/review/listings/{item.id}">{item.title}</a>
				<span class="meta">{item.status} · {formatRange(item.starts_on, item.ends_on)} · {checked(item.checked_on)}</span>
			</li>
		{/each}
	</ul>
{/if}

<h2>Listings in draft or review</h2>
{#each [data.inReview, data.drafts] as group, index (index)}
	{#if !group.ok}
		{@render failed(group.reason)}
	{:else if group.items.length > 0}
		<ul class="results rows" aria-label={index === 0 ? 'In review' : 'Drafts'}>
			{#each group.items as item (item.id)}
				<li>
					<a class="title" href="/review/listings/{item.id}">{item.title}</a>
					<span class="meta">{item.status} · {formatRange(item.starts_on, item.ends_on)}</span>
				</li>
			{/each}
		</ul>
	{/if}
{/each}

<h2>Organizers due a check</h2>
{#if !data.dueOrganizers.ok}
	{@render failed(data.dueOrganizers.reason)}
{:else if data.dueOrganizers.items.length === 0}
	<p>Nothing due.</p>
{:else}
	<ul class="results rows" aria-label="Organizers due a check">
		{#each data.dueOrganizers.items as item (item.id)}
			<li>
				<a class="title" href="/review/organizers/{item.id}">{item.name}</a>
				<span class="meta">{checked(item.checked_on)}</span>
			</li>
		{/each}
	</ul>
{/if}

<h2>Dropzones due a check</h2>
{#if !data.dueDropzones.ok}
	{@render failed(data.dueDropzones.reason)}
{:else if data.dueDropzones.items.length === 0}
	<p>Nothing due.</p>
{:else}
	<ul class="results rows" aria-label="Dropzones due a check">
		{#each data.dueDropzones.items as item (item.id)}
			<li>
				<a class="title" href="/review/dropzones/{item.id}">{item.name}</a>
				<span class="meta">{checked(item.checked_on)}</span>
			</li>
		{/each}
	</ul>
{/if}

<style>
	.actions {
		display: flex;
		flex-wrap: wrap;
		gap: 0.75rem;
		align-items: center;
	}

	.meta {
		color: var(--muted);
		flex-basis: 100%;
	}
</style>
