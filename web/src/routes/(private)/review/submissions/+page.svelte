<script lang="ts">
	import { formatDay } from '#lib/listings.ts';
	import { reviewMessage } from '#lib/review-messages.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();

	const KIND_LABEL: Record<string, string> = {
		suggest_venue: 'Dropzone suggestion',
		suggest_listing: 'Listing suggestion',
		correction: 'Correction',
		report: 'Report'
	};
	const PUBLIC_PATH: Record<string, string> = {
		venue: '/dz',
		provider: '/organizers',
		opportunity: '/events'
	};
	const REVIEW_PATH: Record<string, string> = {
		venue: '/review/dropzones',
		provider: '/review/organizers',
		opportunity: '/review/listings'
	};
</script>

<svelte:head>
	<title>Submissions · Maintenance · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<p><a href="/review">Maintenance</a></p>
<h1>Submissions</h1>
<p class="lede">
	Suggestions, corrections and reports from signed-in members. Who sent them is not shown. Check the
	source, edit the record with the maintenance tools, then resolve; the note is shown to the sender.
</p>

<nav class="tabs" aria-label="Status">
	{#each ['open', 'accepted', 'declined'] as status (status)}
		<a href="?status={status}" aria-current={status === data.status ? 'page' : undefined}>{status}</a>
	{/each}
</nav>

{#if form && 'done' in form}<p role="status">Resolved as {form.done}.</p>{/if}

{#if !data.page.ok}
	<p class="form-error" role="alert">{reviewMessage(data.page.reason)}</p>
{:else if data.page.items.length === 0}
	<p>No {data.status} submissions.</p>
{:else}
	<ul class="results" aria-label="Submissions">
		{#each data.page.items as item (item.id)}
			<li>
				<span class="title">{KIND_LABEL[item.kind]}</span>
				<span class="meta">Received {formatDay(item.created_at.slice(0, 10))}</span>
				{#if item.target_kind && item.target_id}
					<span class="meta">
						About: <a href="{PUBLIC_PATH[item.target_kind]}/{item.target_id}">public page</a> ·
						<a href="{REVIEW_PATH[item.target_kind]}/{item.target_id}">edit</a>
					</span>
				{/if}
				<span class="message">{item.message}</span>
				{#if item.source_url}
					<span class="meta"
						>Source: <a href={item.source_url} rel="external noopener noreferrer nofollow"
							>{item.source_url}</a
						></span
					>
				{/if}
				{#if item.status === 'open'}
					<form method="POST" action="?/resolve" class="form resolve">
						{#if form && 'error' in form && form.id === item.id}
							<p class="form-error" role="alert">{reviewMessage(form.error)}</p>
						{/if}
						<input type="hidden" name="id" value={item.id} />
						<input type="hidden" name="version" value={item.version} />
						<div class="field">
							<label for="note-{item.id}">Note to the sender (optional)</label>
							<input id="note-{item.id}" name="note" maxlength="280" />
						</div>
						<div class="form-actions">
							<button class="button" type="submit" name="outcome" value="accepted">Accept</button>
							<button class="button secondary" type="submit" name="outcome" value="declined"
								>Decline</button
							>
						</div>
					</form>
				{:else}
					<span class="meta">{item.status}{item.resolution_note ? `: ${item.resolution_note}` : ''}</span>
				{/if}
			</li>
		{/each}
	</ul>
	{#if data.page.nextCursor}
		<p><a href="?status={data.status}&cursor={encodeURIComponent(data.page.nextCursor)}">More</a></p>
	{/if}
{/if}

<style>
	.tabs {
		display: flex;
		gap: 1rem;
		margin: 1rem 0;
	}

	.tabs a[aria-current='page'] {
		font-weight: 700;
	}

	.title {
		font-weight: 600;
	}

	.meta {
		color: var(--muted);
		flex-basis: 100%;
		overflow-wrap: anywhere;
	}

	.message {
		flex-basis: 100%;
		white-space: pre-line;
		overflow-wrap: anywhere;
	}

	.resolve {
		flex-basis: 100%;
	}
</style>
