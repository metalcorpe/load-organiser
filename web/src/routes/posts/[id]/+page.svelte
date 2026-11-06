<script lang="ts">
	import { page } from '$app/state';
	import JumpCard from '#lib/components/JumpCard.svelte';
	import { formatDay } from '#lib/listings.ts';
	import { postMessage } from '#lib/posts.ts';
	import { REPORT_REASONS } from '#lib/social.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();
	const post = $derived(data.post);
	const reportError = $derived(
		form && form.form === 'report' && 'error' in form ? postMessage(form.error) : undefined
	);
	const signIn = $derived(`/sign-in?returnTo=${encodeURIComponent(page.url.pathname)}`);
</script>

<svelte:head>
	<title>Jump on {formatDay(post.jumped_on)} by @{post.author.handle} · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<h1>Jump on {formatDay(post.jumped_on)}</h1>
<JumpCard {post} link={false} />
<p class="hint">
	A shared summary chosen by the jumper. It is not a verified record and does not give access to
	their logbook or gear.
</p>

{#if post.is_owner}
	<p>
		This is your post. <a href="/jumps/{post.jump_id}/share">Change who can see it or unpublish</a>
	</p>
{:else if !data.signedIn}
	<p><a href={signIn}>Sign in</a> to report this post.</p>
{:else}
	<form method="POST" action="?/report" class="form">
		{#if form && form.form === 'report' && 'done' in form}
			<p role="status" class="ok">
				Report received. A reviewer will look at it; that is not a promise of a particular outcome or
				time. The person is not told who reported them.
			</p>
		{/if}
		{#if reportError}<p class="form-error" role="alert">{reportError}</p>{/if}
		<div class="field">
			<label for="reason">Report this post</label>
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
{/if}
