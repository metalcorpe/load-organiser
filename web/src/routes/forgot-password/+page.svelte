<script lang="ts">
	import Notice from '#lib/components/Notice.svelte';
	import { authMessage } from '#lib/auth-messages.ts';
	import type { PageProps } from './$types';

	let { form }: PageProps = $props();
	const error = $derived(form && 'error' in form ? authMessage(form.error) : undefined);
</script>

<svelte:head>
	<title>Reset password · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<h1>Reset password</h1>

{#if form && 'sent' in form && form.sent}
	<Notice title="Check your email" tone="ok">
		<p>
			If an account uses that address, we sent a reset link. It works once and expires in 30
			minutes. Resetting signs you out on every device.
		</p>
	</Notice>
	<p><a href="/sign-in">Back to sign in</a></p>
{:else}
	<p class="lede">We will email you a link to choose a new password.</p>
	<form method="POST" class="form" novalidate>
		{#if error}
			<p class="form-error" role="alert">{error}</p>
		{/if}
		<div class="field">
			<label for="email">Email</label>
			<input
				id="email"
				name="email"
				type="email"
				autocomplete="email"
				required
				maxlength="254"
				defaultValue={form?.email ?? ''}
			/>
		</div>
		<div class="form-actions">
			<button class="button" type="submit">Send reset link</button>
			<a href="/sign-in">Back to sign in</a>
		</div>
	</form>
{/if}
