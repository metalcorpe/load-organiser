<script lang="ts">
	import PrivacyLabel from '#lib/components/PrivacyLabel.svelte';
	import RecordTiles from '#lib/components/RecordTiles.svelte';
	import { formatDay } from '#lib/listings.ts';
	import { spreadsheetMessage } from '#lib/records.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const s = $derived(data.summary);
	const n = (value: number) => value.toLocaleString('en-GB');
	const jumps = (value: number) => `${n(value)} ${value === 1 ? 'jump' : 'jumps'}`;
	const sheetError = $derived(spreadsheetMessage(data.sheet.error));

</script>

<svelte:head>
	<title>Records · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<h1>Records</h1>
<PrivacyLabel />
<p class="lede">Private to you.</p>

{#if s}
	<section class="summary" aria-label="Summary">
		{#if s.recorded === 0 && !s.prior}
			<p><a href="/jumps/new">Log your first jump</a>. Only the date, place and type are needed.</p>
		{:else}
			<p class="total">
				{#if s.lifetime !== null}
					<strong>{jumps(s.lifetime)}</strong>
					<span class="hint">({n(s.prior ?? 0)} declared + {n(s.since ?? 0)} recorded)</span>
				{:else}
					<strong>{jumps(s.recorded)}</strong> recorded
				{/if}
			</p>
			{#if s.lastJumpOn}<p class="hint">Last jump {formatDay(s.lastJumpOn)}</p>{/if}
		{/if}
	</section>
{/if}

<RecordTiles />

<section class="sheet" aria-labelledby="sheet-heading">
	<h2 id="sheet-heading">Download as spreadsheet (CSV)</h2>
	<p>Your jumps in one file for Excel, Numbers or Google Sheets.</p>
	<p class="hint">
		Not a full copy: exit time, time zone and the links on your jumps are left out, and gear is
		plain text. For everything, use <a href="/profile/data">Export</a>.
	</p>
	<details class="included">
		<summary>What's included?</summary>
		<div class="included-body">
			<p>
				Date, jump number, place, country, type, aircraft, altitudes and unit, freefall seconds,
				notes and gear used.
			</p>
			<p>
				The columns are the ones the spreadsheet import reads, so the file can be imported into
				another account. On the way back:
			</p>
			<ul>
				<li>gear used comes back as text, not as links to your gear, cut to 200 characters;</li>
				<li>a jump number used twice comes back only once (the import skips the repeat).</li>
			</ul>
			<p>If a download fails, you can try again straight away.</p>
		</div>
	</details>
	{#if sheetError}<p class="form-error" role="alert" id="sheet-error">{sheetError}</p>{/if}
	<!-- novalidate: the server checks the dates and explains. -->
	<form method="POST" action="/records/spreadsheet" class="form sheet-form" novalidate>
		<div class="field">
			<label for="sheet-from">From (optional)</label>
			<input
				id="sheet-from"
				name="from"
				type="date"
				defaultValue={data.sheet.from}
				aria-describedby={sheetError ? 'sheet-error' : undefined}
			/>
		</div>
		<div class="field">
			<label for="sheet-until">Until (optional)</label>
			<input
				id="sheet-until"
				name="until"
				type="date"
				defaultValue={data.sheet.until}
				aria-describedby={sheetError ? 'sheet-error' : undefined}
			/>
		</div>
		<div class="form-actions">
			<button class="button secondary" type="submit">Download as spreadsheet (CSV)</button>
		</div>
	</form>
	<p class="hint">Leave the dates empty for every jump. One download every five minutes.</p>
</section>

<style>
	.summary {
		margin: 0.5rem 0 1.25rem;
		padding: 0.85rem 1rem;
		border-radius: var(--radius);
		background: var(--accent-soft);
	}

	.summary p {
		margin: 0;
	}

	.total strong {
		font-size: 1.35rem;
	}

	.sheet {
		margin: 1.5rem 0 0;
		padding: 0.85rem 1rem;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		background: var(--surface);
	}

	.sheet h2 {
		font-size: 1rem;
		margin: 0 0 0.5rem;
	}

	.sheet p {
		margin: 0 0 0.5rem;
	}

	.included {
		margin: 0 0 0.5rem;
	}

	.included-body {
		font-size: 0.95rem;
	}

	.included-body ul {
		margin: 0 0 0.5rem;
		padding-left: 1.25rem;
	}

	.sheet-form {
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 11rem), 1fr));
		align-items: end;
	}

	.sheet-form .form-actions {
		grid-column: 1 / -1;
	}

</style>
