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
	const requested = $derived(data.requested ?? []);
	const followsNoOne = $derived(data.following !== null && data.following.length === 0);
	// Setting up, step by step: a profile first (needed to ask anyone), then people to follow.
	const setup = $derived(
		!data.hasProfile ? 'profile' : followsNoOne && requested.length === 0 ? 'find' : null
	);
	const profileFromHere = `/profile/public?returnTo=${encodeURIComponent('/people')}`;
</script>

<svelte:head>
	<title>Friends · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<div class="head">
	<h1>Friends</h1>
	<!-- In reach on every state, above the feed; requests come with a profile. -->
	<nav class="links" aria-label="People">
		<a href="/people">Find people</a>
		{#if data.hasProfile}<a href="/people#requests-heading">Requests, followers and blocking</a>{/if}
	</nav>
</div>
<p class="lede">
	Jumps the people you follow chose to share with you. Your logbook stays private; you share a
	jump only when you choose to.
</p>

<!-- Large screens: the shared jumps in the main column, the people you follow beside them. -->
<div class="columns">
	<div class="col-main">
		<!-- On every screen, before the feed: someone is waiting for an answer. -->
		{#if data.requests > 0}
			<p class="requests">
				<a href="/people"
					>{data.requests}
					{data.requests === 1 ? 'follow request' : 'follow requests'} waiting</a
				>
			</p>
		{/if}
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
		{:else if setup === 'profile'}
			<section class="empty-state" aria-labelledby="empty-heading">
				<h2 id="empty-heading">Start with a public profile</h2>
				<p>
					To ask to follow someone you need a public profile: it is what they see before they
					approve you. It shows only the name and details you enter.
				</p>
				<p class="actions">
					<a class="button" href={profileFromHere}>Create your public profile</a>
					<a class="button secondary" href="/people">Look for people first</a>
				</p>
				<p class="hint">After saving it you go on to finding people.</p>
			</section>
		{:else if setup === 'find'}
			<section class="empty-state" aria-labelledby="empty-heading">
				<h2 id="empty-heading">Find people you jump with</h2>
				<p>
					Ask to follow them; each person approves you first. Following never opens their logbook
					or gear, or yours.
				</p>
				<p class="actions"><a class="button" href="/people">Find people</a></p>
			</section>
		{:else if followsNoOne && requested.length > 0}
			<section class="empty-state" aria-labelledby="empty-heading">
				<h2 id="empty-heading">Waiting for approval</h2>
				<p>
					You asked to follow {requested.length === 1 ? 'someone' : `${requested.length} people`}.
					You follow them once they approve; the jumps they share with you then appear here.
				</p>
				<p class="actions"><a class="button secondary" href="/people">Find more people</a></p>
			</section>
		{:else}
			<!-- Following someone, or unknown (the list failed): nothing to set up, only to wait. -->
			<section class="empty-state quiet" aria-labelledby="empty-heading">
				<h2 id="empty-heading">No shared jumps yet</h2>
				<p>
					{data.following === null
						? 'Jumps shared by people you follow appear here, each with its own date.'
						: 'The people you follow have not shared a jump with you yet. When they do, it appears here.'}
				</p>
			</section>
		{/if}
	</div>

	<!-- On a phone this comes after the feed. Following no one, a phone shows only the link to
	     followers and blocking: the empty state above already says it. -->
	<section class="col-side people" class:none={followsNoOne} aria-labelledby="following-heading">
		<h2 id="following-heading" class:wide-only={followsNoOne}>People you follow</h2>
		{#if data.following === null}
			<p class="hint">The people you follow could not be loaded right now. Reload to try again.</p>
		{:else if following.length === 0}
			<p class="hint wide-only">No one yet. The jumps they share will show here once they approve you.</p>
		{:else}
			<ul class="following" aria-labelledby="following-heading">
				{#each following.slice(0, SHOWN) as person (person.handle)}
					<li>
						<a href="/people/{person.handle}">{person.display_name}</a>
						<span class="meta wrap-anywhere">@{person.handle}</span>
					</li>
				{/each}
			</ul>
			{#if following.length > SHOWN}
				<p class="hint">and {following.length - SHOWN} more</p>
			{/if}
		{/if}
		{#if requested.length > 0}
			<h3 class="waiting-heading" id="requested-heading">Waiting for approval</h3>
			<ul class="following" aria-labelledby="requested-heading">
				{#each requested.slice(0, SHOWN) as person (person.handle)}
					<li>
						<a href="/people/{person.handle}">{person.display_name}</a>
						<span class="meta wrap-anywhere">@{person.handle} · asked</span>
					</li>
				{/each}
			</ul>
			{#if requested.length > SHOWN}<p class="hint">and {requested.length - SHOWN} more</p>{/if}
		{/if}
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

	.head .links {
		display: flex;
		flex-wrap: wrap;
		gap: 0 1.25rem;
	}

	.waiting-heading {
		margin: 0.75rem 0 0.35rem;
		font-size: 0.95rem;
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

	.requests {
		margin: 0 0 0.75rem;
	}

	.requests a {
		display: inline-flex;
		align-items: center;
		min-height: 44px;
		font-weight: 600;
	}

	/* Following no one, on a phone: just the link, no card. */
	@media (max-width: 59.99rem) {
		.people.none {
			padding: 0;
			border: 0;
			background: none;
		}
	}

	@media (min-width: 60rem) {
		.people {
			margin-top: 0;
		}
	}
</style>
