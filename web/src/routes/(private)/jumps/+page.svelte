<script lang="ts">
	import PrivacyLabel from '#lib/components/PrivacyLabel.svelte';
	import { JUMP_TYPE_LABEL, jumpMessage } from '#lib/jumps.ts';
	import { formatDay } from '#lib/listings.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const n = (value: number) => value.toLocaleString('en-GB');
	const pick = (loc: { kind: 'venue' | 'place'; id: string }) => `/jumps/new?${loc.kind}=${loc.id}`;
	const first = $derived(data.recent[0] ?? null);
</script>

<svelte:head>
	<title>Logbook · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<div class="head">
	<h1>Logbook</h1>
	<a href="/history">History</a>
</div>
<PrivacyLabel text="Private logbook — only you can see your jumps" />

{#if !data.page.ok}
	<p class="form-error" role="alert">{jumpMessage(data.page.reason)}</p>
{:else}
	{#if !data.older}
		<!-- The screen's one navy card: totals and the main action. -->
		<section class="card" aria-label="Totals and log a jump">
			<div class="totals">
				<p class="big">
					<span class="number">{n(data.summary?.lifetime ?? data.page.recorded_total)}</span>
					<span class="unit"
						>{(data.summary?.lifetime ?? data.page.recorded_total) === 1 ? 'jump' : 'jumps'}</span
					>
				</p>
				<div class="side">
					<p>
						{n(data.page.recorded_total)}
						{data.page.recorded_total === 1 ? 'jump' : 'jumps'} recorded here.
					</p>
					{#if data.summary?.lastJumpOn}<p>Last: {formatDay(data.summary.lastJumpOn)}</p>{/if}
				</div>
			</div>
			{#if first}
				{#if data.continueFrom}
					<a class="button log" href="{pick(first)}&from={data.continueFrom}">Log the next jump at {first.name}</a>
				{:else}
					<a class="button log" href={pick(first)}>Log a jump at {first.name}</a>
				{/if}
				<p class="others">
					{#each data.recent.slice(1) as loc (loc.kind + loc.id)}
						<a class="chip" href={pick(loc)}>{loc.name}</a>
					{/each}
					<a class="chip" href="/jumps/new">Other place</a>
				</p>
			{:else}
				<a class="button log" href="/jumps/new">Log your first jump</a>
			{/if}
		</section>
	{/if}

	{#if data.page.items.length === 0}
		<p class="hint">
			{data.older ? 'No older entries.' : 'No jumps yet. Only the date, place and type are needed.'}
		</p>
	{:else}
		<h2>{data.older ? 'Older jumps' : 'Recent jumps'}</h2>
		<ul class="jumps" aria-label="Jumps">
			{#each data.page.items as jump (jump.id)}
				<li>
					<span class="num" aria-hidden="true">{jump.jump_number ?? '–'}</span>
					<span class="text">
						<a class="title" href="/jumps/{jump.id}"
							>{formatDay(jump.jumped_on)}{jump.jump_number ? ` · #${jump.jump_number}` : ''}</a
						>
						<span class="meta"
							>{JUMP_TYPE_LABEL[jump.jump_type]} · {jump.location.name ?? 'Dropzone no longer listed'}{jump
								.location.kind === 'place'
								? ' (private place)'
								: ''}</span
						>
						{#if jump.components.length > 0}
							<span class="meta">Gear: {jump.components.map((c) => c.label).join(', ')}</span>
						{/if}
					</span>
				</li>
			{/each}
		</ul>
	{/if}
	<p class="pager">
		{#if data.older}<a href="/jumps">Newest</a>{/if}
		{#if data.page.next_cursor}
			<a href="/jumps?cursor={encodeURIComponent(data.page.next_cursor)}">Older jumps</a>
		{/if}
	</p>
{/if}

<style>
	.head {
		display: flex;
		justify-content: space-between;
		align-items: baseline;
	}

	.head a {
		font-weight: 600;
	}

	.card {
		display: grid;
		gap: 0.9rem;
		margin: 0.25rem 0 1.25rem;
		padding: 1.1rem;
		border-radius: 22px;
		background: var(--brand);
		color: var(--brand-fg);
	}

	.card p {
		margin: 0;
	}

	.totals {
		display: flex;
		justify-content: space-between;
		align-items: flex-end;
		gap: 0.75rem;
	}

	.big {
		display: flex;
		align-items: baseline;
		gap: 0.4rem;
	}

	.number {
		font-family: var(--font-display);
		font-weight: 700;
		font-size: 3.6rem;
		line-height: 0.9;
		color: var(--highlight);
		font-variant-numeric: tabular-nums;
	}

	.unit {
		font-family: var(--font-display);
		font-weight: 600;
		font-size: 1.1rem;
		color: var(--brand-muted);
	}

	.side {
		display: grid;
		justify-items: end;
		text-align: right;
		font-size: 0.85rem;
		color: var(--brand-muted);
	}

	.log {
		width: 100%;
		border-radius: 999px;
		min-height: 52px;
	}

	.others {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
	}

	.chip {
		display: inline-flex;
		align-items: center;
		min-height: 44px;
		padding: 0 0.9rem;
		border-radius: 999px;
		border: 1px solid color-mix(in srgb, var(--brand-fg) 30%, transparent);
		color: var(--brand-fg);
		text-decoration: none;
	}

	h2 {
		font-size: 1.15rem;
		margin: 0 0 0.5rem;
	}

	.jumps {
		list-style: none;
		padding: 0;
		margin: 0;
		display: grid;
		gap: 0.5rem;
	}

	.jumps li {
		position: relative;
		display: grid;
		grid-template-columns: 3rem 1fr;
		gap: 0.8rem;
		align-items: center;
		padding: 0.6rem 0.75rem;
		border-radius: var(--radius);
		background: var(--surface);
		box-shadow: 0 0 0 1px var(--border);
	}

	.num {
		display: grid;
		place-items: center;
		height: 2.8rem;
		border-radius: 12px;
		background: var(--surface-soft);
		font-family: var(--font-display);
		font-weight: 700;
	}

	.text {
		display: grid;
		gap: 0.1rem;
		min-width: 0;
	}

	.title {
		font-weight: 600;
		color: var(--fg);
		text-decoration: none;
	}

	/* The whole row is one tap target. */
	.title::after {
		content: '';
		position: absolute;
		inset: 0;
		border-radius: var(--radius);
	}

	.meta {
		color: var(--muted);
		font-size: 0.9rem;
	}

	.pager {
		display: flex;
		gap: 1rem;
	}
</style>
