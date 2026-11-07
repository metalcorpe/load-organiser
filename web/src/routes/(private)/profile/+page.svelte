<script lang="ts">
	import Notice from '#lib/components/Notice.svelte';
	import { authMessage } from '#lib/auth-messages.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();
	const account = $derived(data.account);
	const errorFor = (name: string) =>
		form && form.form === name && 'error' in form ? authMessage(form.error) : undefined;
	const doneFor = (name: string) => Boolean(form && form.form === name && 'done' in form && form.done);
	const expires = $derived(
		new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'UTC' }).format(
			new Date(account.sessionExpiresAt)
		)
	);
</script>

<svelte:head>
	<title>Profile · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<h1>Profile</h1>

{#if data.viewer?.reviewer}
	<p><a href="/review">Maintenance</a>: reviewer tools for listings, organizers, dropzones and submissions.</p>
{/if}
<p class="lede">Your account. A public profile is not part of this release yet.</p>

<section class="card" aria-labelledby="account-heading">
	<h2 id="account-heading">Account</h2>
	<dl>
		<dt>Signed in as</dt>
		<dd data-testid="account-email">{account.email}</dd>
		{#if account.displayName}
			<dt>Name</dt>
			<dd>{account.displayName}</dd>
		{/if}
		<dt>Email</dt>
		<dd data-testid="email-status">{account.emailVerified ? 'Confirmed' : 'Not confirmed'}</dd>
		<dt>Session ends</dt>
		<dd>{expires} UTC <span class="hint">(sessions last seven days)</span></dd>
	</dl>

	{#if !account.emailVerified}
		<form method="POST" action="?/resend" class="inline-form">
			{#if doneFor('resend')}
				<p role="status">We sent a new confirmation link. It expires in 30 minutes.</p>
			{:else if errorFor('resend')}
				<p class="form-error" role="alert">{errorFor('resend')}</p>
			{/if}
			<button class="button secondary" type="submit">Send a new confirmation link</button>
		</form>
	{/if}

	<form method="POST" action="/sign-out" class="inline-form">
		<button class="button secondary" type="submit">Sign out</button>
	</form>
</section>

<section class="card" aria-labelledby="password-heading">
	<h2 id="password-heading">Change password</h2>
	{#if doneFor('password')}
		<Notice title="Password changed" tone="ok">
			<p>Other devices were signed out. This one stays signed in.</p>
		</Notice>
	{/if}
	<form method="POST" action="?/password" class="form" novalidate>
		{#if errorFor('password')}
			<p class="form-error" role="alert">{errorFor('password')}</p>
		{/if}
		<div class="field">
			<label for="current_password">Current password</label>
			<input
				id="current_password"
				name="current_password"
				type="password"
				autocomplete="current-password"
				required
				maxlength="1024"
			/>
		</div>
		<div class="field">
			<label for="new_password">New password</label>
			<input
				id="new_password"
				name="new_password"
				type="password"
				autocomplete="new-password"
				required
				minlength="15"
				maxlength="128"
				aria-describedby="new-password-hint"
			/>
			<p class="hint" id="new-password-hint">15 to 128 characters.</p>
		</div>
		<div class="field">
			<label for="new_password_confirm">Repeat new password</label>
			<input
				id="new_password_confirm"
				name="new_password_confirm"
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
</section>

<section class="card" aria-labelledby="everywhere-heading">
	<h2 id="everywhere-heading">Sign out everywhere</h2>
	<p>Ends every session for this account, including this one. Confirm with your password.</p>
	<form method="POST" action="?/revokeAll" class="form" novalidate>
		{#if errorFor('revokeAll')}
			<p class="form-error" role="alert">{errorFor('revokeAll')}</p>
		{/if}
		<div class="field">
			<label for="revoke_password">Password</label>
			<input
				id="revoke_password"
				name="password"
				type="password"
				autocomplete="current-password"
				required
				maxlength="1024"
			/>
		</div>
		<div class="form-actions">
			<button class="button secondary" type="submit">Sign out everywhere</button>
		</div>
	</form>
</section>

<section class="card" aria-labelledby="delete-heading">
	<h2 id="delete-heading">Delete account</h2>
	<p>
		Deletes this account now, with your logbook, gear, places, history, saved listings, plans,
		public profile, follows, blocks, shared jumps and reports you made. Every session ends. This
		cannot be undone; <a href="/profile/data">export your records</a> first if you want a copy.
	</p>
	<p class="hint">
		People who already saw or copied something you shared publicly keep what they copied.
		Suggestions and problem reports you sent about public listings stay with the reviewers,
		unlinked from you; the text you wrote in them is kept.
	</p>
	<form method="POST" action="?/deleteAccount" class="form" novalidate>
		{#if errorFor('deleteAccount')}
			<p class="form-error" role="alert">{errorFor('deleteAccount')}</p>
		{/if}
		<div class="field">
			<label for="delete_password">Password</label>
			<input
				id="delete_password"
				name="password"
				type="password"
				autocomplete="current-password"
				required
				maxlength="1024"
			/>
		</div>
		<label class="choice"><input type="checkbox" name="confirm" /> Delete my account and records</label>
		<div class="form-actions">
			<button class="button secondary" type="submit">Delete account</button>
		</div>
	</form>
</section>

<section class="card" aria-labelledby="public-heading">
	<h2 id="public-heading">Public profile and people</h2>
	<p>
		<a href="/profile/public">Your public profile</a> is optional and separate from this account.
		<a href="/people">People</a>: find people, follow requests, followers and blocked accounts.
	</p>
</section>

<section class="card" aria-labelledby="data-heading">
	<h2 id="data-heading">Your data</h2>
	<p>
		<a href="/profile/data">Export or restore your records</a>: a file with your logbook, gear,
		prior jump count, private places, saved listings and plans.
	</p>
</section>

<Notice title="Not available yet" tone="warn">
	<p>Sharing jumps, the activity feed and account deletion come later.</p>
</Notice>

<style>
	.card {
		border: 1px solid var(--border);
		border-radius: var(--radius);
		background: var(--surface);
		padding: 1rem;
		margin: 1rem 0;
	}

	h2 {
		font-size: 1.1rem;
		margin: 0 0 0.5rem;
	}

	dl {
		display: grid;
		grid-template-columns: max-content 1fr;
		gap: 0.35rem 1rem;
		margin: 0 0 1rem;
	}

	dt {
		color: var(--muted);
	}

	dd {
		margin: 0;
	}

	.inline-form {
		margin: 0.75rem 0 0;
	}
</style>
