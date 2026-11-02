<script lang="ts">
	import Notice from '#lib/components/Notice.svelte';
	import { authMessage } from '#lib/auth-messages.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();
	const error = $derived(form && 'error' in form ? authMessage(form.error) : undefined);
</script>

<svelte:head>
	<title>Confirm email · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<h1>Confirm email</h1>

{#if form && 'verified' in form && form.verified}
	<Notice title="Email confirmed" tone="ok">
		<p>You can now save private records.</p>
	</Notice>
	<p>
		{#if data.viewer}
			<a class="button" href="/profile">Go to Profile</a>
		{:else}
			<a class="button" href="/sign-in?notice=verified">Sign in</a>
		{/if}
	</p>
{:else if !data.hasToken}
	<Notice title="Link not recognised" tone="warn">
		<p>Open the confirmation link from your email. Signed in? Request a new link from Profile.</p>
	</Notice>
{:else}
	{#if error}
		<p class="form-error" role="alert">{error}</p>
		<p>Signed in? Request a new link from <a href="/profile">Profile</a>.</p>
	{/if}
	<form method="POST" class="form">
		<p>Confirm that this email address belongs to you.</p>
		<div class="form-actions">
			<button class="button" type="submit">Confirm email</button>
		</div>
	</form>
{/if}
