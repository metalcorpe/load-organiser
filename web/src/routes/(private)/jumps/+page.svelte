<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import CurrencyStatus from '#lib/components/CurrencyStatus.svelte';
	import DueList from '#lib/components/DueList.svelte';
	import Notice from '#lib/components/Notice.svelte';
	import PrivacyLabel from '#lib/components/PrivacyLabel.svelte';
	import { localToday } from '#lib/currency.ts';
	import { fieldsFor } from '#lib/field-errors.ts';
	import { dueSoon } from '#lib/gear.ts';
	import { KIND_LABEL } from '#lib/gear.ts';
	import { appliedText, batchHeading, batchMessage, undoneText } from '#lib/jump-batch.ts';
	import { freefallText, jumpsHref } from '#lib/jump-filters.ts';
	import { JUMP_TYPE_LABEL, jumpMessage, loadFailure } from '#lib/jumps.ts';
	import { formatDay, formatRange, statusLabel } from '#lib/listings.ts';
	import { formatLoading, listNote, missingHelp } from '#lib/wing-loading.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();
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
	// The server's UTC day until the browser gives the jumper's own calendar day.
	// svelte-ignore state_referenced_locally
	let today = $state(data.today);
	onMount(() => {
		today = localToday();
	});
	const due = $derived(dueSoon(data.due, today));
	// "Select" mode keeps the filters; leaving it keeps them too.
	const selectHref = (cursor?: string) => {
		const href = jumpsHref(data.filters, cursor);
		return `${href}${href.includes('?') ? '&' : '?'}select=1`;
	};
	const actionQuery = $derived(selectHref().replace(/^\/jumps\?/, ''));
	const batchForm = $derived(form && form.form === 'batch' ? form : null);
	const preview = $derived(batchForm && 'preview' in batchForm ? batchForm.preview : null);
	const choice = $derived(batchForm?.choice ?? null);
	const picked = $derived(new Set(batchForm?.ids ?? []));
	const pickedGear = $derived(new Set(choice?.component_ids ?? []));
	const batchError = $derived(
		form && 'error' in form && (form.form === 'batch' || form.form === 'apply' || form.form === 'undo')
			? batchMessage(form.error)
			: undefined
	);
	const changing = $derived(preview ? preview.items.filter((i) => i.will_change) : []);
	const heading = $derived(
		preview && choice
			? batchHeading(preview.changing, {
					jumpType: choice.jump_type || undefined,
					place: choice.at
						? (preview.location?.name ?? 'the chosen place') +
							(preview.location?.kind === 'place' ? ' (private place)' : '')
						: undefined,
					aircraft: choice.set_aircraft ? choice.aircraft || null : undefined,
					gear: choice.set_gear ? (preview.components ?? []).map((c) => c.label) : undefined
				})
			: ''
	);
	const params = $derived(page.url.searchParams);
	const count = (name: string) => Number(params.get(name) ?? '0') || 0;
	const applied = $derived(
		params.has('changed') ? appliedText(count('changed'), count('skipped'), count('unchanged')) : null
	);
	const undone = $derived(
		params.has('restored') ? undoneText(count('restored'), count('not_restored')) : null
	);
	const undoUntil = (instant: string) =>
		new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium', timeStyle: 'short' }).format(
			new Date(instant)
		);
	// Wing loading shows on the rows that have one; what the others lack is said once.
	const loadingNote = $derived(data.page.ok ? listNote(data.page.items) : null);
	const loadingHelp = $derived(missingHelp(loadingNote?.missing ?? []));
	// No entry at all (whatever the filters): the page leads with logging and importing, and
	// leaves out search, filters and the currency box until there is something to show.
	const firstUse = $derived(
		data.page.ok && data.page.recorded_total === 0 && !data.filtered && !data.older && !data.select
	);
	// Currency, gear and plans: on the plain logbook (any page) beside the jumps. A phone shows
	// them on the first page only, and a filtered one only the count of matches.
	// Nothing beside a failed or stale load.
	const home = $derived(data.page.ok && !data.filtered && !data.select);
	const matchedSide = $derived(
		data.page.ok && data.filtered && matched !== null && matched.jumps > 0
	);
	// Without anything for the side column (selecting jumps, no matches, a failed load), there
	// are no columns: the main column alone, as wide as it is beside the side column.
	const hasSide = $derived(home || matchedSide);
	const sideOnPhones = $derived(matchedSide || (home && !data.older));
	const declared = $derived(
		data.summary?.priorJumps ? { count: data.summary.priorJumps, before: data.summary.priorBefore } : null
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
	<p class="links"><a href="/history">History</a> · <a href="/stats">Statistics</a></p>
</div>
<PrivacyLabel text="Private logbook — only you can see your jumps" />

<!-- Large screens: the jumps (or the way to start) in the main column; currency, gear due
     soon and what is coming up beside them. One column on a phone, in this order. -->
<div class={hasSide ? 'columns' : 'solo'}>
<div class="col-main">
{#if filterError}
	<p class="form-error" role="alert" id="filter-error">{jumpMessage(filterError)}</p>
{/if}
{#if applied}<p class="ok" role="status">{applied}</p>{/if}
{#if undone}<p class="ok" role="status">{undone}</p>{/if}
{#if data.latestBatch}
	<section class="undo" aria-labelledby="undo-heading">
		<h2 id="undo-heading">Your last change of many jumps</h2>
		<p>
			It changed {data.latestBatch.changed}
			{data.latestBatch.changed === 1 ? 'jump' : 'jumps'}. You can undo it until
			{undoUntil(data.latestBatch.undo_until)}, or until your next change of many jumps. Jumps you
			edited since are left as they are.
		</p>
		{#if form && form.form === 'undo' && batchError}<p class="form-error" role="alert">{batchError}</p>{/if}
		<form method="POST" action="?/undo">
			<input type="hidden" name="batch_id" value={data.latestBatch.batch_id} />
			<button class="button secondary" type="submit">Undo this change</button>
		</form>
	</section>
{/if}
<!-- defaultValue keeps text typed before hydration; the key resets the fields when
     the URL's filters change (Clear filters, back/forward). -->
{#if !firstUse}
{#key page.url.search}
	<!-- novalidate: the server checks the dates and explains; WebKit otherwise blocks the
     submit silently on a date field it considers half-filled. -->
<form method="GET" action="/jumps" class="jump-search" role="search" novalidate>
		<div class="search-row">
			<label class="visually-hidden" for="q">Place, aircraft or notes</label>
			<input
				id="q"
				name="q"
				type="search"
				maxlength="100"
				placeholder="Search places, aircraft and notes"
				defaultValue={f.q}
				autocomplete="off"
			/>
			<button class="button secondary" type="submit">Search</button>
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
{/if}

{#if !data.page.ok}
	{#if !filterError && loadFailure(data.page.reason) === 'retry'}
		<!-- A failed load is not an empty logbook: the error tone, and the same page again. -->
		<Notice title="Your jumps could not be loaded" tone="bad">
			<p role="alert">
				{data.page.reason === 'uncertain'
					? 'The service did not answer in time.'
					: 'The service is unavailable right now.'} Nothing in your logbook was changed.
			</p>
			<p>
				<a class="button secondary" href={page.url.pathname + page.url.search} data-sveltekit-reload
					>Try again</a
				>
			</p>
		</Notice>
	{:else if !filterError && loadFailure(data.page.reason) === 'stale'}
		<!-- An old or altered page link: trying it again would not help. -->
		<Notice title="This page of your logbook could not be shown" tone="warn">
			<p role="alert">The link to this page is out of date. Your logbook itself is unchanged.</p>
			<p>
				<a href={jumpsHref(data.filters)}
					>{data.filtered ? 'Go to the first page of this search' : 'Go to your newest jumps'}</a
				>
			</p>
		</Notice>
	{:else if !filterError}
		<!-- Any other refusal keeps its own wording (session ended, not allowed, bad input). -->
		<p class="form-error" role="alert">{jumpMessage(data.page.reason)}</p>
	{/if}
{:else if firstUse}
	<!-- First use: the shared empty state, with the two ways to start. -->
	<section class="empty-state" aria-labelledby="first-use-heading">
		<h2 id="first-use-heading">Start your logbook</h2>
		{#if declared}
			<p>
				You declared {n(declared.count)} prior {declared.count === 1 ? 'jump' : 'jumps'}{declared.before
					? ` before ${formatDay(declared.before)}`
					: ''}; they count in your total. No jumps are logged here yet: add them one by one or
				from a spreadsheet.
			</p>
		{:else}
			<p>No jumps yet. Log one with only the date, place and type, or bring in the logbook you already keep.</p>
		{/if}
		<p class="actions">
			<a class="button" href="/jumps/new">Log your first jump</a>
			<a class="button secondary" href="/records/import">Import existing logbook</a>
		</p>
		<p class="hint">Import reads a spreadsheet (CSV) and checks it before anything is saved.</p>
	</section>
{:else if !data.older && !data.filtered && !data.select}
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
</div>

{#if hasSide}
<div class="col-side" class:wide-only={!sideOnPhones}>
	<!-- The count and span of the matches; with none, the quiet empty state says it. -->
	{#if matchedSide && matched && data.page.ok}
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
	{#if home}
		{#if data.summary?.currency && !firstUse}<CurrencyStatus
				currency={data.summary.currency}
				today={data.today}
				progress={data.summary.progress}
			/>{/if}
		<!-- Gear and plans, each its own section, soonest first. With nothing in one, a phone shows
		     nothing; beside the jumps a line says what would appear there. -->
		{#if due.length > 0}
			<section class="ahead" aria-labelledby="due-heading">
				<h2 id="due-heading">Due soon</h2>
				<DueList items={due} {today} label="Due soon" />
				<p class="more-link"><a href="/gear">All gear dates</a></p>
			</section>
		{:else}
			<section class="ahead quiet wide-only" aria-labelledby="due-heading">
				<h2 id="due-heading">Gear due soon</h2>
				<p>Reserve repacks and other service dates show here as they come due.</p>
				<p class="more-link"><a href="/gear">Your gear</a></p>
			</section>
		{/if}
		{#if data.coming.length > 0}
			<section class="ahead" aria-labelledby="coming-heading">
				<h2 id="coming-heading">Coming up</h2>
				<ol class="coming" aria-label="Coming up">
					{#each data.coming as item (item.kind + item.id)}
						{@const state = item.status ? statusLabel(item.status, false) : null}
						<li>
							<a href={item.kind === 'plan' ? `/plans#plan-${item.id}` : `/events/${item.id}`}
								>{item.title}</a
							>
							<span class="meta"
								>{item.kind === 'plan' ? 'Your plan' : 'Saved listing'} · {formatRange(
									item.starts_on,
									item.ends_on
								)}{item.place ? ` · ${item.place}` : ''}</span
							>
							{#if state}
								<span class="tag"
									>{item.kind === 'plan' ? `Listing ${state.toLowerCase()}` : state}</span
								>
							{/if}
						</li>
					{/each}
				</ol>
				<p class="more-link"><a href="/saved">See all saved</a> · <a href="/plans">See all plans</a></p>
			</section>
		{:else}
			<section class="ahead quiet wide-only" aria-labelledby="coming-heading">
				<h2 id="coming-heading">Coming up</h2>
				<p>Events you save and the visits you plan show here, soonest first.</p>
				<p class="more-link"><a href="/">Browse events</a> · <a href="/plans">Plan a visit</a></p>
			</section>
		{/if}
	{/if}
</div>
{/if}

<div class="col-main-end">
{#if data.page.ok}
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
		<!-- A result, not a page: the quiet empty state, with the way out. -->
		<section class="empty-state quiet" aria-labelledby="empty-heading">
			<h2 id="empty-heading">{data.older ? 'No more matching jumps' : 'No jumps match'}</h2>
			<p>
				{data.older
					? 'The earlier pages hold every jump that matches these filters.'
					: 'No jumps match these filters. Change them, or clear them to see your whole logbook.'}
			</p>
			<p class="actions">
				{#if data.older}<a class="button secondary" href={jumpsHref(data.filters)}
						>Back to the first matching page</a
					>{/if}
				<a class="button secondary" href="/jumps">Clear filters</a>
			</p>
		</section>
	{:else if data.page.items.length === 0 && data.older}
		<section class="empty-state quiet" aria-labelledby="empty-heading">
			<h2 id="empty-heading">No older jumps</h2>
			<p>You have reached the end of your logbook.</p>
			<p class="actions"><a class="button secondary" href="/jumps">Back to your newest jumps</a></p>
		</section>
	{:else if data.page.items.length === 0}
		<!-- An empty first page with entries elsewhere (rare: changed meanwhile); firstUse covers none. -->
		{#if !firstUse}<p class="hint">No jumps on this page. <a href="/jumps">Reload your logbook</a></p>{/if}
	{:else if data.select}
		<section class="batch" aria-labelledby="batch-heading">
			<h2 id="batch-heading">Change many jumps</h2>
			<p class="hint">
				Tick the jumps on this page, or filter the logbook and choose all matching jumps (up to
				200). Then choose what they all get. You see the change before anything is saved.
			</p>
			{#if batchError && form?.form !== 'undo'}<p class="form-error" role="alert">{batchError}</p>{/if}
			{#if preview && choice}
				<section class="confirm" aria-labelledby="confirm-heading">
					<h3 id="confirm-heading">{heading}</h3>
					{#if changing.length > 0}
						<ul class="affected" aria-label="Jumps to change">
							{#each changing as item (item.id)}
								<li>
									{formatDay(item.jumped_on)}{item.jump_number ? ` · #${item.jump_number}` : ''} ·
									{JUMP_TYPE_LABEL[item.jump_type]} · {item.location.name ?? 'Dropzone no longer listed'}{item.aircraft
										? ` · ${item.aircraft}`
										: ''}
								</li>
							{/each}
						</ul>
					{/if}
					{#if preview.items.length > changing.length}
						<p class="hint">
							{preview.items.length - changing.length} of the chosen jumps already have these values.
						</p>
					{/if}
					{#if preview.missing > 0}
						<p class="hint">{preview.missing} of the chosen jumps are no longer in your logbook.</p>
					{/if}
					{#if changing.length > 0}
						<form method="POST" action="?{actionQuery}&/apply" class="form">
							{#each changing as item (item.id)}
								<input type="hidden" name="jump" value="{item.id}:{item.version}" />
							{/each}
							{#if choice.jump_type}<input type="hidden" name="jump_type" value={choice.jump_type} />{/if}
							{#if choice.at}<input type="hidden" name="at" value={choice.at} />{/if}
							{#if choice.set_aircraft}
								<input type="hidden" name="set_aircraft" value="1" />
								<input type="hidden" name="aircraft" value={choice.aircraft} />
							{/if}
							{#if choice.set_gear}
								<input type="hidden" name="set_gear" value="1" />
								{#each choice.component_ids as id (id)}<input type="hidden" name="component_ids" value={id} />{/each}
							{/if}
							<p class="hint">
								Each change is kept in that jump's private history. A jump edited after this check is
								left as it is.
							</p>
							<div class="form-actions">
								<button class="button" type="submit"
									>Change {changing.length} {changing.length === 1 ? 'jump' : 'jumps'}</button
								>
								<a href={selectHref()}>Choose again</a>
							</div>
						</form>
					{:else}
						<p>Nothing to change. <a href={selectHref()}>Choose again</a></p>
					{/if}
				</section>
			{/if}
			<form method="POST" action="?{actionQuery}&/preview" class="form batch-form">
				{#if data.filtered && matched && matched.jumps > 0}
					<label class="choice all"
						><input type="checkbox" name="all" value="1" defaultChecked={batchForm?.all ?? false} />
						All {n(matched.jumps)} matching {matched.jumps === 1 ? 'jump' : 'jumps'}{matched.jumps > 200
							? ' (more than 200: filter further)'
							: ''}</label
					>
				{/if}
				<fieldset class="pick-list">
					<legend>Jumps on this page</legend>
					<ul class="jumps" aria-label="Jumps">
						{#each data.page.items as jump (jump.id)}
							<li class="pick">
								<input
									type="checkbox"
									id="pick-{jump.id}"
									name="id"
									value={jump.id}
									defaultChecked={picked.has(jump.id)}
								/>
								<label class="text" for="pick-{jump.id}">
									<span class="title-text"
										>{formatDay(jump.jumped_on)}{jump.jump_number ? ` · #${jump.jump_number}` : ''}</span
									>
									<span class="meta"
										>{JUMP_TYPE_LABEL[jump.jump_type]} · {jump.location.name ??
											'Dropzone no longer listed'}{jump.location.kind === 'place'
											? ' (private place)'
											: ''}{jump.aircraft ? ` · ${jump.aircraft}` : ''}</span
									>
								</label>
							</li>
						{/each}
					</ul>
				</fieldset>
				<fieldset class="changes">
					<legend>What they all get</legend>
					<div class="field">
						<label for="batch_type">Type</label>
						<select id="batch_type" name="jump_type">
							<option value="" selected={!choice?.jump_type}>Keep each jump's type</option>
							{#each Object.entries(JUMP_TYPE_LABEL) as [value, label] (value)}
								<option {value} selected={choice?.jump_type === value}>{label}</option>
							{/each}
						</select>
					</div>
					<div class="field">
						<label for="batch_at">Place</label>
						<select id="batch_at" name="at">
							<option value="" selected={!choice?.at}>Keep each jump's place</option>
							{#each data.placeOptions as option (option.value)}
								<option value={option.value} selected={choice?.at === option.value}>{option.label}</option>
							{/each}
						</select>
					</div>
					<div class="field">
						<label class="choice"
							><input
								type="checkbox"
								name="set_aircraft"
								value="1"
								defaultChecked={choice?.set_aircraft ?? false}
							/> Change the aircraft</label
						>
						<label for="batch_aircraft">Aircraft (leave empty to clear it)</label>
						<input
							id="batch_aircraft"
							name="aircraft"
							maxlength="60"
							autocomplete="off"
							defaultValue={choice?.aircraft ?? ''}
						/>
					</div>
					<fieldset class="field">
						<legend>Gear used</legend>
						<label class="choice"
							><input type="checkbox" name="set_gear" value="1" defaultChecked={choice?.set_gear ?? false} />
							Replace the gear used with the items ticked here (none ticked: no gear)</label
						>
						{#each data.gear as item (item.id)}
							<label class="choice"
								><input
									type="checkbox"
									name="component_ids"
									value={item.id}
									defaultChecked={pickedGear.has(item.id)}
								/>
								{item.label} <span class="meta">({KIND_LABEL[item.kind] ?? item.kind})</span></label
							>
						{/each}
						{#if !data.gearOk}<p class="hint">Your gear could not be loaded right now.</p>{/if}
					</fieldset>
				</fieldset>
				<div class="form-actions">
					<button class="button" type="submit">Check the change</button>
					<a href={jumpsHref(data.filters)}>Cancel</a>
				</div>
			</form>
		</section>
	{:else}
		<div class="list-head">
			<h2>{data.filtered ? 'Matching jumps' : data.older ? 'Older jumps' : 'Recent jumps'}</h2>
			<a href={selectHref()}>Select jumps to change</a>
		</div>
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
								: ''}{jump.aircraft ? ` · ${jump.aircraft}` : ''}{jump.wing_loading.value !== null
								? ` · wing loading ${formatLoading(jump.wing_loading.value)}`
								: ''}</span
						>
						{#if jump.components.length > 0}
							<span class="meta">Gear: {jump.components.map((c) => c.label).join(', ')}</span>
						{/if}
					</span>
				</li>
			{/each}
		</ul>
		{#if loadingNote}
			<p class="hint">
				No wing loading for {loadingNote.count}
				{loadingNote.count === 1 ? 'jump' : 'jumps'} here: {loadingNote.text}.
				{#if loadingHelp.profile}<a href="/profile#weight-heading">Set your exit weight</a>{/if}{#if loadingHelp.profile && loadingHelp.gear}
					·
				{/if}{#if loadingHelp.gear}<a href="/gear">Add canopy sizes under Gear</a>{/if}
			</p>
		{/if}
	{/if}
	<p class="pager">
		{#if data.older}<a href={data.select ? selectHref() : jumpsHref(data.filters)}>Newest</a>{/if}
		{#if data.page.next_cursor}
			<a
				href={data.select
					? selectHref(data.page.next_cursor)
					: jumpsHref(data.filters, data.page.next_cursor)}
				rel="next">Older jumps</a
			>
		{/if}
	</p>
{/if}
</div>
</div>

<style>
	/* With very large text the links move under the heading; "Logbook" never breaks inside
	   the word (the page's overflow-wrap: anywhere would let the flex row squeeze it). */
	.head {
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		align-items: baseline;
		column-gap: 1rem;
	}

	.head h1 {
		overflow-wrap: break-word;
	}

	.head .links {
		margin: 0;
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

	/* With large text the dates move under the total; no number or word breaks in two. */
	.totals {
		flex-wrap: wrap;
	}

	.totals p,
	.totals span {
		overflow-wrap: break-word;
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

	.list-head h2 {
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
		/* The number tile grows with large text instead of breaking "214" in two. */
		grid-template-columns: minmax(3rem, max-content) minmax(0, 1fr);
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
		min-height: 2.8rem;
		padding: 0 0.35rem;
		border-radius: 12px;
		overflow-wrap: normal;
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

	.list-head {
		display: flex;
		flex-wrap: wrap;
		justify-content: space-between;
		align-items: baseline;
		column-gap: 1rem;
	}

	.undo,
	.batch,
	.confirm {
		margin: 0 0 1.25rem;
		padding: 0.75rem 0.9rem;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		background: var(--surface);
	}

	.undo h2,
	.batch h2 {
		font-size: 1rem;
		margin: 0 0 0.5rem;
	}

	.confirm h3 {
		font-size: 1rem;
		margin: 0 0 0.5rem;
	}

	.undo p,
	.confirm p {
		margin: 0 0 0.5rem;
	}

	.affected {
		margin: 0 0 0.5rem;
		padding-left: 1.1rem;
		max-height: 16rem;
		overflow: auto;
	}

	.batch-form fieldset {
		border: 0;
		margin: 0;
		padding: 0;
		min-width: 0;
	}

	.batch-form legend {
		font-weight: 600;
		margin-bottom: 0.4rem;
	}

	.batch-form .changes {
		display: grid;
		gap: 0.75rem;
	}

	.jumps li.pick {
		grid-template-columns: auto 1fr;
	}

	.pick input[type='checkbox'] {
		width: 1.4rem;
		height: 1.4rem;
		margin: 0;
	}

	.pick .text {
		cursor: pointer;
	}

	.title-text {
		font-weight: 600;
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
		/* The plain surface: accent links on --surface-soft fail WCAG contrast. */
		background: var(--surface);
		box-shadow: 0 0 0 1px var(--border);
	}

	.matched p {
		margin: 0;
	}

	.matched p + p {
		margin-top: 0.25rem;
	}

	.ahead {
		margin: 0 0 1.25rem;
		padding: 0.75rem 0.9rem;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		background: var(--surface);
		font-size: 0.95rem;
	}

	.ahead h2 {
		font-size: 1rem;
		margin: 0 0 0.35rem;
	}

	.ahead .more-link {
		margin: 0.4rem 0 0;
	}

	/* Nothing in it yet (beside the jumps only): a line and a link, no card. */
	.ahead.quiet {
		padding: 0.6rem 0 0;
		border: 0;
		border-top: 1px solid var(--border);
		border-radius: 0;
		background: none;
	}

	.ahead.quiet p {
		margin: 0;
		color: var(--muted);
	}

	.ahead.quiet .more-link {
		margin-top: 0.25rem;
	}

	.coming {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 0.4rem;
	}

	.coming li {
		display: flex;
		flex-wrap: wrap;
		column-gap: 0.5rem;
		align-items: baseline;
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
