<script lang="ts">
	import { page } from '$app/state';
	import PrivacyLabel from '#lib/components/PrivacyLabel.svelte';
	import { fieldsFor } from '#lib/field-errors.ts';
	import { freefallText, jumpsHref } from '#lib/jump-filters.ts';
	import { JUMP_TYPE_LABEL, jumpMessage } from '#lib/jumps.ts';
	import { formatDay, formatRange } from '#lib/listings.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const n = (value: number) => value.toLocaleString('en-GB');
	const pick = (loc: { kind: 'venue' | 'place'; id: string }) => `/jumps/new?${loc.kind}=${loc.id}`;
	const first = $derived(data.recent[0] ?? null);
	const f = $derived(data.filters);
	// A refused filter (e.g. dates out of order) keeps the form and marks its field.
	const filterError = $derived(
		!data.page.ok && fieldsFor(data.page.reason).length > 0 ? data.page.reason : null
	);
	const invalid = $derived(new Set(fieldsFor(filterError)));
	const moreFilters = $derived(
		Boolean(f.type || f.at || f.from || f.to || f.from_number || f.to_number)
	);
	const atKnown = $derived(!f.at || data.places.some((p) => p.value === f.at));
	const matched = $derived(data.page.ok ? data.page.matched : null);
	const freefall = $derived(
		matched ? freefallText(matched.freefall_seconds, matched.freefall_recorded, matched.jumps) : null
	);
	const described = (name: string) =>
		invalid.has(name) ? { 'aria-invalid': 'true' as const, 'aria-describedby': 'filter-error' } : {};
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

{#if filterError}
	<p class="form-error" role="alert" id="filter-error">{jumpMessage(filterError)}</p>
{/if}
<!-- defaultValue keeps text typed before hydration; the key resets the fields when
     the URL's filters change (Clear filters, back/forward). -->
{#key page.url.search}
	<form method="GET" action="/jumps" class="jump-search" role="search">
		<div class="search-row">
			<label class="visually-hidden" for="q">Place or notes</label>
			<input
				id="q"
				name="q"
				type="search"
				maxlength="100"
				placeholder="Search places and notes"
				defaultValue={f.q}
				autocomplete="off"
			/>
			<button class="button" type="submit">Search</button>
		</div>
		<details class="more" open={moreFilters || Boolean(filterError)}>
			<summary class="disclosure">Filters</summary>
			<div class="form filters">
				<div class="field">
					<label for="type">Type</label>
					<select id="type" name="type">
						<option value="" selected={!f.type}>Any type</option>
						{#each Object.entries(JUMP_TYPE_LABEL) as [value, label] (value)}
							<option {value} selected={value === f.type}>{label}</option>
						{/each}
					</select>
				</div>
				<div class="field">
					<label for="at">Place</label>
					<select id="at" name="at">
						<option value="" selected={!f.at}>Any place</option>
						{#if !atKnown}<option value={f.at} selected>The chosen place</option>{/if}
						{#each data.places as option (option.value)}
							<option value={option.value} selected={option.value === f.at}>{option.label}</option>
						{/each}
					</select>
				</div>
				<div class="field">
					<label for="from">From date</label>
					<input id="from" name="from" type="date" defaultValue={f.from} {...described('from')} />
				</div>
				<div class="field">
					<label for="to">To date</label>
					<input id="to" name="to" type="date" defaultValue={f.to} {...described('to')} />
				</div>
				<div class="field">
					<label for="from_number">From jump number</label>
					<input
						id="from_number"
						name="from_number"
						inputmode="numeric"
						maxlength="7"
						defaultValue={f.from_number}
						{...described('from_number')}
					/>
				</div>
				<div class="field">
					<label for="to_number">To jump number</label>
					<input
						id="to_number"
						name="to_number"
						inputmode="numeric"
						maxlength="7"
						defaultValue={f.to_number}
						{...described('to_number')}
					/>
				</div>
				<div class="form-actions wide">
					<button class="button" type="submit">Show jumps</button>
					{#if data.filtered}<a href="/jumps">Clear filters</a>{/if}
				</div>
			</div>
		</details>
	</form>
{/key}

{#if !data.page.ok}
	{#if !filterError}<p class="form-error" role="alert">{jumpMessage(data.page.reason)}</p>{/if}
{:else}
	{#if data.filtered && matched}
		<section class="matched" aria-label="Matching jumps">
			<p>
				<strong>{n(matched.jumps)} {matched.jumps === 1 ? 'jump matches' : 'jumps match'}</strong>
				{#if matched.first_on && matched.last_on}
					· {formatRange(matched.first_on, matched.last_on)}{/if}
				{#if freefall}· {freefall}{/if}
			</p>
			{#if data.page.items.length > 0}<p><a href="/jumps">Clear filters</a></p>{/if}
		</section>
	{/if}
	{#if !data.older && !data.filtered}
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

	{#if data.numbering.notes.length > 0}
		<section class="numbering" aria-labelledby="numbering-heading">
			<h2 id="numbering-heading">Jump numbers to check</h2>
			<ul>
				{#each data.numbering.notes as note (note.text)}
					<li>
						{#if note.kind === 'gap'}
							{note.text}, between <a href="/jumps/{note.before.id}">#{note.before.number}</a> and
							<a href="/jumps/{note.after.id}">#{note.after.number}</a>.
						{:else}
							{note.text}:
							{#each note.jumps as jump, i (jump.id)}{i > 0 ? ', ' : ''}<a href="/jumps/{jump.id}"
									>{formatDay(jump.jumped_on)}</a
								>{/each}.
						{/if}
					</li>
				{/each}
			</ul>
			{#if data.numbering.more}<p>{data.numbering.more}</p>{/if}
		</section>
	{/if}

	{#if data.page.items.length === 0 && data.filtered}
		<p class="hint">
			{data.older ? 'No older matching jumps.' : 'No jumps match these filters.'}
			<a href="/jumps">Clear filters</a>
		</p>
	{:else if data.page.items.length === 0}
		<p class="hint">
			{data.older ? 'No older entries.' : 'No jumps yet. Only the date, place and type are needed.'}
		</p>
		{#if !data.older}
			<p>Have a logbook already? <a href="/records/import">Import a spreadsheet</a></p>
		{/if}
	{:else}
		<h2>{data.filtered ? 'Matching jumps' : data.older ? 'Older jumps' : 'Recent jumps'}</h2>
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
		{#if data.older}<a href={jumpsHref(data.filters)}>Newest</a>{/if}
		{#if data.page.next_cursor}
			<a href={jumpsHref(data.filters, data.page.next_cursor)} rel="next">Older jumps</a>
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

	.jump-search {
		margin: 0 0 1rem;
	}

	.search-row {
		display: flex;
		gap: 0.5rem;
	}

	.search-row input {
		flex: 1;
		min-width: 0;
		min-height: 44px;
		padding: 0.5rem 0.75rem;
		border: 1px solid var(--field-border);
		border-radius: 9px;
		background: var(--field);
		color: var(--fg);
		font: inherit;
	}

	.more {
		margin-top: 0.25rem;
	}

	.filters {
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 12rem), 1fr));
		margin: 0.25rem 0 0;
		padding: 0.85rem;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		background: var(--surface);
	}

	.wide {
		grid-column: 1 / -1;
		align-items: center;
	}

	.matched {
		margin: 0 0 1rem;
		padding: 0.75rem 0.9rem;
		border-radius: var(--radius);
		background: var(--surface-soft);
	}

	.matched p {
		margin: 0;
	}

	.matched p + p {
		margin-top: 0.25rem;
	}

	.numbering {
		margin: 0 0 1.25rem;
		padding: 0.75rem 0.9rem;
		border-radius: var(--radius);
		background: var(--surface-soft);
		font-size: 0.95rem;
	}

	.numbering h2 {
		font-size: 1rem;
		margin: 0 0 0.25rem;
	}

	.numbering ul {
		margin: 0;
		padding-left: 1.1rem;
	}

	.numbering p {
		margin: 0.25rem 0 0;
	}
</style>
