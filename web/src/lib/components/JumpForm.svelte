<script lang="ts">
	import Disclosure from '#lib/components/Disclosure.svelte';
	import TextArea from '#lib/components/TextArea.svelte';
	import { onMount } from 'svelte';
	import { fieldsFor } from '#lib/field-errors.ts';
	import { KIND_LABEL } from '#lib/gear.ts';
	import { DATUM_LABEL, JUMP_TYPE_LABEL } from '#lib/jumps.ts';
	import {
		UNIT_LABEL,
		formatWeight,
		highestNote,
		isNotable,
		parseWeight,
		wingLoading,
		type LoadingContext,
		type WeightUnit
	} from '#lib/wing-loading.ts';

	type Gear = {
		id: string;
		label: string;
		kind: string;
		archived: boolean;
		canopySize?: number | null;
	};

	/**
	 * The private jump form (#153), for both a new entry and an edit. Values come
	 * from the saved jump or from the refused submission (`echoed`), so nothing
	 * typed is lost on a refusal. Gear is optional: nothing is preselected, and an
	 * unknown answer is simply no selection.
	 */
	let {
		action,
		values,
		location,
		gear,
		selected,
		keys,
		version = null,
		submitLabel,
		confirmDistinct = false,
		disabled = false,
		numberHint = null,
		aircraftHint = null,
		loading = null,
		error = null,
		openFilled = true
	}: {
		action: string;
		values: Record<string, string>;
		location: { name: string; detail: string; venueId: string | null; placeId: string | null; changeHref: string };
		gear: Gear[];
		selected: string[];
		keys: { jump?: string; component: string };
		version?: number | null;
		submitLabel: string;
		confirmDistinct?: boolean;
		disabled?: boolean;
		/** Why the jump number is filled in, e.g. "Your last numbered jump is #120." */
		numberHint?: string | null;
		/** Why the aircraft is filled in, e.g. "From your last jump at this place." */
		aircraftHint?: string | null;
		/** For the wing loading note: the usual exit weight and the highest of the other jumps. */
		loading?: LoadingContext | null;
		/** The refusal shown for this form, if any: its section opens so the field can take focus. */
		error?: string | null;
		/**
		 * Open the optional sections that hold values (an edit). A new jump passes false: its
		 * proposed number, aircraft or copied details stay folded, named in each summary.
		 */
		openFilled?: boolean;
	} = $props();

	let dateInput: HTMLInputElement | undefined = $state();
	let zoneInput: HTMLInputElement | undefined = $state();
	const pad = (n: number) => String(n).padStart(2, '0');

	onMount(() => {
		// The jumper's own local day; set in the browser, never from the server clock.
		if (dateInput && !dateInput.value) {
			const now = new Date();
			dateInput.value = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
		}
		if (zoneInput && !zoneInput.value) {
			zoneInput.value = Intl.DateTimeFormat().resolvedOptions().timeZone ?? '';
		}
	});

	const v = (name: string) => values[name] ?? '';
	const chosen = $derived(new Set(selected));
	// A refused form keeps the unit its number was typed in.
	const unit = $derived<WeightUnit>(
		v('exit_weight_unit') === 'lb' || v('exit_weight_unit') === 'kg'
			? (v('exit_weight_unit') as WeightUnit)
			: (loading?.unit ?? 'kg')
	);

	// The wing loading note follows the ticked gear and the weight typed, read from the
	// form itself (the inputs stay uncontrolled, so nothing typed before hydration is lost).
	// svelte-ignore state_referenced_locally
	let ticked = $state<string[]>(selected);
	// svelte-ignore state_referenced_locally
	let weightText = $state(values.exit_weight ?? '');
	let formElement: HTMLFormElement | undefined = $state();
	// The optional fields as they stand in the form, for the sections' "Filled in" line:
	// null until the first change, then read the same way as the gear and the weight.
	let current = $state<Record<string, string> | null>(null);
	function follow() {
		if (!formElement) return;
		const data = new FormData(formElement);
		ticked = data.getAll('component_ids').map(String);
		weightText = String(data.get('exit_weight') ?? '');
		current = Object.fromEntries(
			Object.values(SECTIONS).flatMap((section) =>
				Object.keys(section.named).map((name) => [name, String(data.get(name) ?? '')])
			)
		);
	}
	const candidate = $derived.by(() => {
		if (!loading) return null;
		const mains = gear.filter((g) => g.kind === 'main' && ticked.includes(g.id));
		const size = mains.length === 1 ? (mains[0].canopySize ?? null) : null;
		const typed = parseWeight(weightText, unit);
		const grams = typed === 'invalid' ? null : (typed ?? loading.usualGrams);
		return wingLoading(grams, size);
	});
	const note = $derived(
		loading && candidate !== null && loading.highest !== null && isNotable(candidate, loading.highest)
			? highestNote(candidate, loading.highest)
			: ''
	);
	// Quick entry: the date, place and type, then a save button. Everything else is in three
	// named sections that stay folded unless they hold something to see. A folded section is
	// still part of the form, so its values (typed, proposed or saved) are always sent.
	const SECTIONS = {
		details: {
			fields: ['jump_number', 'freefall_seconds', 'exit_time', 'time_zone', 'exit_altitude',
				'deployment_altitude', 'altitude_unit', 'altitude_datum', 'aircraft'],
			// What counts as filled in (a time zone, unit or datum alone says nothing).
			named: { jump_number: 'number', exit_time: 'exit time', exit_altitude: 'altitudes',
				deployment_altitude: 'altitudes', freefall_seconds: 'freefall', aircraft: 'aircraft' }
		},
		equipment: {
			fields: ['component_ids', 'other_gear', 'new_component_kind', 'new_component_label',
				'exit_weight'],
			named: { other_gear: 'other equipment', new_component_label: 'new component',
				exit_weight: 'exit weight' }
		},
		notes: { fields: ['notes', 'links'], named: { notes: 'notes', links: 'links' } }
	} as const;
	type Section = keyof typeof SECTIONS;

	// What a section holds now: what was typed since the page loaded, else what it came with.
	const filled = (section: Section): string[] => {
		const names: string[] = Object.entries(SECTIONS[section].named)
			.filter(([field]) => (current ? (current[field] ?? '') : v(field)).trim() !== '')
			.map(([, name]) => name);
		if (section === 'equipment' && ticked.length > 0) {
			names.unshift(ticked.length === 1 ? '1 item of gear' : `${ticked.length} items of gear`);
		}
		return [...new Set(names)];
	};
	const errorFields = $derived(fieldsFor(error));
	const hasError = (section: Section) =>
		errorFields.some((name) => (SECTIONS[section].fields as readonly string[]).includes(name));
	const isOpen = (section: Section) =>
		hasError(section) || (openFilled && filled(section).length > 0);
	// Decided once, when the form is made; Disclosure applies it only then (see there), so
	// a section the jumper opens stays open whatever else on the form updates.
	// svelte-ignore state_referenced_locally
	const opened = {
		details: isOpen('details'),
		equipment: isOpen('equipment'),
		notes: isOpen('notes'),
		// Open when re-shown with a label, so nothing hidden is sent again.
		component: v('new_component_label') !== '' || fieldsFor(error).includes('new_component_label')
	};
</script>

<form
	method="POST"
	{action}
	class="form"
	novalidate
	bind:this={formElement}
	onchange={follow}
	oninput={follow}
>
	{#if keys.jump}<input type="hidden" name="client_key" value={keys.jump} />{/if}
	{#if version}<input type="hidden" name="version" value={version} />{/if}
	{#if confirmDistinct}<input type="hidden" name="confirm_distinct" value="1" />{/if}
	{#if location.venueId}<input type="hidden" name="venue_id" value={location.venueId} />{/if}
	{#if location.placeId}<input type="hidden" name="place_id" value={location.placeId} />{/if}

	<div class="field">
		<span class="label">Where</span>
		<p><strong>{location.name}</strong> <span class="meta">{location.detail}</span></p>
		<p><a href={location.changeHref}>Change place</a></p>
	</div>
	<div class="pair">
		<div class="field">
			<label for="jumped_on">Date</label>
			<input id="jumped_on" name="jumped_on" type="date" required bind:this={dateInput} defaultValue={v('jumped_on')} />
		</div>
		<div class="field">
			<label for="jump_type">Type</label>
			<select id="jump_type" name="jump_type" required>
				{#each Object.entries(JUMP_TYPE_LABEL) as [value, label] (value)}
					<option {value} selected={(v('jump_type') || 'unspecified') === value}>{label}</option>
				{/each}
			</select>
		</div>
	</div>

	<!-- The essentials are enough to save: this button sends the whole form, folded
	     sections included, exactly like the one at the end. -->
	<div class="form-actions">
		<button class="button" type="submit" {disabled}>{submitLabel}</button>
	</div>

	<Disclosure class="section" open={opened.details}>
		{#snippet summary()}
			Number, time, altitudes and aircraft (optional){#if filled('details').length}<span
					class="filled"><span class="visually-hidden">. </span>Filled in: {filled('details').join(', ')}</span
				>{/if}
		{/snippet}
		<div class="section-body">
			<div class="pair">
				<div class="field">
					<label for="jump_number">Your jump number</label>
					<input
						id="jump_number"
						name="jump_number"
						inputmode="numeric"
						maxlength="8"
						defaultValue={v('jump_number')}
						aria-describedby={numberHint ? 'jump_number_hint' : undefined}
					/>
					{#if numberHint}<p class="hint" id="jump_number_hint">{numberHint} Change it if needed.</p>{/if}
				</div>
				<div class="field">
					<label for="freefall_seconds">Freefall (seconds)</label>
					<input id="freefall_seconds" name="freefall_seconds" inputmode="numeric" maxlength="4" defaultValue={v('freefall_seconds')} />
				</div>
			</div>
			<div class="pair">
				<div class="field">
					<label for="exit_time">Exit time (local)</label>
					<input id="exit_time" name="exit_time" type="time" defaultValue={v('exit_time')} />
				</div>
				<div class="field">
					<label for="time_zone">Time zone</label>
					<input id="time_zone" name="time_zone" maxlength="64" placeholder="Europe/Madrid" autocomplete="off" bind:this={zoneInput} defaultValue={v('time_zone')} />
				</div>
			</div>
			<p class="hint">Leave the time empty if you don't know it; it is never filled in for you.</p>
			<div class="pair">
				<div class="field">
					<label for="exit_altitude">Exit altitude</label>
					<input id="exit_altitude" name="exit_altitude" inputmode="numeric" maxlength="7" defaultValue={v('exit_altitude')} />
				</div>
				<div class="field">
					<label for="deployment_altitude">Deployment altitude</label>
					<input id="deployment_altitude" name="deployment_altitude" inputmode="numeric" maxlength="7" defaultValue={v('deployment_altitude')} />
				</div>
			</div>
			<fieldset class="field">
				<legend>Altitude unit</legend>
				<label class="choice"><input type="radio" name="altitude_unit" value="ft" checked={v('altitude_unit') === 'ft'} /> Feet</label>
				<label class="choice"><input type="radio" name="altitude_unit" value="m" checked={v('altitude_unit') === 'm'} /> Metres</label>
			</fieldset>
			<div class="field">
				<label for="altitude_datum">Measured from</label>
				<select id="altitude_datum" name="altitude_datum">
					{#each Object.entries(DATUM_LABEL) as [value, label] (value)}
						<option {value} selected={(v('altitude_datum') || 'unspecified') === value}>{label}</option>
					{/each}
				</select>
			</div>

			<div class="field">
				<label for="aircraft">Aircraft (optional)</label>
				<input
					id="aircraft"
					name="aircraft"
					maxlength="60"
					autocomplete="off"
					placeholder="e.g. Cessna 208 SX-ABC"
					defaultValue={v('aircraft')}
					aria-describedby={aircraftHint ? 'aircraft_hint' : undefined}
				/>
				{#if aircraftHint}<p class="hint" id="aircraft_hint">{aircraftHint} Change it if needed.</p>{/if}
			</div>
		</div>
	</Disclosure>

	<Disclosure class="section" open={opened.equipment}>
		{#snippet summary()}
			Equipment and exit weight (optional){#if filled('equipment').length}<span class="filled"
					><span class="visually-hidden">. </span>Filled in: {filled('equipment').join(', ')}</span
				>{/if}
		{/snippet}
		<div class="section-body">
			<fieldset class="field">
				<legend>Equipment used (optional)</legend>
				<p class="hint">
					Tick only what you actually jumped. Leave everything empty if you don't know; your current rig is
					not assumed.
				</p>
				{#each gear as item (item.id)}
					<label class="choice">
						<input type="checkbox" name="component_ids" value={item.id} checked={chosen.has(item.id)} />
						{item.label} <span class="meta"
							>({KIND_LABEL[item.kind] ?? item.kind}{item.canopySize ? `, ${item.canopySize} sq ft` : ''}{item.archived
								? ', archived'
								: ''})</span
						>
					</label>
				{/each}
				<div class="field">
					<label for="other_gear">Borrowed, rented or other equipment</label>
					<input id="other_gear" name="other_gear" maxlength="200" placeholder="e.g. rented student rig" defaultValue={v('other_gear')} />
				</div>
				<Disclosure open={opened.component}>
					{#snippet summary()}Add a new component used on this jump{/snippet}
					<input type="hidden" name="new_component_key" value={keys.component} />
					<div class="pair">
						<div class="field">
							<label for="new_component_kind">Component type</label>
							<select id="new_component_kind" name="new_component_kind">
								{#each Object.entries(KIND_LABEL) as [value, label] (value)}
									<option {value} selected={(v('new_component_kind') || 'main') === value}>{label}</option>
								{/each}
							</select>
						</div>
						<div class="field">
							<label for="new_component_label">Component label</label>
							<input id="new_component_label" name="new_component_label" maxlength="80" defaultValue={v('new_component_label')} />
						</div>
					</div>
					<p class="hint">
						Saved to your private gear together with this jump. Leave the label empty to skip it; you can add
						serials and dates later under Gear.
					</p>
				</Disclosure>
			</fieldset>

			<div class="field">
				<label for="exit_weight">Exit weight on this jump in {UNIT_LABEL[unit]} (optional)</label>
				<input type="hidden" name="exit_weight_unit" value={unit} />
				{#if v('exit_weight_saved')}
					<!-- The saved weight and how it was shown: an untouched field is not sent again,
					     so a conversion to and from the unit never changes it. -->
					<input type="hidden" name="exit_weight_saved" value={v('exit_weight_saved')} />
					<input type="hidden" name="exit_weight_shown" value={v('exit_weight_shown')} />
				{/if}
				<input
					id="exit_weight"
					name="exit_weight"
					inputmode="decimal"
					maxlength="6"
					autocomplete="off"
					defaultValue={v('exit_weight')}
					aria-describedby="exit_weight_hint"
				/>
				<p class="hint" id="exit_weight_hint">
					Your weight with your gear on, for the wing loading.
					{#if loading?.usualGrams}Empty: your usual exit weight, {formatWeight(loading.usualGrams, unit)}.
					{:else}Set your usual exit weight on your <a href="/profile#weight-heading">profile</a>.{/if}
				</p>
				<p class="hint" role="status">{note}</p>
			</div>
		</div>
	</Disclosure>

	<Disclosure class="section" open={opened.notes}>
		{#snippet summary()}
			Notes and links (optional, private){#if filled('notes').length}<span class="filled"
					><span class="visually-hidden">. </span>Filled in: {filled('notes').join(', ')}</span
				>{/if}
		{/snippet}
		<div class="section-body">
			<div class="field">
				<label for="notes">Notes (optional, private)</label>
				<TextArea id="notes" name="notes" maxlength={2000} rows={3} initial={v('notes')} />
			</div>
			<div class="field">
				<label for="links">Links (optional, private; one per line, at most five)</label>
				<TextArea id="links" name="links" rows={2} spellcheck="false" initial={v('links')} />
			</div>
		</div>
	</Disclosure>
	<p class="hint">This is your own record. Nothing here is shared or verified.</p>
	<div class="form-actions">
		<button class="button" type="submit" {disabled}>{submitLabel}</button>
	</div>
</form>

<style>
	/* Two fields side by side when there is room, each with the form's own spacing. */
	.pair {
		display: grid;
		gap: 1rem;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 12rem), 1fr));
	}

	/* A folded group of optional fields: a full-width row with its summary, then the fields with
	   the form's own spacing. */
	/* The <details> and <summary> are rendered by Disclosure, hence :global. */
	.form :global(details.section) {
		border-top: 1px solid var(--border);
		padding-top: 0.25rem;
	}

	.form :global(details.section > summary) {
		display: flex;
		flex-wrap: wrap;
		gap: 0.1rem 0.4rem;
	}

	.form :global(details.section > summary::after) {
		order: 1;
	}

	.filled {
		order: 2;
		flex-basis: 100%;
		color: var(--muted);
		font-size: 0.9rem;
		font-weight: 400;
	}

	.section-body {
		display: grid;
		gap: 1rem;
		padding: 0.5rem 0 0.25rem;
	}
</style>
