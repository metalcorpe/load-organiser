<script lang="ts">
	import Notice from '#lib/components/Notice.svelte';
	import PasswordInput from '#lib/components/PasswordInput.svelte';
	import { authMessage } from '#lib/auth-messages.ts';
	import { errorSummary, fieldMessage, type FieldErrors } from '#lib/account-form.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();
	const fields: FieldErrors = $derived(form && 'fields' in form ? (form.fields ?? {}) : {});
	const error = $derived(
		form && 'error' in form ? (errorSummary(fields) ?? authMessage(form.error)) : undefined
	);
	// The ids describing a field: its own hint and error, if any.
	const describe = (...ids: (string | false | undefined)[]) => ids.filter(Boolean).join(' ') || undefined;
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

	<!-- novalidate: the server checks each field and says what is wrong with it. -->
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
				aria-invalid={fields.email ? 'true' : undefined}
				aria-describedby={describe(fields.email && 'email-error')}
			/>
			{#if fields.email}<p class="field-error" id="email-error">{fieldMessage(fields.email)}</p>{/if}
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
			<PasswordInput
				id="password"
				name="password"
				autocomplete="new-password"
				required
				minlength={15}
				maxlength={128}
				invalid={Boolean(fields.password)}
				describedby={describe('password-hint', fields.password && 'password-error')}
			/>
			<p class="hint" id="password-hint">
				15 to 128 characters. Any characters, spaces and emoji work; a passphrase is fine.
			</p>
			{#if fields.password}
				<p class="field-error" id="password-error">{fieldMessage(fields.password)}</p>
			{/if}
		</div>
		<div class="field">
			<label for="password_confirm">Repeat password</label>
			<PasswordInput
				id="password_confirm"
				name="password_confirm"
				autocomplete="new-password"
				what="repeated password"
				required
				minlength={15}
				maxlength={128}
				invalid={Boolean(fields.password_confirm)}
				describedby={describe(fields.password_confirm && 'password-confirm-error')}
			/>
			{#if fields.password_confirm}
				<p class="field-error" id="password-confirm-error">
					{fieldMessage(fields.password_confirm)}
				</p>
			{/if}
		</div>
		<div class="form-actions">
			<button class="button" type="submit">Create account</button>
		</div>
	</form>

	<p>Already have an account? <a href={signInHref}>Sign in</a></p>
{/if}
