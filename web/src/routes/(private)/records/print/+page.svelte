<script lang="ts">
	import PrivacyLabel from '#lib/components/PrivacyLabel.svelte';
	import { count } from '#lib/history.ts';
	import { formatDay } from '#lib/listings.ts';
	import { formatFreefall, paginate, printMessage, type Totals } from '#lib/print.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const o = $derived(data.options);
	const r = $derived(data.result);
	const pages = $derived(r.ok ? paginate(r.jumps, { notes: o.notes, before: r.before }) : []);
	const last = $derived(pages.at(-1) ?? null);
	// Number, date, place, type, exit, freefall, equipment, [notes], signature.
	const columns = $derived(o.notes ? 9 : 8);
	const range = $derived(
		o.from && o.until
			? `${formatDay(o.from)} to ${formatDay(o.until)}`
			: o.from
				? `From ${formatDay(o.from)}`
				: o.until
					? `Until ${formatDay(o.until)}`
					: 'All recorded jumps'
	);
	const totals = (t: Totals) => `${count(t.jumps)} · freefall ${formatFreefall(t.freefall)}`;
</script>

<svelte:head>
	<title>Printable logbook · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<div class="print-root">
	<div class="no-print">
		<p><a href="/records">Records</a> · <a href="/history">History</a></p>
		<h1>Printable logbook</h1>
		<PrivacyLabel />
		<p class="lede">
			Your own entries, oldest first, laid out like a paper logbook with an empty column for an
			instructor's or witness's signature.
		</p>

		<form method="GET" class="options" aria-label="What to print">
			<div class="field">
				<label for="print-from">From</label>
				<input id="print-from" name="from" type="date" defaultValue={o.from} />
			</div>
			<div class="field">
				<label for="print-until">Until</label>
				<input id="print-until" name="until" type="date" defaultValue={o.until} />
			</div>
			<label class="choice">
				<input type="checkbox" name="notes" value="yes" defaultChecked={o.notes} />
				Include notes (shortened)
			</label>
			<button class="button secondary" type="submit">Show</button>
		</form>
		<p class="hint">Leave the dates empty to include every jump. Notes are left out unless you tick the box.</p>

		{#if r.ok && pages.length > 0}
			<p>
				<button class="button" type="button" onclick={() => window.print()}>Print or save as PDF</button>
			</p>
			<noscript>
				<p class="hint">
					The button needs JavaScript. Use your browser's own Print command instead (Ctrl+P, or ⌘P on a
					Mac), then choose a printer or "Save as PDF".
				</p>
			</noscript>
			<p class="hint">Landscape fits best. Each sheet holds up to 12 jumps.</p>
		{/if}
	</div>

	{#if !r.ok}
		<p class="form-error" role="alert">{printMessage(r.reason)}</p>
	{:else if pages.length === 0}
		<p class="hint">No jumps recorded {o.from || o.until ? 'in these dates' : 'yet'}.</p>
	{:else}
		<section class="sheet" aria-labelledby="sheet-title">
			<h2 id="sheet-title">Logbook{o.owner ? ` of ${o.owner}` : ''}</h2>
			<p class="sheet-meta">
				{range} · {count(r.jumps.length)} · printed from Load Organiser. Self-reported entries; a
				signature is the signer's own confirmation.
			</p>
			{#if r.incomplete}
				<p class="form-error" role="alert">Only the first {count(r.jumps.length)} are shown.</p>
			{/if}
			{#if last}
				<p class="sheet-meta" role="status">
					Total to date: {totals(last.toDate)}.
					{#if r.before.jumps > 0}Includes {count(r.before.jumps)} recorded before this range.{/if}
					Freefall adds only jumps with a recorded freefall time.
				</p>
			{/if}

			<!-- Wider than a phone: the scrolling region takes focus so it scrolls by keyboard too. -->
			<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
			<div class="scroll" role="region" aria-label="Logbook sheets" tabindex="0">
				{#each pages as p (p.number)}
					<table class="logbook">
						<caption>Sheet {p.number} of {pages.length}</caption>
						<thead>
							<tr>
								<th scope="col" class="num">No.</th>
								<th scope="col" class="date">Date</th>
								<th scope="col">Place</th>
								<th scope="col">Type</th>
								<th scope="col" class="num">Exit altitude</th>
								<th scope="col" class="num">Freefall</th>
								<th scope="col">Equipment</th>
								{#if o.notes}<th scope="col">Notes</th>{/if}
								<th scope="col" class="sign">Signature</th>
							</tr>
						</thead>
						<tbody>
							{#each p.rows as row (row.id)}
								<tr>
									<td class="num">{row.number}</td>
									<td class="date">{row.date}</td>
									<td>{row.place}</td>
									<td>{row.type}</td>
									<td class="num">{row.exit}</td>
									<td class="num">{row.freefall}</td>
									<td>{row.equipment}</td>
									{#if o.notes}<td class="notes">{row.notes}</td>{/if}
									<td class="sign"></td>
								</tr>
							{/each}
						</tbody>
						<tfoot>
							<tr>
								<th scope="row" colspan="3">This sheet</th>
								<td colspan={columns - 3}>{totals(p.page)}</td>
							</tr>
							<tr>
								<th scope="row" colspan="3">Brought forward</th>
								<td colspan={columns - 3}>{totals(p.broughtForward)}</td>
							</tr>
							<tr>
								<th scope="row" colspan="3">Total to date</th>
								<td colspan={columns - 3}>{totals(p.toDate)}</td>
							</tr>
						</tfoot>
					</table>
				{/each}
			</div>
		</section>
	{/if}
</div>

<style>
	.options {
		display: flex;
		flex-wrap: wrap;
		align-items: end;
		gap: 0.75rem 1rem;
		margin: 1rem 0 0.5rem;
	}

	.sheet h2 {
		margin: 1.25rem 0 0.25rem;
	}

	.sheet-meta {
		margin: 0 0 0.5rem;
		color: var(--muted);
		font-size: 0.92rem;
	}

	.scroll {
		overflow-x: auto;
	}

	.logbook {
		width: 100%;
		min-width: 52rem;
		border-collapse: collapse;
		margin: 0 0 1.5rem;
		font-size: 0.88rem;
		font-variant-numeric: tabular-nums;
	}

	.logbook caption {
		text-align: start;
		font-weight: 600;
		padding-block-end: 0.25rem;
	}

	.logbook th,
	.logbook td {
		border: 1px solid var(--border);
		padding: 0.3rem 0.4rem;
		text-align: start;
		vertical-align: top;
	}

	.logbook thead th {
		background: var(--surface-soft);
	}

	.logbook .num {
		text-align: end;
		white-space: nowrap;
	}

	.logbook .date {
		white-space: nowrap;
	}

	.logbook .sign {
		width: 9rem;
	}

	.logbook tfoot th,
	.logbook tfoot td {
		font-weight: 600;
	}

	@media print {
		/* Only the sheet prints: no options, notices or links. */
		:global(main > :not(.print-root)) {
			display: none !important;
		}

		.print-root {
			page: logbook;
			font-size: 8.5pt;
			color: #000;
		}

		.sheet h2 {
			margin: 0 0 1mm;
			font-size: 12pt;
		}

		.sheet-meta {
			color: #000;
			font-size: 8pt;
		}

		.scroll {
			overflow: visible;
		}

		.logbook {
			min-width: 0;
			font-size: 8.5pt;
			margin: 0;
		}

		/* One sheet a printed page; the header repeats if a sheet still breaks. */
		.logbook + .logbook {
			break-before: page;
		}

		.logbook thead {
			display: table-header-group;
		}

		.logbook tfoot {
			display: table-row-group;
		}

		.logbook tr {
			break-inside: avoid;
		}

		.logbook th,
		.logbook td {
			border: 0.6pt solid #000;
			color: #000;
		}

		.logbook thead th {
			background: none;
			border-bottom-width: 1.2pt;
		}

		/* Room to sign by hand. */
		.logbook tbody td {
			height: 9mm;
		}
	}
</style>
