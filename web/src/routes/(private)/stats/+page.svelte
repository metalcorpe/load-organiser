<script lang="ts">
	import BarTable from '#lib/components/BarTable.svelte';
	import PrivacyLabel from '#lib/components/PrivacyLabel.svelte';
	import { count, historyMessage } from '#lib/history.ts';
	import {
		aircraftRows,
		freefallRows,
		monthRows,
		placeRows,
		totalText,
		typeRows,
		yearRows
	} from '#lib/stats.ts';
	import { formatLoading, missingText } from '#lib/wing-loading.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const s = $derived(data.stats);
	const n = (value: number) => value.toLocaleString('en-GB');
	const UNIT_NAME: Record<string, string> = { ft: 'Feet', m: 'Metres' };
</script>

<svelte:head>
	<title>Statistics · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<p><a href="/history">History</a> · <a href="/jumps">Logbook</a></p>
<h1>Statistics</h1>
<PrivacyLabel />
<p class="lede">Counts and measurements from your own entries, private to you.</p>

<!-- novalidate: the server checks the year and explains. -->
<form method="GET" action="/stats" class="year-filter" novalidate>
	<div class="field">
		<label for="year">Year</label>
		<select id="year" name="year">
			<option value="" selected={!data.year}>All years</option>
			{#if s.ok}
				{#if data.year && !s.years.includes(Number(data.year))}
					<option value={data.year} selected>{data.year}</option>
				{/if}
				{#each s.years as year (year)}
					<option value={String(year)} selected={String(year) === data.year}>{year}</option>
				{/each}
			{/if}
		</select>
	</div>
	<button class="button secondary" type="submit">Show</button>
</form>

{#if !s.ok}
	<p class="form-error" role="alert">
		{s.reason === 'year_invalid' ? 'Choose a year from the list.' : historyMessage(s.reason)}
	</p>
{:else if s.total.recorded === 0 && s.years.length === 0}
	<p class="hint">No jumps recorded yet.</p>
	<p><a href="/jumps/new">Add jump</a></p>
{:else}
	<section class="card" aria-labelledby="total-heading">
		<h2 id="total-heading">Jumps</h2>
		<p role="status">{totalText(s)}</p>
		<p class="hint">
			Only this total includes a declared prior jump count; it has no dates, types or places, so
			everything below counts your recorded jumps only.
		</p>
		<BarTable caption="Jumps per year" rowHeader="Year" valueHeader="Jumps" rows={yearRows(s)} />
		<BarTable
			caption={s.year ? `Jumps per month in ${s.year}` : 'Jumps per month, last 24 months'}
			rowHeader="Month"
			valueHeader="Jumps"
			rows={monthRows(s)}
		/>
	</section>

	{#if s.total.recorded === 0}
		<p class="hint">No jumps recorded in {s.year}. <a href="/stats">All years</a></p>
	{:else}
		<section class="card" aria-labelledby="kinds-heading">
			<h2 id="kinds-heading">Types, places and aircraft</h2>
			<BarTable caption="Jumps by type" rowHeader="Type" valueHeader="Jumps" rows={typeRows(s)} />
			<BarTable
				caption={s.by_place.other_places > 0 ? 'Jumps by place, top 10' : 'Jumps by place'}
				rowHeader="Place"
				valueHeader="Jumps"
				rows={placeRows(s)}
			/>
			{#if s.by_aircraft.items.length > 0}
				<BarTable
					caption={s.by_aircraft.other_aircraft > 0 ? 'Jumps by aircraft, top 10' : 'Jumps by aircraft'}
					rowHeader="Aircraft"
					valueHeader="Jumps"
					rows={aircraftRows(s)}
					hint={s.by_aircraft.not_recorded > 0
						? `${count(s.by_aircraft.not_recorded)} without an aircraft recorded.`
						: null}
				/>
			{:else}
				<p class="hint">No aircraft recorded on these jumps.</p>
			{/if}
		</section>

		<section class="card" aria-labelledby="measures-heading">
			<h2 id="measures-heading">Freefall, altitude and wing loading</h2>
			<BarTable
				caption="Freefall time per year"
				rowHeader="Year"
				valueHeader="Freefall"
				extraHeader="Jumps without a freefall time"
				rows={freefallRows(s)}
				hint="Recorded freefall times only; jumps without one add nothing."
			/>

			{#if s.altitudes.length > 0}
				<table class="plain">
					<caption>Exit altitude</caption>
					<thead>
						<tr>
							<th scope="col">Unit</th>
							<th scope="col" class="num">Jumps</th>
							<th scope="col" class="num">Average</th>
							<th scope="col" class="num">Highest</th>
						</tr>
					</thead>
					<tbody>
						{#each s.altitudes as a (a.unit)}
							<tr>
								<th scope="row">{UNIT_NAME[a.unit] ?? a.unit}</th>
								<td class="num">{n(a.jumps)}</td>
								<td class="num">{n(a.average)} {a.unit}</td>
								<td class="num">{n(a.highest)} {a.unit}</td>
							</tr>
						{/each}
					</tbody>
				</table>
				<p class="hint">
					In the unit each altitude was entered in; feet and metres are not mixed or converted.
					{#if s.altitude_not_recorded > 0}{count(s.altitude_not_recorded)} without an exit altitude.{/if}
				</p>
			{:else}
				<p class="hint">No exit altitude recorded on these jumps.</p>
			{/if}

			{#if s.wing_loading.known > 0 && s.wing_loading.lowest !== null && s.wing_loading.highest !== null}
				<p>
					Wing loading from {formatLoading(s.wing_loading.lowest)} to {formatLoading(
						s.wing_loading.highest
					)} over {count(s.wing_loading.known)}.
					{#if s.wing_loading.unknown > 0}
						<span class="hint"
							>{count(s.wing_loading.unknown)} without one: {missingText(
								s.wing_loading.missing.map((m) => m.missing)
							)}.</span
						>
					{/if}
				</p>
			{:else}
				<p class="hint">
					No wing loading on these jumps: it needs your exit weight (on your
					<a href="/profile#weight-heading">profile</a>) and a main canopy with its size recorded on the
					jump.
				</p>
			{/if}
		</section>
	{/if}
{/if}

<style>
	.year-filter {
		display: flex;
		flex-wrap: wrap;
		align-items: flex-end;
		gap: 0.75rem;
		margin: 0 0 1rem;
	}

	.year-filter .field {
		margin: 0;
	}

	.plain {
		border-collapse: collapse;
		margin-block: 0.5rem;
	}

	.plain caption {
		text-align: start;
		font-weight: 600;
		padding-block-end: 0.25rem;
	}

	.plain th,
	.plain td {
		padding: 0.25rem 1rem 0.25rem 0;
		text-align: start;
		border-block-end: 1px solid var(--border);
	}

	.plain .num {
		text-align: end;
		font-variant-numeric: tabular-nums;
	}
</style>
