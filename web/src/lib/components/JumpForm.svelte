<script lang="ts">
	import TextArea from '#lib/components/TextArea.svelte';
	import { onMount } from 'svelte';
	import { KIND_LABEL } from '#lib/gear.ts';
	import { DATUM_LABEL, JUMP_TYPE_LABEL } from '#lib/jumps.ts';

	type Gear = { id: string; label: string; kind: string; archived: boolean };

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
		aircraftHint = null
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
	const showDetails = $derived(
		['jump_number', 'exit_time', 'exit_altitude', 'deployment_altitude', 'freefall_seconds'].some(
			(n) => v(n) !== ''
		)
	);
</script>

<form method="POST" {action} class="form" novalidate>
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

	<details open={showDetails}>
		<summary>Number, time and altitudes (optional)</summary>
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
	</details>

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

	<fieldset class="field">
		<legend>Equipment used (optional)</legend>
		<p class="hint">
			Tick only what you actually jumped. Leave everything empty if you don't know; your current rig is
			not assumed.
		</p>
		{#each gear as item (item.id)}
			<label class="choice">
				<input type="checkbox" name="component_ids" value={item.id} checked={chosen.has(item.id)} />
				{item.label} <span class="meta">({KIND_LABEL[item.kind] ?? item.kind}{item.archived ? ', archived' : ''})</span>
			</label>
		{/each}
		<div class="field">
			<label for="other_gear">Borrowed, rented or other equipment</label>
			<input id="other_gear" name="other_gear" maxlength="200" placeholder="e.g. rented student rig" defaultValue={v('other_gear')} />
		</div>
		<!-- Open when re-shown with a label, so nothing hidden is sent again. -->
		<details open={v('new_component_label') !== ''}>
			<summary>Add a new component used on this jump</summary>
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
		</details>
	</fieldset>

	<div class="field">
		<label for="notes">Notes (optional, private)</label>
		<TextArea id="notes" name="notes" maxlength={2000} rows={3} initial={v('notes')} />
	</div>
	<div class="field">
		<label for="links">Links (optional, private; one per line, at most five)</label>
		<TextArea id="links" name="links" rows={2} spellcheck="false" initial={v('links')} />
	</div>
	<p class="hint">This is your own record. Nothing here is shared or verified.</p>
	<div class="form-actions">
		<button class="button" type="submit" {disabled}>{submitLabel}</button>
	</div>
</form>
