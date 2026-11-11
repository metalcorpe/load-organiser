<script lang="ts">
	import { page } from '$app/state';
	import type { TotalsOut } from '#lib/contracts/index.ts';
	import { count, historyMessage } from '#lib/history.ts';
	import { formatDay } from '#lib/listings.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();
	const current = $derived(data.history.ok ? data.history.baseline : null);
	const previewing = $derived(data.preview !== null);
	// The version the entered values are based on: kept from the first preview onwards.
	const based = $derived(previewing ? data.based : (current?.version ?? null));
	// Keep the preview in the action URL, so a refused save re-renders it with the error.
	const query = $derived(
		[...page.url.searchParams]
			.filter(([k]) => k === 'prior_jumps' || k === 'before_on' || k === 'version')
			.map(([k, val]) => `${k}=${encodeURIComponent(val)}`)
			.join('&')
	);
	const errorFor = (name: string) =>
		form && form.form === name && 'error' in form ? historyMessage(form.error) : undefined;

	function total(t: TotalsOut): string {
		if (t.inconsistent) return 'Not shown: more entries before the date than declared';
		return t.lifetime === null ? `${count(t.recorded)} recorded (no prior count)` : count(t.lifetime);
	}
	const declared = (n: number | null, on: string | null) =>
		n === null || on === null ? 'None' : `${count(n)} before ${formatDay(on)}`;
	const plain = (v: unknown) => v as { prior_jumps: number; before_on: string };
</script>

<svelte:head>
	<title>Prior jump count · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<p><a href="/history">History</a></p>
<h1>Prior jump count</h1>
<p class="lede">
	Optional. If you jumped before keeping this logbook, declare how many jumps you completed before a
	date. Only you can see it.
</p>
<p class="hint">
	Your total becomes that number plus the jumps you record from that date on. Entries you record before
	the date stay in your logbook but are not counted twice. The count is your own statement: it adds no
	dated jumps or gear use and is not evidence of currency.
</p>

{#if !data.history.ok}
	<p class="form-error" role="alert">{historyMessage(data.history.reason)}</p>
{:else}
	{#if current}
		<p role="status">
			Currently: <strong>{declared(current.prior_jumps, current.before_on)}</strong>
			<span class="meta">(self-declared)</span>
		</p>
	{/if}
	{#if !data.emailVerified}
		<p class="hint">
			Confirm your email address on your <a href="/profile">profile</a> to save a prior jump count.
		</p>
	{/if}

	<form method="GET" action="/history/baseline" class="form" novalidate>
		{#if based}<input type="hidden" name="version" value={based} />{/if}
		<div class="pair">
			<div class="field">
				<label for="prior_jumps">Jumps completed before the date</label>
				<input
					id="prior_jumps"
					name="prior_jumps"
					inputmode="numeric"
					maxlength="7"
					required
					defaultValue={data.entered.prior_jumps || (current?.prior_jumps.toString() ?? '')}
				/>
			</div>
			<div class="field">
				<label for="before_on">Date</label>
				<input
					id="before_on"
					name="before_on"
					type="date"
					required
					defaultValue={data.entered.before_on || (current?.before_on ?? '')}
				/>
			</div>
		</div>
		<p class="hint">For example, 200 jumps before 1 January 2026.</p>
		<div class="form-actions">
			<button class="button secondary" type="submit">Preview</button>
		</div>
	</form>

	{#if data.preview && !data.preview.ok}
		<p class="form-error" role="alert">{historyMessage(data.preview.error)}</p>
	{:else if data.preview?.ok}
		{@const p = data.preview.value}
		<table class="compare">
			<caption>Preview: nothing is saved yet</caption>
			<thead>
				<tr><th scope="col"></th><th scope="col">Now</th><th scope="col">With this change</th></tr>
			</thead>
			<tbody>
				<tr><th scope="row">Reported total</th><td>{total(p.current)}</td><td>{total(p.proposed)}</td></tr>
				<tr>
					<th scope="row">Declared</th>
					<td>{declared(p.current.prior_jumps, p.current.before_on)}</td>
					<td>{declared(p.proposed.prior_jumps, p.proposed.before_on)}</td>
				</tr>
				<tr>
					<th scope="row">Recorded before the date</th>
					<td>{p.current.recorded_before ?? '–'}</td>
					<td>{p.proposed.recorded_before}</td>
				</tr>
				<tr>
					<th scope="row">Recorded from the date on</th>
					<td>{p.current.recorded_since ?? '–'}</td>
					<td>{p.proposed.recorded_since}</td>
				</tr>
			</tbody>
		</table>
		{#if p.proposed.inconsistent}
			<p class="hint" role="note">
				You recorded more jumps before this date than this count declares. You can still save it; no
				combined total is shown until it adds up.
			</p>
		{/if}
		<form method="POST" action="?{query}&/save" class="form">
			{#if errorFor('save')}<p class="form-error" role="alert">{errorFor('save')}</p>{/if}
			<input type="hidden" name="prior_jumps" value={data.preview.prior_jumps} />
			<input type="hidden" name="before_on" value={data.preview.before_on} />
			{#if based}<input type="hidden" name="version" value={based} />{/if}
			<div class="form-actions">
				<button class="button" type="submit" disabled={!data.emailVerified}>Save prior jump count</button>
			</div>
		</form>
	{/if}

	{#if current}
		<h2>Remove</h2>
		<form method="POST" action="?/remove" class="form">
			{#if errorFor('remove')}<p class="form-error" role="alert">{errorFor('remove')}</p>{/if}
			<input type="hidden" name="version" value={current.version} />
			<label class="choice"><input type="checkbox" name="confirm" /> Remove my prior jump count</label>
			<p class="hint">Your recorded jumps are kept. Totals then show recorded entries only.</p>
			<div class="form-actions">
				<button class="button secondary" type="submit" disabled={!data.emailVerified}>Remove</button>
			</div>
		</form>
	{/if}

	{#if data.history.baseline_events.length > 0}
		<h2>Changes</h2>
		<p class="hint">Your private record of what you declared and corrected.</p>
		<ul class="results rows" aria-label="Changes">
			{#each data.history.baseline_events as event, i (i)}
				<li>
					<span class="title">{formatDay(event.created_at.slice(0, 10))}</span>
					<span class="meta">
						{#if event.kind === 'declared'}
							Declared {declared(plain(event.detail).prior_jumps, plain(event.detail).before_on)}
						{:else if event.kind === 'corrected'}
							Corrected from {declared(plain(event.detail.from).prior_jumps, plain(event.detail.from).before_on)}
							to {declared(plain(event.detail.to).prior_jumps, plain(event.detail.to).before_on)}
						{:else if event.kind === 'from_export'}
							Restored from your export: {declared(plain(event.detail).prior_jumps, plain(event.detail).before_on)}
						{:else}
							Removed {declared(plain(event.detail.from).prior_jumps, plain(event.detail.from).before_on)}
						{/if}
					</span>
				</li>
			{/each}
		</ul>
	{/if}
{/if}

<style>
	.compare {
		border-collapse: collapse;
		margin-block: 1rem 0.5rem;
		inline-size: 100%;
	}
	.compare caption {
		text-align: start;
		font-weight: 600;
		padding-block-end: 0.25rem;
	}
	.compare th,
	.compare td {
		padding: 0.35rem 0.5rem 0.35rem 0;
		text-align: start;
		vertical-align: top;
		border-block-end: 1px solid var(--border);
	}
</style>
