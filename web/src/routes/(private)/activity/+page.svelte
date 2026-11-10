<script lang="ts">
	import JumpCard from '#lib/components/JumpCard.svelte';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
</script>

<svelte:head>
	<title>Activity · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<h1>Activity</h1>
<p class="lede">Jumps shared by people you follow, newest first. Each card shows the jump's own date.</p>

{#if data.feed === null}
	<p class="form-error" role="alert">Activity is unavailable right now. Try again later.</p>
{:else if data.feed.items.length > 0}
	<ul class="results" aria-label="Activity">
		{#each data.feed.items as post (post.id)}
			<li><JumpCard {post} /></li>
		{/each}
	</ul>
	{#if data.feed.next_before}
		<p><a href="/activity?before={data.feed.next_before}">Older activity</a></p>
	{/if}
{:else if data.older}
	<p>No older activity.</p>
	<p><a href="/activity">Back to the newest</a></p>
{:else}
	<div class="empty">
		<p><strong>Nothing to show yet.</strong> Jumps appear here when people you follow share them.</p>
		<p class="empty-actions">
			<a class="button" href="/people">Find people you know</a>
			{#if !data.hasProfile}
				<a class="button secondary" href="/profile/public">Create a public profile</a>
			{/if}
		</p>
		<p class="hint">Your logbook stays private; you choose which jumps to share from their pages.</p>
	</div>
{/if}

<style>
	.empty {
		margin: 1rem 0;
		padding: 1rem;
		border: 1px dashed var(--border);
		border-radius: var(--radius);
	}

	.empty p {
		margin: 0 0 0.75rem;
	}

	.empty-actions {
		display: flex;
		flex-wrap: wrap;
		gap: 0.6rem;
	}
</style>
