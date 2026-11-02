<script lang="ts">
	import Notice from '#lib/components/Notice.svelte';
	import { authMessage } from '#lib/auth-messages.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();
	const error = $derived(form && 'error' in form ? authMessage(form.error) : undefined);
	const signInHref = $derived(
		data.returnTo ? `/sign-in?returnTo=${encodeURIComponent(data.returnTo)}` : '/sign-in'
	);
</script>

<svelte:head>
	<title>Create account · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<h1>Create account</h1>

{#if form && 'sent' in form && form.sent}
	<Notice title="Check your email" tone="ok">
		<p>
			If <strong>{form.email}</strong> can be registered, we sent a link to confirm it. The link works
			once and expires in 30 minutes.
		</p>
		<p>You can sign in now; saving private records needs a confirmed email.</p>
	</Notice>
	<p><a class="button" href={signInHref}>Sign in</a></p>
{:else}
	<p class="lede">
		An account keeps your records private to you. You do not need a dropzone membership or a public
		profile.
	</p>

	<form method="POST" class="form" novalidate>
		{#if error}
			<p class="form-error" role="alert" id="register-error">{error}</p>
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
		<div class="field">
			<label for="display_name">Name <span class="hint">(optional, private for now)</span></label>
			<input
				id="display_name"
				name="display_name"
				type="text"
				autocomplete="nickname"
				maxlength="80"
				defaultValue={form?.displayName ?? ''}
			/>
		</div>
		<div class="field">
			<label for="password">Password</label>
			<input
				id="password"
				name="password"
				type="password"
				autocomplete="new-password"
				required
				minlength="15"
				maxlength="128"
				aria-describedby="password-hint{error ? ' register-error' : ''}"
			/>
			<p class="hint" id="password-hint">
				15 to 128 characters. Any characters, spaces and emoji work; a passphrase is fine.
			</p>
		</div>
		<div class="field">
			<label for="password_confirm">Repeat password</label>
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
			<button class="button" type="submit">Create account</button>
		</div>
	</form>

	<p>Already have an account? <a href={signInHref}>Sign in</a></p>
{/if}
