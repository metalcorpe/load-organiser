<script lang="ts">
	import Notice from '#lib/components/Notice.svelte';
	import { authMessage } from '#lib/auth-messages.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();
	const error = $derived(authMessage(form?.error));
	const registerHref = $derived(
		data.returnTo ? `/register?returnTo=${encodeURIComponent(data.returnTo)}` : '/register'
	);
</script>

<svelte:head>
	<title>Sign in · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<h1>Sign in</h1>

{#if data.notice === 'reset'}
	<Notice title="Password changed" tone="ok">
		<p>You were signed out everywhere. Sign in with your new password.</p>
	</Notice>
{:else if data.notice === 'signed-out'}
	<Notice title="Signed out" tone="ok"><p>You are signed out on this device.</p></Notice>
{:else if data.notice === 'account-deleted'}
	<Notice title="Account deleted" tone="ok">
		<p>
			Your account and everything it held have been deleted, and every session has ended. You can
			register again with the same address; it starts empty.
		</p>
	</Notice>
{:else if data.notice === 'signed-out-everywhere'}
	<Notice title="Signed out everywhere" tone="ok">
		<p>Every session for your account has ended, including this one.</p>
	</Notice>
{:else if data.notice === 'signed-out-unconfirmed'}
	<Notice title="Signed out on this device" tone="warn">
		<p>
			The service could not confirm the sign-out. If this was a shared device, sign in later and
			use “Sign out everywhere”.
		</p>
	</Notice>
{:else if data.notice === 'verified'}
	<Notice title="Email confirmed" tone="ok"><p>Sign in to continue.</p></Notice>
{/if}

{#if data.sessionUnconfirmed}
	<Notice title="Session not confirmed" tone="warn">
		<p>
			The service could not be reached to confirm your session. Try again shortly, or
			<a href="/sign-out">sign out on this device</a>.
		</p>
	</Notice>
{/if}

{#if data.returnTo}
	<p class="lede">Sign in to continue to the page you asked for.</p>
{/if}

<form method="POST" class="form" novalidate>
	{#if error}
		<p class="form-error" role="alert" id="sign-in-error">{error}</p>
	{/if}
	<div class="field">
		<label for="email">Email</label>
		<input
			id="email"
			name="email"
			type="email"
			autocomplete="username"
			required
			maxlength="254"
			defaultValue={form?.email ?? ''}
			aria-invalid={error ? 'true' : undefined}
			aria-describedby={error ? 'sign-in-error' : undefined}
		/>
	</div>
	<div class="field">
		<label for="password">Password</label>
		<input
			id="password"
			name="password"
			type="password"
			autocomplete="current-password"
			required
			maxlength="1024"
			aria-invalid={error ? 'true' : undefined}
			aria-describedby={error ? 'sign-in-error' : undefined}
		/>
	</div>
	<div class="form-actions">
		<button class="button" type="submit">Sign in</button>
		<a href="/forgot-password">Forgot password?</a>
	</div>
</form>

<p>New here? <a href={registerHref}>Create an account</a></p>
<p class="hint">Sessions last seven days, then you sign in again.</p>
