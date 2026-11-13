<script lang="ts">
	import { onMount } from 'svelte';
	import TextArea from '#lib/components/TextArea.svelte';
	import { page } from '$app/state';
	import DueList from '#lib/components/DueList.svelte';
	import ReviewHistory from '#lib/components/ReviewHistory.svelte';
	import { localToday } from '#lib/currency.ts';
	import {
		CANOPY_KINDS,
		KIND_LABEL,
		METHOD_LABEL,
		RELATION_LABEL,
		REPACK_INTERVAL_LABEL,
		SERVICE_LABEL,
		gearMessage
	} from '#lib/gear.ts';
	import { formatDay } from '#lib/listings.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();
	const d = $derived(data.detail);
	const c = $derived(d?.component ?? null);
	const echoed = $derived(
		form && 'values' in form && form.values && form.form === 'save' ? form.values : null
	);
	const v = (name: string, current: string | null | undefined) =>
		echoed ? (echoed[name] ?? '') : (current ?? '');
	const errorFor = (name: string) =>
		form && form.form === name && 'error' in form ? gearMessage(form.error) : undefined;
	// Writable derived: follows the record or the echoed form, and the radios.
	let relation = $derived(v('relation', c?.relation ?? 'owned') || 'owned');
	// Only a reserve has a repack interval; the field follows the chosen type.
	// The saved or echoed type is the server-rendered state (`selected` on each option,
	// so a choice made before hydration is not overwritten); `chosen` follows changes.
	const savedKind = $derived(v('kind', c?.kind ?? 'main') || 'main');
	let chosen = $state<string | null>(null);
	const kind = $derived(chosen ?? savedKind);
	// Shown when the record is a reserve (works without JS after a save) or when the
	// type is changed to reserve in the browser.
	const showInterval = $derived(savedKind === 'reserve' || kind === 'reserve');
	// Only a main or reserve canopy has a size, the same way.
	const showSize = $derived(CANOPY_KINDS.includes(savedKind) || CANOPY_KINDS.includes(kind));
	// The server's UTC day until the browser gives the jumper's own calendar day.
	// svelte-ignore state_referenced_locally
	let today = $state(data.today);
	onMount(() => {
		today = localToday();
	});
	const PRECISION: Record<number, string> = { 4: 'year only', 7: 'month only', 10: 'exact day' };
</script>

<svelte:head>
	<title>{c ? c.label : 'Add a component'} · Gear · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<p><a href="/gear">Gear</a></p>
<h1>{c ? c.label : 'Add a component'}</h1>
{#if c}
	<p class="lede">
		{KIND_LABEL[c.kind]}{c.canopy_size_sqft ? ` · ${c.canopy_size_sqft} sq ft` : ''} · {RELATION_LABEL[
			c.relation
		]}{c.archived ? ' · archived' : ''} · entered by you, not verified
	</p>
{/if}
{#if page.url.searchParams.get('saved') || (form && form.form === 'save' && 'done' in form)}
	<p role="status" class="ok">Saved privately.</p>
{/if}
{#if d && d.same_serial.length > 0}
	<p class="hint" role="note">
		You have {d.same_serial.length === 1 ? 'another item' : `${d.same_serial.length} other items`} with
		the same serial:
		{#each d.same_serial as other, i (other)}{i ? ', ' : ''}<a href="/gear/{other}">view</a>{/each}.
		Check for a typing mistake or a duplicate entry.
	</p>
{/if}
{#if !data.emailVerified}
	<p class="hint">Confirm your email address on your <a href="/profile">profile</a> to save gear.</p>
{/if}

<form method="POST" action="?/save" class="form" novalidate>
	{#if errorFor('save')}<p class="form-error" role="alert">{errorFor('save')}</p>{/if}
	<input
		type="hidden"
		name="version"
		value={(echoed && form && 'based' in form && form.based) || (c?.version ?? '')}
	/>
	{#if !c}<input type="hidden" name="client_key" value={echoed?.client_key || data.createKey} />{/if}
	<div class="field">
		<label for="kind">Type</label>
		<select
			id="kind"
			name="kind"
			required
			onchange={(event) => (chosen = event.currentTarget.value)}
		>
			{#each Object.entries(KIND_LABEL) as [value, label] (value)}
				<option {value} selected={savedKind === value}>{label}</option>
			{/each}
		</select>
	</div>
	<div class="field">
		<label for="label">Label</label>
		<input id="label" name="label" maxlength="80" required defaultValue={v('label', c?.label)} />
		<p class="hint">How you recognise it, e.g. "Blue Sabre 2 170".</p>
	</div>
	{#if showSize}
		<div class="field">
			<label for="canopy_size_sqft">Canopy size in square feet (optional)</label>
			<input
				id="canopy_size_sqft"
				name="canopy_size_sqft"
				inputmode="numeric"
				maxlength="10"
				aria-describedby="canopy-size-hint"
				defaultValue={v('canopy_size_sqft', c?.canopy_size_sqft?.toString())}
			/>
			<p class="hint" id="canopy-size-hint">
				As on the canopy's label, e.g. 170. A main canopy's size gives the wing loading of the jumps
				it is recorded on, with your exit weight.
			</p>
		</div>
	{/if}
	<div class="pair">
		<div class="field">
			<label for="manufacturer">Manufacturer (optional)</label>
			<input id="manufacturer" name="manufacturer" maxlength="80" defaultValue={v('manufacturer', c?.manufacturer)} />
		</div>
		<div class="field">
			<label for="model">Model (optional)</label>
			<input id="model" name="model" maxlength="80" defaultValue={v('model', c?.model)} />
		</div>
	</div>
	<div class="field">
		<label for="serial">Serial number (optional, private)</label>
		<input id="serial" name="serial" maxlength="120" autocomplete="off" spellcheck="false" defaultValue={v('serial', c?.serial)} />
		<p class="hint">Kept exactly as typed, including leading zeros and punctuation. Never shown to anyone else.</p>
	</div>
	<div class="field">
		<label for="manufactured">Manufactured (optional)</label>
		<input id="manufactured" name="manufactured" maxlength="10" placeholder="2019 or 2019-04" defaultValue={v('manufactured', c?.manufactured)} />
		<p class="hint">
			Enter only what the label shows: a year, a year and month, or a full date.
			{#if c?.manufactured}Stored as {PRECISION[c.manufactured.length]}.{/if}
		</p>
	</div>
	<fieldset class="field">
		<legend>How you hold it</legend>
		{#each Object.entries(RELATION_LABEL) as [value, label] (value)}
			<label class="choice"><input type="radio" name="relation" {value} bind:group={relation} /> {label}</label>
		{/each}
	</fieldset>
	{#if relation === 'owned'}
		<div class="pair">
			<div class="field">
				<label for="acquisition_method">How you got it (optional)</label>
				<select id="acquisition_method" name="acquisition_method">
					<option value="">Not stated</option>
					{#each Object.entries(METHOD_LABEL) as [value, label] (value)}
						<option {value} selected={v('acquisition_method', c?.acquisition_method) === value}>{label}</option>
					{/each}
				</select>
			</div>
			<div class="field">
				<label for="acquired">When (optional)</label>
				<input id="acquired" name="acquired" maxlength="10" placeholder="2020 or 2020-06" defaultValue={v('acquired', c?.acquired)} />
			</div>
		</div>
	{/if}
	{#if showInterval}
		<div class="field">
			<label for="repack_interval_days">Repack interval in days (optional)</label>
			<input
				id="repack_interval_days"
				name="repack_interval_days"
				inputmode="numeric"
				maxlength="3"
				aria-describedby="repack-interval-hint"
				defaultValue={v('repack_interval_days', c?.repack_interval_days?.toString())}
			/>
			<p class="hint" id="repack-interval-hint">
				Empty: {REPACK_INTERVAL_LABEL}. The next repack is counted from your last recorded repack,
				unless you entered a due date with it.
			</p>
		</div>
	{/if}
	<div class="field">
		<label for="end_of_life_on">End of life (optional)</label>
		<input
			id="end_of_life_on"
			name="end_of_life_on"
			type="date"
			aria-describedby="end-of-life-hint"
			defaultValue={v('end_of_life_on', c?.end_of_life_on)}
		/>
		<p class="hint" id="end-of-life-hint">
			Only a date from the label or the manufacturer's documents, for example an AAD's end of life.
			The app never estimates it.
		</p>
	</div>
	<fieldset class="field">
		<legend>Jump limit (optional)</legend>
		<p class="hint" id="jump-limit-hint">
			Your own number, for example a reline after a number of jumps. Nothing is filled in for you:
			use the manufacturer's or your rigger's figure. It counts the jumps logged with this item since
			its latest service of the kind chosen below, or all of them when there is none.
		</p>
		<div class="pair">
			<div class="field">
				<label for="jump_limit">Limit in jumps</label>
				<input
					id="jump_limit"
					name="jump_limit"
					inputmode="numeric"
					maxlength="7"
					aria-describedby="jump-limit-hint"
					defaultValue={v('jump_limit', c?.jump_limit?.toString())}
				/>
			</div>
			<div class="field">
				<label for="jump_limit_label">What is due then</label>
				<input
					id="jump_limit_label"
					name="jump_limit_label"
					maxlength="80"
					placeholder="e.g. Reline"
					defaultValue={v('jump_limit_label', c?.jump_limit_label)}
				/>
			</div>
		</div>
		<div class="field">
			<label for="jump_limit_service_kind">Count restarts after</label>
			<select id="jump_limit_service_kind" name="jump_limit_service_kind">
				{#each Object.entries(SERVICE_LABEL) as [value, label] (value)}
					<option
						{value}
						selected={(v('jump_limit_service_kind', c?.jump_limit_service_kind) || 'maintenance') === value}
						>{label}</option
					>
				{/each}
			</select>
		</div>
	</fieldset>
	<div class="field">
		<label for="notes">Notes (optional, private)</label>
		<TextArea id="notes" name="notes" maxlength={1000} rows={3} initial={v('notes', c?.notes)} />
	</div>
	<p class="hint">
		This is your own record. It is not proof of ownership and does not say whether the item is
		airworthy.
	</p>
	<div class="form-actions"><button class="button" type="submit">{c ? 'Save changes' : 'Save component'}</button></div>
</form>

{#if c && d}
	<h2>Rig</h2>
	<p>
		{#if d.rig}In <strong>{d.rig.rig_label}</strong> since {formatDay(d.rig.from_on)}.{:else}Not in a rig.{/if}
	</p>
	{#if !c.archived}
		{#if errorFor('place')}<p class="form-error" role="alert">{errorFor('place')}</p>{/if}
		{#if form && form.form === 'place' && 'done' in form}<p role="status">Rig updated.</p>{/if}
		<form method="POST" action="?/place" class="form">
			<input type="hidden" name="version" value={c.version} />
			<div class="pair">
				<div class="field">
					<label for="rig_id">Move to</label>
					<select id="rig_id" name="rig_id" required>
						<option value="" disabled selected>Choose…</option>
						{#if d.rig}<option value="none">Out of any rig</option>{/if}
						{#each data.rigs.filter((r) => r.id !== d.rig?.rig_id) as rig (rig.id)}
							<option value={rig.id}>{rig.label}</option>
						{/each}
					</select>
				</div>
				<div class="field">
					<label for="on">From</label>
					<input id="on" name="on" type="date" required />
				</div>
			</div>
			<div class="form-actions"><button class="button secondary" type="submit">Update rig</button></div>
		</form>
		{#if data.rigs.length === 0}<p class="hint">Add a rig on the <a href="/gear">Gear</a> page first.</p>{/if}
	{/if}
	{#if d.rig_history.length > 0}
		<ul aria-label="Rig history">
			{#each d.rig_history as stint (stint.rig_id + stint.from_on)}
				<li>
					{stint.rig_label}: {formatDay(stint.from_on)} – {stint.until_on ? formatDay(stint.until_on) : 'now'}
				</li>
			{/each}
		</ul>
	{/if}

	{#if data.due.length > 0}
		<section aria-labelledby="due-heading">
			<h2 id="due-heading">Due dates</h2>
			<DueList items={data.due} {today} label="Due dates" detailed />
		</section>
	{/if}

	<h2>Service you recorded</h2>
	<p class="hint">Dates you entered yourself. They do not certify servicing or airworthiness.</p>
	{#if errorFor('removeService')}<p class="form-error" role="alert">{errorFor('removeService')}</p>{/if}
	{#if d.service.length === 0}
		<p>No service entries.</p>
	{:else}
		<ul class="results rows" aria-label="Service entries">
			{#each d.service as entry (entry.id)}
				<li>
					<span class="title">{SERVICE_LABEL[entry.kind]} on {formatDay(entry.done_on)}</span>
					{#if entry.due_on}<span class="meta">Next due you entered: {formatDay(entry.due_on)}</span>{/if}
					{#if entry.performed_by}<span class="meta">By (as you entered): {entry.performed_by}</span>{/if}
					{#if entry.notes}<span class="meta notes">{entry.notes}</span>{/if}
					<form method="POST" action="?/removeService">
						<input type="hidden" name="entry" value={entry.id} />
						<button class="button danger small" type="submit">Remove</button>
					</form>
				</li>
			{/each}
		</ul>
	{/if}
	{#if page.url.searchParams.get('service')}<p role="status">Service entry saved.</p>{/if}
	<form method="POST" action="?/service" class="form">
		{#if errorFor('service')}<p class="form-error" role="alert">{errorFor('service')}</p>{/if}
		<input
			type="hidden"
			name="client_key"
			value={(form && form.form === 'service' && 'values' in form && form.values?.client_key) ||
				data.serviceKey}
		/>
		<div class="pair">
			<div class="field">
				<label for="service-kind">Service</label>
				<select id="service-kind" name="kind">
					{#each Object.entries(SERVICE_LABEL) as [value, label] (value)}
						<option {value}>{label}</option>
					{/each}
				</select>
			</div>
			<div class="field">
				<label for="done_on">Done on</label>
				<input id="done_on" name="done_on" type="date" required />
			</div>
			<div class="field">
				<label for="due_on">Next due (optional)</label>
				<input id="due_on" name="due_on" type="date" />
			</div>
		</div>
		<div class="field">
			<label for="performed_by">Done by (optional)</label>
			<input id="performed_by" name="performed_by" maxlength="120" />
		</div>
		<div class="field">
			<label for="service-notes">Notes (optional)</label>
			<textarea id="service-notes" name="notes" maxlength="1000" rows="2"></textarea>
		</div>
		<div class="form-actions"><button class="button secondary" type="submit">Add service entry</button></div>
	</form>

	<h2>{c.archived ? 'Restore' : 'Archive'}</h2>
	<p class="hint">
		{c.archived
			? 'Restoring puts it back in your current gear list.'
			: 'Archived gear keeps its history; archiving takes it out of its rig today.'}
	</p>
	{#if errorFor('archive')}<p class="form-error" role="alert">{errorFor('archive')}</p>{/if}
	<form method="POST" action="?/archive">
		<input type="hidden" name="version" value={c.version} />
		<input type="hidden" name="archived" value={c.archived ? 'false' : 'true'} />
		<button class="button secondary" type="submit">{c.archived ? 'Restore' : 'Archive'}</button>
	</form>

	<h2>Delete</h2>
	{#if errorFor('delete')}<p class="form-error" role="alert">{errorFor('delete')}</p>{/if}
	<form method="POST" action="?/delete" class="form">
		<input type="hidden" name="version" value={c.version} />
		<label class="choice"><input type="checkbox" name="confirm" /> Delete this item, its service entries and history</label>
		<div class="form-actions"><button class="button danger" type="submit">Delete permanently</button></div>
	</form>

	<ReviewHistory events={d.events} />
{/if}

<style>
	.ok {
		color: var(--ok-fg);
		font-weight: 600;
	}

	.pair {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 10rem), 1fr));
		gap: 1rem;
	}

	fieldset {
		border: 0;
		padding: 0;
		margin: 0;
	}

	legend {
		font-weight: 650;
		margin-bottom: 0.3rem;
	}


	.title {
		font-weight: 600;
		flex-basis: 100%;
	}

	.meta {
		color: var(--muted);
		flex-basis: 100%;
		overflow-wrap: anywhere;
	}

	.notes {
		white-space: pre-line;
	}

	.small {
		min-height: 36px;
		padding: 0.25rem 0.75rem;
	}
</style>
