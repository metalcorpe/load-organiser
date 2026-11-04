<script lang="ts">
	import { page } from '$app/state';
	import { countryName } from '#lib/countries.ts';
	import { REPORT_REASONS, disciplineLabel, socialMessage } from '#lib/social.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();
	const p = $derived(data.person);
	const errorFor = (name: string) =>
		form && form.form === name && 'error' in form ? socialMessage(form.error) : undefined;
	const doneFor = (name: string) => form && form.form === name && 'done' in form;
	const signIn = $derived(`/sign-in?returnTo=${encodeURIComponent(page.url.pathname)}`);
</script>

<svelte:head>
	<title>{p.display_name} (@{p.handle}) · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<h1>{p.display_name}</h1>
<p class="lede">@{p.handle}</p>

{#if p.bio}<p class="bio">{p.bio}</p>{/if}
<dl class="facts">
	{#if p.disciplines.length > 0}
		<dt>Disciplines</dt>
		<dd>{p.disciplines.map(disciplineLabel).join(', ')}</dd>
	{/if}
	{#if p.home_venue}
		<dt>Home dropzone</dt>
		<dd>
			<a href="/dz/{p.home_venue.id}">{p.home_venue.name}</a>, {countryName(p.home_venue.country)}
		</dd>
	{/if}
</dl>
<p class="hint">
	A profile is the person's own description. It is not a verified identity, licence or experience
	record, and it never gives access to their logbook or gear.
</p>

{#if p.is_self}
	<p role="status">This is your profile as others see it. <a href="/profile/public">Edit</a></p>
{:else if !data.signedIn}
	<p><a href={signIn}>Sign in</a> to ask to follow, block or report.</p>
{:else}
	<section aria-labelledby="follow-heading">
		<h2 id="follow-heading">Follow</h2>
		{#if p.follows_you === 'following'}<p class="meta">Follows you.</p>{/if}
		{#if p.follows_you === 'requested'}
			<p class="meta">Asked to follow you. <a href="/people">Review requests</a></p>
		{/if}
		{#if errorFor('follow')}<p class="form-error" role="alert">{errorFor('follow')}</p>{/if}
		{#if p.follow_state === 'none'}
			<form method="POST" action="?/follow" class="form">
				<p class="hint">
					They see your handle and display name and decide. If they approve, you can see what they
					share with followers, including posts they shared before.
				</p>
				<div class="form-actions">
					<button class="button" type="submit" disabled={!data.emailVerified}>Ask to follow</button>
				</div>
			</form>
		{:else}
			<form method="POST" action="?/unfollow" class="form">
				<p role="status">{p.follow_state === 'requested' ? 'Requested; waiting for approval.' : 'Following.'}</p>
				<div class="form-actions">
					<button class="button secondary" type="submit" disabled={!data.emailVerified}>
						{p.follow_state === 'requested' ? 'Cancel request' : 'Unfollow'}
					</button>
				</div>
			</form>
		{/if}
	</section>

	<section aria-labelledby="safety-heading">
		<h2 id="safety-heading">Block or report</h2>
		<form method="POST" action="?/block" class="form">
			{#if errorFor('block')}<p class="form-error" role="alert">{errorFor('block')}</p>{/if}
			<label class="choice"><input type="checkbox" name="confirm" /> Block @{p.handle}</label>
			<p class="hint">
				Removes follows both ways. While signed in, neither of you can see or find the other's
				profile or posts. Anything shared publicly stays visible to people who are not signed in.
				They are not told.
			</p>
			<div class="form-actions">
				<button class="button secondary" type="submit" disabled={!data.emailVerified}>Block</button>
			</div>
		</form>

		<form method="POST" action="?/report" class="form">
			{#if doneFor('report')}
				<p role="status" class="ok">
					Report received. A reviewer will look at it; that is not a promise of a particular
					outcome or time. The person is not told who reported them.
				</p>
			{/if}
			{#if errorFor('report')}<p class="form-error" role="alert">{errorFor('report')}</p>{/if}
			<div class="field">
				<label for="reason">Report this profile</label>
				<select id="reason" name="reason">
					<option value="">Choose a reason…</option>
					{#each Object.entries(REPORT_REASONS) as [value, label] (value)}
						<option {value}>{label}</option>
					{/each}
				</select>
			</div>
			<div class="field">
				<label for="note">What is wrong (optional)</label>
				<textarea id="note" name="note" rows="2" maxlength="1000"></textarea>
			</div>
			<div class="form-actions">
				<button class="button secondary" type="submit" disabled={!data.emailVerified}>Send report</button>
			</div>
		</form>
	</section>
{/if}

<style>
	.bio {
		white-space: pre-line;
	}
</style>
