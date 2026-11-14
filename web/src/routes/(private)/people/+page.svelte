<script lang="ts">
	import InviteLink from '#lib/components/InviteLink.svelte';
	import { page } from '$app/state';
	import type { PersonOut } from '#lib/contracts/index.ts';
	import { socialMessage } from '#lib/social.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();
	const errorFor = (name: string) =>
		form && form.form === name && 'error' in form ? socialMessage(form.error) : undefined;
</script>

<svelte:head>
	<title>People · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<p><a href="/profile">Profile</a></p>
<h1>People</h1>
<p class="lede">Follow people you know. Following never opens anyone's logbook or gear.</p>

{#if page.url.searchParams.get('blocked')}
	<p role="status" class="ok">Blocked. Follows between you were removed.</p>
{/if}

{#if !data.profileOk}
	<p class="form-error" role="alert">{socialMessage('unavailable')}</p>
{:else if !data.profile}
	<section class="card you">
		<p>
			You have no public profile, so no one can find you and you cannot ask to follow people.
			Your logbook stays private either way.
		</p>
		<a class="button" href="/profile/public">Create a profile</a>
	</section>
{:else}
	<section class="card you">
		<p>
			You are <a class="wrap-anywhere" href="/people/{data.profile.handle}">@{data.profile.handle}</a>
			({data.profile.discoverable ? 'discoverable' : 'not discoverable: only approved followers see your profile'}).
		</p>
		{#if data.profile.discoverable}
			<p>Send your profile link to the people you jump with, so they can ask to follow you.</p>
			<InviteLink
				url="{page.url.origin}/people/{data.profile.handle}"
				name={data.profile.display_name}
			/>
		{:else}
			<p class="hint">
				To invite people with a link, turn on "Let people find my profile": until you approve
				them, others cannot open a private profile.
			</p>
		{/if}
		<a class="button secondary" href="/profile/public">Edit profile</a>
	</section>
{/if}

<form method="GET" class="form search card" role="search">
	<div class="field">
		<label for="q">Find people by handle or name</label>
		<input id="q" name="q" type="search" maxlength="40" defaultValue={data.q} />
	</div>
	<div class="form-actions"><button class="button secondary" type="submit">Search</button></div>
</form>
{#if data.search && !data.search.ok}
	<p class="form-error" role="alert">{socialMessage(data.search.reason)}</p>
{:else if data.search}
	{#if data.search.items.length === 0}
		<p class="hint">No discoverable profile matches. People who keep their profile private cannot be found.</p>
	{:else}
		<ul class="results rows" aria-label="Search results">
			{#each data.search.items as person (person.handle)}
				<li><a class="title" href="/people/{person.handle}">{person.display_name}</a> <span class="meta wrap-anywhere">@{person.handle}</span></li>
			{/each}
		</ul>
	{/if}
{/if}

{#snippet who(person: PersonOut)}
	<a class="title" href="/people/{person.handle}">{person.display_name}</a>
	<span class="meta wrap-anywhere">@{person.handle}</span>
{/snippet}

{#snippet block(person: PersonOut)}
	<details>
		<summary>Block @{person.handle}</summary>
		<form method="POST" action="?/block" class="form">
			<input type="hidden" name="handle" value={person.handle} />
			<label class="choice"><input type="checkbox" name="confirm" /> Block @{person.handle}</label>
			<p class="hint">
				Removes follows both ways; while signed in, neither of you can see or find the other.
				Anything shared publicly stays visible to people who are not signed in. They are not told.
			</p>
			<button class="button danger" disabled={!data.emailVerified}>Block</button>
		</form>
	</details>
{/snippet}

{#if errorFor('people')}<p class="form-error" role="alert">{errorFor('people')}</p>{/if}

<section class="card">
<h2>Follow requests</h2>
{#if errorFor('requests')}<p class="form-error" role="alert">{errorFor('requests')}</p>{/if}
{#if data.requests === null}
	<p class="form-error" role="alert">{socialMessage('unavailable')}</p>
{:else if data.requests.length === 0}
	<p class="hint">No pending requests.</p>
{:else}
	<p class="hint">
		Approving lets them see what you share with followers, including what you shared before.
	</p>
	<ul class="results rows" aria-label="Follow requests">
		{#each data.requests as person (person.handle)}
			<li>
				{@render who(person)}
				<form method="POST" class="inline">
					<input type="hidden" name="handle" value={person.handle} />
					<button class="button" formaction="?/approve" disabled={!data.emailVerified}>Approve</button>
					<button class="button secondary" formaction="?/reject" disabled={!data.emailVerified}>Decline</button>
				</form>
				{@render block(person)}
			</li>
		{/each}
	</ul>
{/if}
</section>

<section class="card">
<h2>Followers</h2>
{#if errorFor('followers')}<p class="form-error" role="alert">{errorFor('followers')}</p>{/if}
{#if data.followers === null}
	<p class="form-error" role="alert">{socialMessage('unavailable')}</p>
{:else if data.followers.length === 0}
	<p class="hint">No followers yet.</p>
{:else}
	<ul class="results rows" aria-label="Followers">
		{#each data.followers as person (person.handle)}
			<li>
				{@render who(person)}
				<form method="POST" action="?/remove" class="inline">
					<input type="hidden" name="handle" value={person.handle} />
					<button class="button secondary" disabled={!data.emailVerified}>Remove follower</button>
				</form>
				{@render block(person)}
			</li>
		{/each}
	</ul>
{/if}
</section>

<section class="card">
<h2>Following</h2>
{#if data.following === null}
	<p class="form-error" role="alert">{socialMessage('unavailable')}</p>
{:else if data.following.length === 0}
	<p class="hint">You follow no one yet.</p>
{:else}
	<ul class="results rows" aria-label="Following">
		{#each data.following as person (person.handle)}
			<li>{@render who(person)}</li>
		{/each}
	</ul>
{/if}
</section>

<section class="card">
<h2>Blocked</h2>
{#if errorFor('blocked')}<p class="form-error" role="alert">{errorFor('blocked')}</p>{/if}
{#if data.blocked === null}
	<p class="form-error" role="alert">{socialMessage('unavailable')}</p>
{:else if data.blocked.length === 0}
	<p class="hint">You have blocked no one.</p>
{:else}
	<ul class="results rows" aria-label="Blocked">
		{#each data.blocked as person (person.handle)}
			<li>
				<span class="title">{person.display_name}</span> <span class="meta wrap-anywhere">@{person.handle}</span>
				<form method="POST" action="?/unblock" class="inline">
					<input type="hidden" name="handle" value={person.handle} />
					<button class="button secondary" disabled={!data.emailVerified}>Unblock</button>
				</form>
			</li>
		{/each}
	</ul>
	<p class="hint">Unblocking does not restore earlier follows.</p>
{/if}
</section>

<style>
	.you p {
		margin-top: 0;
	}

	.search {
		margin: 1rem 0;
	}

	.inline {
		display: flex;
		gap: 0.5rem;
		margin-block-start: 0.5rem;
	}
</style>
