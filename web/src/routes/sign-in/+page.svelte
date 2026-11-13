<script lang="ts">
	import Notice from '#lib/components/Notice.svelte';
	import PasswordInput from '#lib/components/PasswordInput.svelte';
	import { authMessage } from '#lib/auth-messages.ts';
	import { errorSummary, fieldMessage, type FieldErrors } from '#lib/account-form.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();
	const fields: FieldErrors = $derived(form?.fields ?? {});
	const error = $derived(errorSummary(fields) ?? authMessage(form?.error));
	// As in the sign-in sheet: a field problem marks and describes only that field; refused
	// details mark both (the answer never says which) and point them at the alert. Throttling or
	// an outage says nothing about the fields.
	const refused = $derived(form?.error === 'invalid_credentials');
	const invalid = (name: 'email' | 'password') => Boolean(fields[name] || refused);
	const describedBy = (name: 'email' | 'password') =>
		fields[name] ? `${name}-error` : refused ? 'sign-in-error' : undefined;
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
			aria-invalid={invalid('email') ? 'true' : undefined}
			aria-describedby={describedBy('email')}
		/>
		{#if fields.email}<p class="field-error" id="email-error">{fieldMessage(fields.email)}</p>{/if}
	</div>
	<div class="field">
		<label for="password">Password</label>
		<PasswordInput
			id="password"
			name="password"
			autocomplete="current-password"
			required
			maxlength={1024}
			invalid={invalid('password')}
			describedby={describedBy('password')}
		/>
		{#if fields.password}
			<p class="field-error" id="password-error">{fieldMessage(fields.password)}</p>
		{/if}
	</div>
	<div class="form-actions">
		<button class="button" type="submit">Sign in</button>
		<a href="/forgot-password">Forgot password?</a>
	</div>
</form>

<p>New here? <a href={registerHref}>Create an account</a></p>
<p class="hint">Sessions last seven days, then you sign in again.</p>
