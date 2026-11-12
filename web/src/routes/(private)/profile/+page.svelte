<script lang="ts">
	import Notice from '#lib/components/Notice.svelte';
	import RecordTiles from '#lib/components/RecordTiles.svelte';
	import { authMessage } from '#lib/auth-messages.ts';
	import { LICENCES, LICENCE_LABEL, licenceMessage } from '#lib/currency.ts';
	import { UNIT_NAME, inUnit, weightMessage } from '#lib/wing-loading.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();
	const account = $derived(data.account);
	const errorFor = (name: string) =>
		form && form.form === name && 'error' in form ? authMessage(form.error) : undefined;
	const doneFor = (name: string) => Boolean(form && form.form === name && 'done' in form && form.done);
	// A refused weight re-shows what was typed; otherwise the saved weight in its unit.
	const weightEcho = $derived(
		form && form.form === 'exitWeight' && 'values' in form && form.values ? form.values : null
	);
	const savedWeight = $derived(data.exitWeight?.exit_weight ?? null);
	const weightUnit = $derived(weightEcho?.exit_weight_unit || data.exitWeight?.unit || 'kg');
	const weightValue = $derived(
		weightEcho
			? weightEcho.exit_weight
			: savedWeight
				? String(inUnit(savedWeight.grams, savedWeight.unit))
				: ''
	);
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
<p class="lede">
	Your account, sign-in and records. Your public profile is optional and separate: see
	<a href="#public-heading">Public profile and people</a>.
</p>

<RecordTiles />

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

<section class="card" aria-labelledby="licence-heading">
	<h2 id="licence-heading">Licence</h2>
	<p>
		Private to you. Used only to show your jump currency on your Logbook and History, from USPA
		guidance (USPA SIM 5-2). It is not checked and not a verified status.
	</p>
	<form method="POST" action="?/licence" class="form" novalidate>
		{#if doneFor('licence')}
			<p role="status" class="ok">Licence saved.</p>
		{:else if form && form.form === 'licence' && 'error' in form}
			<p class="form-error" role="alert">{licenceMessage(form.error)}</p>
		{/if}
		{#if data.licence === null}
			<p class="hint">Your current licence could not be loaded. Saving sets it again.</p>
		{/if}
		<div class="field">
			<label for="licence">Licence</label>
			<select id="licence" name="licence">
				{#each LICENCES as value (value)}
					<option {value} selected={(data.licence ?? 'none') === value}>{LICENCE_LABEL[value]}</option>
				{/each}
			</select>
		</div>
		<div class="form-actions">
			<button class="button" type="submit">Save licence</button>
		</div>
	</form>
</section>

<section class="card" aria-labelledby="weight-heading">
	<h2 id="weight-heading">Exit weight</h2>
	<p>
		Private to you. Your weight with your gear on, used only to show the wing loading of your jumps
		(exit weight over the size of your main canopy). A jump can have its own exit weight; this one
		is used for the others. It is not checked and not shared.
	</p>
	<form method="POST" action="?/exitWeight" class="form" novalidate>
		{#if doneFor('exitWeight')}
			<p role="status" class="ok">
				{form && 'cleared' in form && form.cleared ? 'Exit weight removed.' : 'Exit weight saved.'}
			</p>
		{:else if form && form.form === 'exitWeight' && 'error' in form}
			<p class="form-error" role="alert" id="exit-weight-error">{weightMessage(form.error)}</p>
		{/if}
		{#if data.exitWeight === null}
			<p class="hint">Your current exit weight could not be loaded. Saving sets it again.</p>
		{/if}
		<div class="pair">
			<div class="field">
				<label for="exit_weight">Exit weight (optional)</label>
				<input
					id="exit_weight"
					name="exit_weight"
					inputmode="decimal"
					maxlength="6"
					autocomplete="off"
					defaultValue={weightValue}
					aria-describedby="exit-weight-hint"
					aria-invalid={weightEcho && form && 'error' in form ? 'true' : undefined}
				/>
				<p class="hint" id="exit-weight-hint">30 to 250 kg (67 to 551 lb). Leave empty to remove it.</p>
			</div>
			<fieldset class="field">
				<legend>Unit</legend>
				{#each Object.entries(UNIT_NAME) as [value, name] (value)}
					<label class="choice"
						><input
							type="radio"
							name="exit_weight_unit"
							{value}
							defaultChecked={weightUnit === value}
						/>
						{name}</label
					>
				{/each}
			</fieldset>
		</div>
		<div class="form-actions">
			<button class="button" type="submit">Save exit weight</button>
		</div>
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
		prior jump count, licence, private places, saved listings and plans.
	</p>
</section>

<section class="card" aria-labelledby="beta-heading">
	<h2 id="beta-heading">About the beta</h2>
	<p>
		<a href="/privacy">Privacy and the beta</a>: what is private, what you share, deletion and
		recovery, and known limits. <a href="/submit?kind=feedback">Send feedback</a>.
	</p>
</section>

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
