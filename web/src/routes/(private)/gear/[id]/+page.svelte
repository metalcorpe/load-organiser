<script lang="ts">
	import { page } from '$app/state';
	import ReviewHistory from '#lib/components/ReviewHistory.svelte';
	import { KIND_LABEL, METHOD_LABEL, RELATION_LABEL, SERVICE_LABEL, gearMessage } from '#lib/gear.ts';
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
		{KIND_LABEL[c.kind]} · {RELATION_LABEL[c.relation]}{c.archived ? ' · archived' : ''} · entered by
		you, not verified
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
	<input type="hidden" name="version" value={c?.version ?? ''} />
	{#if !c}<input type="hidden" name="client_key" value={data.createKey} />{/if}
	<div class="field">
		<label for="kind">Type</label>
		<select id="kind" name="kind" required>
			{#each Object.entries(KIND_LABEL) as [value, label] (value)}
				<option {value} selected={v('kind', c?.kind ?? 'main') === value}>{label}</option>
			{/each}
		</select>
	</div>
	<div class="field">
		<label for="label">Label</label>
		<input id="label" name="label" maxlength="80" required defaultValue={v('label', c?.label)} />
		<p class="hint">How you recognise it, e.g. "Blue Sabre 2 170".</p>
	</div>
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
	<div class="field">
		<label for="notes">Notes (optional, private)</label>
		<textarea id="notes" name="notes" maxlength="1000" rows="3">{v('notes', c?.notes)}</textarea>
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
					<select id="rig_id" name="rig_id">
						<option value="">Out of any rig</option>
						{#each data.rigs as rig (rig.id)}
							<option value={rig.id} selected={d.rig?.rig_id === rig.id}>{rig.label}</option>
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

	<h2>Service you recorded</h2>
	<p class="hint">Dates you entered yourself. They do not certify servicing or airworthiness.</p>
	{#if errorFor('removeService')}<p class="form-error" role="alert">{errorFor('removeService')}</p>{/if}
	{#if d.service.length === 0}
		<p>No service entries.</p>
	{:else}
		<ul class="results" aria-label="Service entries">
			{#each d.service as entry (entry.id)}
				<li>
					<span class="title">{SERVICE_LABEL[entry.kind]} on {formatDay(entry.done_on)}</span>
					{#if entry.due_on}<span class="meta">Next due you entered: {formatDay(entry.due_on)}</span>{/if}
					{#if entry.performed_by}<span class="meta">By (as you entered): {entry.performed_by}</span>{/if}
					{#if entry.notes}<span class="meta notes">{entry.notes}</span>{/if}
					<form method="POST" action="?/removeService">
						<input type="hidden" name="entry" value={entry.id} />
						<button class="button secondary small" type="submit">Remove</button>
					</form>
				</li>
			{/each}
		</ul>
	{/if}
	{#if page.url.searchParams.get('service')}<p role="status">Service entry saved.</p>{/if}
	<form method="POST" action="?/service" class="form">
		{#if errorFor('service')}<p class="form-error" role="alert">{errorFor('service')}</p>{/if}
		<input type="hidden" name="client_key" value={data.serviceKey} />
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
		<div class="form-actions"><button class="button secondary" type="submit">Delete permanently</button></div>
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

	.choice {
		display: flex;
		gap: 0.5rem;
		align-items: center;
		min-height: 44px;
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
