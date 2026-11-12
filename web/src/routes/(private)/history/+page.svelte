<script lang="ts">
	import PrivacyLabel from '#lib/components/PrivacyLabel.svelte';
	import { page } from '$app/state';
	import CurrencyStatus from '#lib/components/CurrencyStatus.svelte';
	import Notice from '#lib/components/Notice.svelte';
	import { countryName } from '#lib/countries.ts';
	import { KIND_LABEL } from '#lib/gear.ts';
	import { count, formatMonth, historyMessage } from '#lib/history.ts';
	import { JUMP_TYPE_LABEL } from '#lib/jumps.ts';
	import { formatDay } from '#lib/listings.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const h = $derived(data.history);
	// Bar lengths for the month table, relative to the busiest month (at least 1 to avoid /0).
	const peak = $derived(h.ok ? Math.max(1, ...h.months.map((m) => m.jumps)) : 1);
</script>

<svelte:head>
	<title>History · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<p><a href="/records">Records</a></p>
<h1>History</h1>
<PrivacyLabel />
<p class="lede">Totals from your own entries, private to you.</p>
{#if page.url.searchParams.get('saved')}<p role="status" class="ok">Prior jump count saved.</p>{/if}
{#if page.url.searchParams.get('removed')}
	<p role="status" class="ok">Prior jump count removed. Your recorded jumps are kept.</p>
{/if}

{#if !h.ok}
	<p class="form-error" role="alert">{historyMessage(h.reason)}</p>
{:else}
	{@const t = h.totals}
	<section class="hero" aria-labelledby="totals-heading">
	<h2 id="totals-heading" class="visually-hidden">Totals</h2>
	<p class="big" aria-hidden="true">{count(h.baseline && !t.inconsistent ? (t.lifetime ?? 0) : t.recorded).replace(/ jumps?$/, '')}</p>
	{#if !h.baseline}
		<p role="status"><strong>{count(t.recorded)}</strong> recorded here.</p>
		<p class="hint">
			This counts the entries you logged, not your lifetime total. If you jumped before keeping this
			logbook, you can <a href="/history/baseline">add a prior jump count</a>.
		</p>
	{:else}
		{#if t.inconsistent}
			<Notice title="Check your prior jump count" tone="warn">
				<p role="alert">
					You recorded {count(t.recorded_before ?? 0)} before {formatDay(h.baseline.before_on)}, but
					declared {count(h.baseline.prior_jumps)} before that date. No combined total is shown until
					you correct the count or date, or the entries.
				</p>
				<p><a href="/history/baseline">Correct your prior jump count</a> · <a href="/jumps">Logbook</a></p>
			</Notice>
		{:else}
			<p role="status">
				Reported total: <strong>{count(t.lifetime ?? 0)}</strong>
				<span class="meta"
					>({h.baseline.prior_jumps.toLocaleString('en-GB')} declared + {(
						t.recorded_since ?? 0
					).toLocaleString('en-GB')} recorded since)</span
				>
			</p>
		{/if}
		<dl class="facts">
			<dt>Declared before {formatDay(h.baseline.before_on)}</dt>
			<dd>{count(h.baseline.prior_jumps)} (self-declared, not itemised)</dd>
			<dt>Recorded on or after {formatDay(h.baseline.before_on)}</dt>
			<dd>{count(t.recorded_since ?? 0)}</dd>
			<dt>Recorded before {formatDay(h.baseline.before_on)}</dt>
			<dd>
				{count(t.recorded_before ?? 0)}
				{#if (t.recorded_before ?? 0) > 0}(already within your declared count, not added again){/if}
			</dd>
			<dt>All recorded entries</dt>
			<dd>{count(t.recorded)}</dd>
		</dl>
		<p><a href="/history/baseline">Change prior jump count</a></p>
	{/if}
	</section>

	{#if h.currency}<CurrencyStatus currency={h.currency} today={data.today} />{/if}

	{#if t.recorded === 0}
		<p class="hint">No jumps recorded yet. <a href="/jumps/new">Add jump</a></p>
	{:else}
		<section class="card" aria-labelledby="activity-heading">
		<h2 id="activity-heading">Recent activity</h2>
		<p>
			Last recorded jump: {h.last_jump_on ? formatDay(h.last_jump_on) : 'none'}. First recorded: {h.first_jump_on
				? formatDay(h.first_jump_on)
				: 'none'}.
		</p>
		<table class="months">
			<caption>Recorded jumps in the last 12 months</caption>
			<thead><tr><th scope="col">Month</th><th scope="col">Jumps</th></tr></thead>
			<tbody>
				{#each [...h.months].reverse() as m (m.month)}
					<tr>
						<th scope="row">{formatMonth(m.month)}</th>
						<td><span class="track" aria-hidden="true"><span class="bar" style="--w: {(m.jumps / peak) * 100}%"></span></span>{m.jumps}</td>
					</tr>
				{/each}
			</tbody>
		</table>
		<p class="hint">Recorded entries only; not evidence of currency or eligibility.</p>
		</section>

		<section class="card">
		<h2>By type</h2>
		<ul class="results rows" aria-label="By type">
			{#each h.by_type as item (item.jump_type)}
				<li>
					<span class="title">{JUMP_TYPE_LABEL[item.jump_type] ?? item.jump_type}</span>
					<span class="meta">{count(item.jumps)}</span>
				</li>
			{/each}
		</ul>
		</section>

		<section class="card">
		<h2>By place</h2>
		<ul class="results rows" aria-label="By place">
			{#each h.by_location as item (item.location.kind + item.location.id)}
				<li>
					<span class="title"
						>{item.location.name ??
							(item.location.kind === 'venue' ? 'Dropzone no longer listed' : 'Private place')}</span
					>
					<span class="meta"
						>{item.location.country ? countryName(item.location.country) : ''}{item.location.kind ===
						'place'
							? ' · private place'
							: item.location.closed
								? ' · closed'
								: ''} · {count(item.jumps)}</span
					>
				</li>
			{/each}
		</ul>
		</section>

		<section class="card">
		<h2>Equipment used</h2>
		{#if h.by_component.length === 0}
			<p class="hint">No jump records a component yet.</p>
		{:else}
			<ul class="results rows" aria-label="Equipment used">
				{#each h.by_component as use (use.component.id)}
					<li>
						<a class="title" href="/gear/{use.component.id}">{use.component.label}</a>
						<span class="meta"
							>{KIND_LABEL[use.component.kind] ?? use.component.kind}{use.component.archived
								? ', archived'
								: ''} · {count(use.jumps)} · last {formatDay(use.last_on)}</span
						>
					</li>
				{/each}
			</ul>
		{/if}
		<p class="hint">
			Counts only jumps where you ticked the component. Jumps without recorded gear and your prior jump
			count add no use.
		</p>
		</section>
	{/if}
{/if}

<style>
	/* Totals: the screen's one navy card. */
	.hero {
		margin: 0.5rem 0 1rem;
		padding: 1.1rem;
		border-radius: 22px;
		background: var(--brand);
		color: var(--brand-fg);
	}

	.hero :global(a) {
		color: var(--brand-fg);
	}

	.hero :global(.hint),
	.hero :global(.meta),
	.hero :global(dt) {
		color: var(--brand-muted);
	}

	.big {
		margin: 0 0 0.35rem;
		font-family: var(--font-display);
		font-weight: 700;
		font-size: 3.4rem;
		line-height: 0.95;
		color: var(--highlight);
		font-variant-numeric: tabular-nums;
	}

	/* A fixed track per row, so the bars compare at a glance; the number stays the data. */
	.track {
		display: inline-block;
		width: 9rem;
		height: 0.6rem;
		margin-right: 0.6rem;
		border-radius: 999px;
		background: var(--surface-soft);
		vertical-align: middle;
	}

	.bar {
		display: block;
		width: var(--w);
		height: 100%;
		border-radius: 999px;
		background: var(--accent);
	}

	.months td {
		white-space: nowrap;
	}

	.months {
		border-collapse: collapse;
		margin-block: 0.5rem;
	}
	.months caption {
		text-align: start;
		font-weight: 600;
		padding-block-end: 0.25rem;
	}
	.months th,
	.months td {
		padding: 0.25rem 1rem 0.25rem 0;
		text-align: start;
		border-block-end: 1px solid var(--border);
	}
	.months td {
		text-align: end;
		font-variant-numeric: tabular-nums;
	}
</style>
