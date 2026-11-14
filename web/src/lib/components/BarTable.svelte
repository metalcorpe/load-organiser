<script lang="ts" module>
	/**
	 * A small bar chart that is a data table: one row per item, the number as text
	 * and a decorative bar beside it (hidden from assistive technology). Bars are
	 * relative to the largest value, so they compare at a glance; the numbers stay
	 * the data. The same pattern as History's recent activity.
	 */
	export type BarRow = {
		/** Row header, e.g. "Oct 2026", "Freefly". */
		label: string;
		/** The number the bar shows; 0 or null draws no bar. */
		value: number | null;
		/** The cell text; defaults to the value in en-GB format, or "–" for null. */
		text?: string;
		/** A second, plain cell (e.g. a count) when the table has `extra`. */
		extra?: string;
	};
</script>

<script lang="ts">
	let {
		caption,
		rowHeader,
		valueHeader,
		extraHeader = null,
		rows,
		hint = null
	}: {
		caption: string;
		rowHeader: string;
		valueHeader: string;
		extraHeader?: string | null;
		rows: BarRow[];
		/** A short note under the table, e.g. what is counted. */
		hint?: string | null;
	} = $props();

	const peak = $derived(Math.max(0, ...rows.map((r) => r.value ?? 0)));
	const width = (value: number | null) => (peak > 0 && value ? (value / peak) * 100 : 0);
	const text = (row: BarRow) =>
		row.text ?? (row.value === null ? '–' : row.value.toLocaleString('en-GB'));
</script>

<table class="bars">
	<caption>{caption}</caption>
	<thead>
		<tr>
			<th scope="col">{rowHeader}</th>
			<th scope="col" class="value">{valueHeader}</th>
			{#if extraHeader}<th scope="col" class="value">{extraHeader}</th>{/if}
		</tr>
	</thead>
	<tbody>
		{#each rows as row, i (i)}
			<tr>
				<th scope="row">{row.label}</th>
				<td class="value"
					><span class="track" aria-hidden="true"><span class="bar" style="--w: {width(row.value)}%"></span></span
					>{text(row)}</td
				>
				{#if extraHeader}<td class="value">{row.extra ?? ''}</td>{/if}
			</tr>
		{/each}
	</tbody>
</table>
{#if hint}<p class="hint">{hint}</p>{/if}

<style>
	.bars {
		border-collapse: collapse;
		margin-block: 0.5rem;
		max-width: 100%;
	}

	.bars caption {
		text-align: start;
		font-weight: 600;
		padding-block-end: 0.25rem;
	}

	.bars th,
	.bars td {
		padding: 0.25rem 1rem 0.25rem 0;
		text-align: start;
		border-block-end: 1px solid var(--border);
		font-weight: normal;
	}

	.bars thead th {
		font-weight: 600;
	}

	/* The labels share each row with a fixed-width bar; with large text a long label (a place
	   name) breaks inside a word rather than widening the table past the screen. */
	.bars th {
		overflow-wrap: anywhere;
	}

	.bars .value {
		text-align: end;
		white-space: nowrap;
		font-variant-numeric: tabular-nums;
	}

	/* A fixed track per row, so the bars compare at a glance; the number stays the data. */
	.track {
		display: inline-block;
		width: clamp(4rem, 30vw, 9rem);
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
</style>
