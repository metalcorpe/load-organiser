<script lang="ts">
	import PrivacyLabel from '#lib/components/PrivacyLabel.svelte';
	import Notice from '#lib/components/Notice.svelte';
	import { formatDay } from '#lib/listings.ts';
	import { describeCounts, recordsMessage } from '#lib/records.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();
	const errorFor = (name: string) =>
		form && form.form === name && 'error' in form ? recordsMessage(form.error) : undefined;
	const problem = $derived(form && 'problem' in form && form.problem ? form.problem : null);
	const check = $derived(form && form.form === 'check' && 'check' in form ? form.check : null);
	const result = $derived(form && form.form === 'restore' && 'result' in form ? form.result : null);
	const day = (instant: string) => formatDay(instant.slice(0, 10));
</script>

<svelte:head>
	<title>Your data · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<p><a href="/profile">Profile</a></p>
<h1>Your data</h1>
<PrivacyLabel />
<p class="lede">Keep a copy of your records, or bring a copy back. Both are free and private.</p>

{#if !data.records.ok}
	<p class="form-error" role="alert">{recordsMessage(data.records.reason)}</p>
{:else}
	<p role="status">You hold: {describeCounts(data.records.counts)}.</p>
	{#if data.records.last_restore}
		<p class="hint">
			Last restored from a file on {day(data.records.last_restore.restored_at)}.
		</p>
	{/if}
{/if}

<section class="card" aria-labelledby="export-heading">
	<h2 id="export-heading">Export</h2>
	<p>All your private records in one JSON file.</p>
	<p class="hint">
		It holds your private notes and serial numbers, so store it somewhere safe. One export every
		five minutes.
	</p>
	<details class="included">
		<summary>What's included?</summary>
		<p>
			Format version 1: your jumps and their history, gear with rigs and service entries, your
			prior jump count, licence, private places, saved listings and visit plans, plus the names of
			the public dropzones and listings they point to.
		</p>
		<p>
			It does not contain your password, sessions, email address or any other person's records.
		</p>
	</details>
	{#if data.exportRefused}
		<p class="form-error" role="alert">{recordsMessage(data.exportRefused)}</p>
	{/if}
	<form method="POST" action="/profile/data/export" class="form">
		<div class="form-actions">
			<button class="button" type="submit">Download export</button>
		</div>
	</form>
</section>

<section class="card" aria-labelledby="restore-heading">
	<h2 id="restore-heading">Restore</h2>
	<p>
		Restore brings back an export of your records into <strong>empty</strong> records only. It never
		overwrites or merges. Restoring the same file again changes nothing.
	</p>
	<p class="hint">
		Check a file first to see what it holds. Dropzones and listings that are no longer published come
		back as private places or without their link.
	</p>

	{#if check}
		<Notice
			title={check.eligible ? 'Ready to restore' : 'This file cannot be restored here'}
			tone={check.eligible ? 'ok' : 'warn'}
		>
			<p role="status">
				Exported on {day(check.exported_at)}: {describeCounts(check.counts)}.
			</p>
			{#if check.venues_to_private_places > 0}
				<p>
					{check.venues_to_private_places} dropzone{check.venues_to_private_places === 1 ? ' is' : 's are'}
					no longer listed and will come back as private places.
				</p>
			{/if}
			{#if check.plan_links_dropped > 0}
				<p>{check.plan_links_dropped} plan link{check.plan_links_dropped === 1 ? '' : 's'} to a listing no longer published will be dropped; the plans stay.</p>
			{/if}
			{#if check.saved_not_restorable.length > 0}
				<p>Saved listings no longer published, not restored: {check.saved_not_restorable.join('; ')}.</p>
			{/if}
			{#if check.reason === 'already_restored' && check.already_restored_at}
				<p>This exact file was already restored on {day(check.already_restored_at)}. Restoring it again changes nothing.</p>
			{:else if check.reason === 'records_not_empty'}
				<p>{recordsMessage('records_not_empty')}</p>
			{:else}
				<p>Choose the same file again below and confirm with your password to restore it.</p>
			{/if}
		</Notice>
	{/if}

	{#if result}
		<Notice
			title={result.outcome === 'restored' ? 'Restored' : 'Already restored'}
			tone="ok"
		>
			<p role="status">
				{#if result.outcome === 'restored'}
					Restored {describeCounts(result.counts)}.
				{:else}
					This exact file was already restored on {day(result.restored_at)}. Nothing was changed.
				{/if}
			</p>
			<p><a href="/jumps">Logbook</a> · <a href="/history">History</a> · <a href="/gear">Gear</a></p>
		</Notice>
	{/if}

	<form method="POST" action="?/check" class="form" enctype="multipart/form-data" novalidate>
		{#if errorFor('check')}
			<p class="form-error" role="alert">{errorFor('check')}</p>
			{#if problem}<p class="hint">Problem found at: <code>{problem}</code></p>{/if}
		{/if}
		<div class="field">
			<label for="check_archive">Export file to check</label>
			<input id="check_archive" name="archive" type="file" accept=".json,application/json" />
		</div>
		<div class="form-actions">
			<button class="button secondary" type="submit">Check file</button>
		</div>
	</form>

	<form method="POST" action="?/restore" class="form" enctype="multipart/form-data" novalidate>
		{#if errorFor('restore')}
			<p class="form-error" role="alert">{errorFor('restore')}</p>
			{#if problem}<p class="hint">Problem found at: <code>{problem}</code></p>{/if}
		{/if}
		{#if !data.emailVerified}
			<p class="hint">Confirm your email address on your <a href="/profile">profile</a> to restore.</p>
		{/if}
		<div class="field">
			<label for="restore_archive">Export file to restore</label>
			<input id="restore_archive" name="archive" type="file" accept=".json,application/json" />
		</div>
		<div class="field">
			<label for="restore_password">Password</label>
			<input
				id="restore_password"
				name="password"
				type="password"
				autocomplete="current-password"
				maxlength="1024"
			/>
		</div>
		<div class="form-actions">
			<button class="button" type="submit" disabled={!data.emailVerified}>Restore into empty records</button>
		</div>
	</form>
</section>

<style>
	.included p {
		margin: 0 0 0.5rem;
		font-size: 0.95rem;
	}

	.card {
		border: 1px solid var(--border);
		border-radius: var(--radius);
		background: var(--surface);
		padding: 1rem;
		margin: 1rem 0;
	}
</style>
