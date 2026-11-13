<script lang="ts">
	import JumpCard from '#lib/components/JumpCard.svelte';
	import Notice from '#lib/components/Notice.svelte';
	import { page } from '$app/state';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	// The tab is Friends, but following is one way: the copy says "people you follow" and never
	// calls anyone a friend.
	const SHOWN = 8;
	const following = $derived(data.following ?? []);
	const followsNoOne = $derived(data.following !== null && data.following.length === 0);
</script>

<svelte:head>
	<title>Friends · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<div class="head">
	<h1>Friends</h1>
	<p class="links"><a href="/people">Find people</a></p>
</div>
<p class="lede">
	Jumps shared by people you follow, newest first. Following is one way: it shows you what they
	share and opens nothing of yours.
</p>

<!-- Large screens: the shared jumps in the main column, the people you follow beside them. -->
<div class="columns">
	<div class="col-main">
		{#if data.feed === null}
			<Notice title="Shared jumps could not be loaded" tone="bad">
				<p role="alert">The service is unavailable right now. Try again later.</p>
				<p>
					<a class="button secondary" href={page.url.pathname + page.url.search} data-sveltekit-reload
						>Try again</a
					>
				</p>
			</Notice>
		{:else if data.feed.items.length > 0}
			<section aria-labelledby="feed-heading">
				<h2 id="feed-heading" class="feed-heading">Shared jumps</h2>
				<ul class="results" aria-label="Shared jumps">
					{#each data.feed.items as post (post.id)}
						<li><JumpCard {post} /></li>
					{/each}
				</ul>
				{#if data.feed.next_before}
					<p><a href="/activity?before={data.feed.next_before}">Older shared jumps</a></p>
				{/if}
			</section>
		{:else if data.older}
			<section class="empty-state quiet" aria-labelledby="empty-heading">
				<h2 id="empty-heading">No older shared jumps</h2>
				<p>You have reached the oldest jump shared with you.</p>
				<p class="actions"><a class="button secondary" href="/activity">Back to the newest</a></p>
			</section>
		{:else if followsNoOne}
			<section class="empty-state" aria-labelledby="empty-heading">
				<h2 id="empty-heading">You do not follow anyone yet</h2>
				<p>
					Follow people you jump with to see the jumps they share. They approve each request, and
					following never opens anyone's logbook or gear.
				</p>
				<p class="actions">
					<a class="button" href="/people">Find people</a>
					{#if !data.hasProfile}
						<a class="button secondary" href="/profile/public">Create a public profile</a>
					{/if}
				</p>
				<p class="hint">Your logbook stays private; you choose which jumps to share from their pages.</p>
			</section>
		{:else}
			<section class="empty-state" aria-labelledby="empty-heading">
				<h2 id="empty-heading">No shared jumps yet</h2>
				<p>
					The people you follow have not shared a jump with you yet. Their shared jumps appear here,
					each with its own date.
				</p>
				<p class="actions">
					<a class="button" href="/people">Find people</a>
					{#if !data.hasProfile}
						<a class="button secondary" href="/profile/public">Create a public profile</a>
					{/if}
				</p>
			</section>
		{/if}
	</div>

	<!-- On a phone this comes after the feed, and only once there is someone to list. -->
	<section
		class="col-side people"
		class:wide-only={data.following === null || following.length === 0}
		aria-labelledby="following-heading"
	>
		<h2 id="following-heading">People you follow</h2>
		{#if data.following === null}
			<p class="hint">The people you follow could not be loaded right now.</p>
		{:else if following.length === 0}
			<p class="hint">No one yet. The jumps they share will show here once they approve you.</p>
		{:else}
			<ul class="following" aria-labelledby="following-heading">
				{#each following.slice(0, SHOWN) as person (person.handle)}
					<li>
						<a href="/people/{person.handle}">{person.display_name}</a>
						<span class="meta">@{person.handle}</span>
					</li>
				{/each}
			</ul>
			{#if following.length > SHOWN}
				<p class="hint">and {following.length - SHOWN} more</p>
			{/if}
		{/if}
		{#if data.requests > 0}
			<p>
				<a href="/people"
					>{data.requests}
					{data.requests === 1 ? 'follow request' : 'follow requests'} waiting</a
				>
			</p>
		{/if}
		<p class="more-link"><a href="/people">Followers, requests and blocking</a></p>
	</section>
</div>

<style>
	/* With very large text the link moves under the heading, which never breaks inside its word. */
	.head {
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		align-items: baseline;
		column-gap: 1rem;
	}

	.head h1 {
		overflow-wrap: break-word;
	}

	.head .links {
		margin: 0;
	}

	.head a {
		display: inline-flex;
		align-items: center;
		min-height: 44px;
		font-weight: 600;
	}

	.feed-heading {
		font-size: 1.15rem;
		margin: 0 0 0.25rem;
	}

	.people {
		margin: 1.5rem 0 1rem;
		padding: 0.75rem 0.9rem;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		background: var(--surface);
		font-size: 0.95rem;
	}

	.people h2 {
		font-size: 1rem;
		margin: 0 0 0.35rem;
	}

	.people p {
		margin: 0.4rem 0 0;
	}

	.following {
		display: grid;
		list-style: none;
		margin: 0;
		padding: 0;
	}

	.following li {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		column-gap: 0.5rem;
		min-height: 44px;
	}

	.following a {
		font-weight: 600;
	}

	.meta {
		color: var(--muted);
		font-size: 0.9rem;
	}

	@media (min-width: 60rem) {
		.people {
			margin-top: 0;
		}
	}
</style>
