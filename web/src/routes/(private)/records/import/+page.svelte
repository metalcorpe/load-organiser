<script lang="ts">
	import PrivacyLabel from '#lib/components/PrivacyLabel.svelte';
	import Notice from '#lib/components/Notice.svelte';
	import { COUNTRY_OPTIONS, countryName } from '#lib/countries.ts';
	import {
		DATE_ORDER_LABEL,
		FIELD_LABEL,
		IMPORT_FIELDS,
		PLACE_KIND_LABEL,
		describeImport,
		describeUndo,
		importMessage,
		rowProblem
	} from '#lib/imports.ts';
	import { JUMP_TYPE_LABEL } from '#lib/jumps.ts';
	import { formatDay } from '#lib/listings.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();

	const errorFor = (name: string, id?: string) =>
		form && form.form === name && 'error' in form && (!id || ('id' in form && form.id === id))
			? importMessage(form.error)
			: undefined;
	const names = $derived<string[]>(
		form && 'names' in form && Array.isArray(form.names) ? form.names : []
	);
	const choices = $derived(
		form && 'choices' in form && form.choices
			? form.choices
			: { date_order: 'dmy', unit: 'ft', country: '' }
	);
	const check = $derived(form && form.form === 'check' && 'check' in form ? form.check : null);
	const result = $derived(form && form.form === 'import' && 'result' in form ? form.result : null);
	const undone = $derived(form && form.form === 'undo' && 'undone' in form ? form.undone : null);
	const day = (instant: string) => formatDay(instant.slice(0, 10));
	const n = (value: number) => value.toLocaleString('en-GB');
	const jumps = (value: number) => `${n(value)} ${value === 1 ? 'jump' : 'jumps'}`;
	const blocked = $derived(
		!check || check.rows_ok === 0 || check.rows_ok > check.room || !data.emailVerified
	);
</script>

<svelte:head>
	<title>Import from a spreadsheet · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<p><a href="/records">Records</a></p>
<h1>Import from a spreadsheet</h1>
<PrivacyLabel />
<p class="lede">
	Bring the jumps you already logged into your private logbook from a CSV file, instead of typing
	them again.
</p>

{#if result}
	<Notice
		title={result.outcome === 'imported' ? 'Imported' : 'Already imported'}
		tone="ok"
	>
		<p role="status">
			{#if result.outcome === 'imported'}
				Imported {describeImport(result.item.counts)}.
			{:else}
				This exact file was already imported on {day(result.item.created_at)} with these choices
				({describeImport(result.item.counts)}). Nothing was changed.
			{/if}
		</p>
		<p>Imported jumps show as imported by you, not verified.</p>
		<p><a href="/jumps">Open your logbook</a></p>
	</Notice>
{/if}

<section class="card" aria-labelledby="file-heading">
	<h2 id="file-heading">1. Choose your file</h2>
	<p>
		Save your spreadsheet as CSV (comma, semicolon or tab separated) with the column headings in the
		first row. Up to 2,000 rows and 1 MB.
	</p>
	<p class="hint">
		A date and a dropzone or place are needed on every row. Jump number, type, exit altitude,
		freefall seconds and notes are read when present. Nothing is saved until you import.
	</p>
	<form method="POST" action="?/check" class="form" enctype="multipart/form-data" novalidate>
		{#if errorFor('check')}
			<p class="form-error" role="alert">{errorFor('check')}</p>
			{#if names.length > 0}
				<p class="hint">Not in the directory: {names.join('; ')}.</p>
			{/if}
		{/if}
		<div class="field">
			<label for="check_file">Spreadsheet file (CSV)</label>
			<input id="check_file" name="file" type="file" accept=".csv,text/csv" />
		</div>
		<div class="field">
			<label for="check_date_order">Dates are written as</label>
			<select id="check_date_order" name="date_order">
				{#each Object.entries(DATE_ORDER_LABEL) as [value, label] (value)}
					<option {value} selected={choices.date_order === value}>{label}</option>
				{/each}
			</select>
			<p class="hint">Dates written as 2024-12-31 are always read correctly.</p>
		</div>
		<fieldset>
			<legend>Altitudes are in</legend>
			<label class="choice"
				><input type="radio" name="unit" value="ft" checked={choices.unit !== 'm'} /> Feet</label
			>
			<label class="choice"
				><input type="radio" name="unit" value="m" checked={choices.unit === 'm'} /> Metres</label
			>
		</fieldset>
		<div class="field">
			<label for="check_country">Country for places not in the directory</label>
			<select id="check_country" name="country">
				<option value="">Choose a country</option>
				{#each COUNTRY_OPTIONS as option (option.code)}
					<option value={option.code} selected={choices.country === option.code}>{option.name}</option>
				{/each}
			</select>
			<p class="hint">
				A place that matches a listed dropzone or one of your private places is used as it is.
				Any other place becomes a new private place in this country, seen only by you.
			</p>
		</div>
		<div class="form-actions">
			<button class="button secondary" type="submit">Check file</button>
		</div>
	</form>
</section>

{#if check || (form && form.form === 'import' && 'error' in form)}
	<section class="card" aria-labelledby="preview-heading">
		<h2 id="preview-heading">2. Check what will be saved</h2>
		{#if check}
			<Notice
				title={check.rows_ok === 0
					? 'Nothing to import'
					: check.rows_ok > check.room
						? 'Too many jumps for your logbook'
						: 'Ready to import'}
				tone={check.rows_ok === 0 || check.rows_ok > check.room ? 'warn' : 'ok'}
			>
				<p role="status">
					{n(check.rows_total)}
					{check.rows_total === 1 ? 'row' : 'rows'} read: {jumps(check.rows_ok)} to import,
					{n(check.problems_total)} skipped.
				</p>
				{#if check.rows_ok > check.room}
					<p>
						Your logbook has room for {jumps(check.room)} more (the limit is 2,000). Remove rows from
						the file, or jumps from your logbook, then check again.
					</p>
				{/if}
				{#if check.already_imported_at}
					<p>
						This exact file was already imported on {day(check.already_imported_at)} with these
						choices. Importing it again changes nothing.
					</p>
				{/if}
				{#if check.encoding === 'windows-1252'}
					<p>
						The file was read as Windows-1252 text. If accented letters look wrong below, save it as
						CSV UTF-8 and check again.
					</p>
				{/if}
			</Notice>

			{#if check.new_places.length > 0}
				<h3>New private places ({n(check.new_places.length)})</h3>
				<p class="hint">
					Created in {countryName(choices.country)} and seen only by you. You can rename them or
					link them to a listed dropzone later under Private places.
				</p>
				<ul class="places">
					{#each check.new_places as name, i (i)}<li>{name}</li>{/each}
				</ul>
			{/if}

			{#if check.sample.length > 0}
				<h3>First rows as they will be saved</h3>
				<ul class="results rows" aria-label="First rows to import">
					{#each check.sample as row (row.row)}
						<li>
							<span class="title"
								>Row {row.row}: {formatDay(row.jumped_on)}{row.jump_number
									? ` · #${row.jump_number}`
									: ''}</span
							>
							<span class="meta"
								>{JUMP_TYPE_LABEL[row.jump_type]} · {row.place} ({PLACE_KIND_LABEL[row.place_kind]})</span
							>
							{#if row.exit_altitude !== null || row.freefall_seconds !== null}
								<span class="meta"
									>{row.exit_altitude !== null
										? `Exit ${n(row.exit_altitude)} ${row.altitude_unit}`
										: ''}{row.exit_altitude !== null && row.freefall_seconds !== null
										? ' · '
										: ''}{row.freefall_seconds !== null
										? `freefall ${row.freefall_seconds} s`
										: ''}</span
								>
							{/if}
							{#if row.notes}<span class="meta notes">{row.notes}</span>{/if}
						</li>
					{/each}
				</ul>
			{/if}

			{#if check.problems_total > 0}
				<h3>Skipped rows ({n(check.problems_total)})</h3>
				<p class="hint">Row 1 is the first row under the headings.</p>
				<ul class="problems" aria-label="Skipped rows">
					{#each check.problems as problem (problem.row)}
						<li>Row {problem.row}: {rowProblem(problem.code)}.</li>
					{/each}
				</ul>
				{#if check.problems_total > check.problems.length}
					<p class="hint">
						And {n(check.problems_total - check.problems.length)} more. Fix them in the file and check
						again, or import without them.
					</p>
				{/if}
			{/if}
		{/if}

		<form method="POST" action="?/import" class="form" enctype="multipart/form-data" novalidate>
			{#if errorFor('import')}
				<p class="form-error" role="alert">{errorFor('import')}</p>
				{#if names.length > 0}
					<p class="hint">Not in the directory: {names.join('; ')}.</p>
				{/if}
			{/if}
			{#if !data.emailVerified}
				<p class="hint">Confirm your email address on your <a href="/profile">profile</a> to import.</p>
			{/if}
			<input type="hidden" name="date_order" value={choices.date_order} />
			<input type="hidden" name="unit" value={choices.unit} />
			<input type="hidden" name="country" value={choices.country} />
			{#if check}
				<input type="hidden" name="expected" value={check.fingerprint} />
				<fieldset>
					<legend>Columns</legend>
					<p class="hint">
						Found from the headings. Change one and check again to see the result.
					</p>
					{#each IMPORT_FIELDS as name (name)}
						<div class="field">
							<label for="col_{name}">{FIELD_LABEL[name]}</label>
							<select id="col_{name}" name="col_{name}">
								<option value="none" selected={check.columns[name] === null}>Not in this file</option>
								{#each check.headings as heading, i (i)}
									<option value={String(i)} selected={check.columns[name] === i}
										>{i + 1}. {heading || '(no heading)'}</option
									>
								{/each}
							</select>
						</div>
					{/each}
				</fieldset>
			{/if}
			<div class="field">
				<label for="import_file">Choose the same file again</label>
				<input id="import_file" name="file" type="file" accept=".csv,text/csv" />
				<p class="hint">The file is not kept between steps, so it is sent again with each button.</p>
			</div>
			<div class="form-actions">
				<button class="button secondary" type="submit" formaction="?/check">Check again</button>
				{#if check}
					<button class="button" type="submit" disabled={blocked}>Import {jumps(check.rows_ok)}</button>
				{/if}
			</div>
		</form>
	</section>
{/if}

<section class="card" aria-labelledby="past-heading">
	<h2 id="past-heading">Your imports</h2>
	{#if undone}
		<Notice title="Import undone" tone="ok">
			<p role="status">{describeUndo(undone.counts)}.</p>
		</Notice>
	{/if}
	{#if !data.imports.ok}
		<p class="form-error" role="alert">{importMessage(data.imports.reason)}</p>
	{:else if data.imports.items.length === 0}
		<p class="hint">No imports yet.</p>
	{:else}
		<ul class="results rows" aria-label="Your imports">
			{#each data.imports.items as item (item.id)}
				<li>
					<span class="title">Imported on {day(item.created_at)}</span>
					<span class="meta">{describeImport(item.counts)}</span>
					{#if item.undone_at}
						<span class="meta">Undone on {day(item.undone_at)}. {describeUndo(item.counts)}.</span>
					{:else}
						<form method="POST" action="?/undo" class="form undo">
							{#if errorFor('undo', item.id)}
								<p class="form-error" role="alert">{errorFor('undo', item.id)}</p>
							{/if}
							<input type="hidden" name="id" value={item.id} />
							<label class="choice"
								><input type="checkbox" name="confirm" /> Delete the jumps from this import</label
							>
							<p class="hint">
								Every jump this import added is deleted, even if you edited it since, with the new
								private places nothing else uses. This cannot be reversed.
							</p>
							<div class="form-actions">
								<button class="button secondary" type="submit" disabled={!data.emailVerified}
									>Undo this import</button
								>
							</div>
						</form>
					{/if}
				</li>
			{/each}
		</ul>
	{/if}
</section>

<style>
	h3 {
		font-size: 1.05rem;
		margin: 1rem 0 0.35rem;
	}

	.places,
	.problems {
		margin: 0.25rem 0 0.75rem;
		padding-left: 1.25rem;
	}

	.notes {
		overflow-wrap: anywhere;
	}

	.undo {
		margin: 0.5rem 0 0;
		gap: 0.5rem;
	}
</style>
