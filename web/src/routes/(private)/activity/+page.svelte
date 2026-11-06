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
<p class="lede">
	Jumps shared by people you follow, newest publication first. Each card shows the date of the jump
	itself, which can be much earlier than when it was shared.
</p>

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
	<p>Nothing to show yet. Posts appear here when people you follow share a jump.</p>
	<ul>
		<li><a href="/people">Find people you know</a> by name or handle and ask to follow them.</li>
		{#if !data.hasProfile}
			<li><a href="/profile/public">Create a public profile</a> so people can see who is asking.</li>
		{/if}
		<li><a href="/">Discover events and camps</a> or <a href="/dz">browse dropzones</a>.</li>
		<li><a href="/jumps">Your logbook</a> stays private; you can share a jump from its page.</li>
	</ul>
{/if}
