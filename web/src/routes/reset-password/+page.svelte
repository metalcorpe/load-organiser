<script lang="ts">
	import Notice from '#lib/components/Notice.svelte';
	import { authMessage } from '#lib/auth-messages.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();
	const error = $derived(authMessage(form?.error));
</script>

<svelte:head>
	<title>Choose a new password · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<h1>Choose a new password</h1>

{#if !data.hasToken}
	<Notice title="Link not recognised" tone="warn">
		<p>Open the reset link from your email, or request a new one.</p>
	</Notice>
	<p><a class="button" href="/forgot-password">Request a new link</a></p>
{:else}
	<form method="POST" class="form" novalidate>
		{#if error}
			<p class="form-error" role="alert">{error}</p>
			{#if form?.error === 'invalid_or_expired_token'}
				<p><a href="/forgot-password">Request a new link</a></p>
			{/if}
		{/if}
		<div class="field">
			<label for="password">New password</label>
			<input
				id="password"
				name="password"
				type="password"
				autocomplete="new-password"
				required
				minlength="15"
				maxlength="128"
				aria-describedby="password-hint"
			/>
			<p class="hint" id="password-hint">15 to 128 characters. Signs you out on every device.</p>
		</div>
		<div class="field">
			<label for="password_confirm">Repeat new password</label>
			<input
				id="password_confirm"
				name="password_confirm"
				type="password"
				autocomplete="new-password"
				required
				minlength="15"
				maxlength="128"
			/>
		</div>
		<div class="form-actions">
			<button class="button" type="submit">Change password</button>
		</div>
	</form>
{/if}
