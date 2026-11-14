<script lang="ts">
	import RecordTiles, { type RecordGroup } from '#lib/components/RecordTiles.svelte';
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
	// Me's own groups after the records: people and the rest. Account and security is linked
	// once, from the account card. The licence and exit weight come first on this page (the
	// logbook, History and Statistics link to their anchors), the links after them.
	const extra = $derived<RecordGroup[]>([
		{
			id: 'people',
			heading: 'People',
			items: [
				{ href: '/profile/public', name: 'Your public profile', text: '' },
				{ href: '/people', name: 'People and follow requests', text: '' }
			]
		},
		{
			id: 'more',
			heading: 'More',
			items: [
				{ href: '/privacy', name: 'Privacy and the beta', text: '' },
				{ href: '/submit?kind=feedback', name: 'Send feedback', text: '' },
				...(data.viewer?.reviewer
					? [{ href: '/review', name: 'Maintenance (reviewer tools)', text: '' }]
					: [])
			]
		}
	]);
</script>

<svelte:head>
	<title>Profile · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<h1>Profile</h1>

<section class="card summary" aria-labelledby="account-heading">
	<h2 id="account-heading" class="visually-hidden">Account</h2>
	<dl>
		<dt>Signed in as</dt>
		<dd data-testid="account-email">{account.email}</dd>
		<dt>Email</dt>
		<dd data-testid="email-status">{account.emailVerified ? 'Confirmed' : 'Not confirmed'}</dd>
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

	<div class="summary-actions">
		<a href="/profile/account" aria-describedby="account-link-hint">Account and security</a>
		<span class="visually-hidden" id="account-link-hint"
			>Password, sign out everywhere and deleting the account</span
		>
		<form method="POST" action="/sign-out">
			<button class="button secondary" type="submit">Sign out</button>
		</form>
	</div>
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

<!-- Everything else, in one compact card. -->
<nav aria-label="Your records and more">
	<RecordTiles compact {extra} />
</nav>

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

	.summary dl {
		margin: 0;
	}

	.summary-actions {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem 1rem;
		align-items: center;
		justify-content: space-between;
		margin: 0.75rem 0 0.25rem;
	}

	.summary-actions a {
		display: inline-flex;
		align-items: center;
		min-height: 44px;
		font-weight: 600;
	}

	.summary-actions form {
		margin: 0;
	}

	.pair {
		display: grid;
		gap: 1rem;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 12rem), 1fr));
	}
</style>
