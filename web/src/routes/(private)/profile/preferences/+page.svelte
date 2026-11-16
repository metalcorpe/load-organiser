<script lang="ts">
	import { LICENCES, LICENCE_LABEL, licenceMessage } from '#lib/currency.ts';
	import { UNIT_NAME, inUnit, weightMessage } from '#lib/wing-loading.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();
	const doneFor = (name: string) => Boolean(form && form.form === name && 'done' in form && form.done);
	// A refused weight re-shows what was typed; otherwise the saved weight in its unit.
	const weightEcho = $derived(
		form && form.form === 'exitWeight' && 'values' in form && form.values ? form.values : null
	);
	const weightError = $derived(
		form && form.form === 'exitWeight' && 'error' in form ? weightMessage(form.error) : null
	);
	const savedWeight = $derived(data.exitWeight?.exit_weight ?? null);
	const weightUnit = $derived(weightEcho?.exit_weight_unit || data.exitWeight?.unit || 'kg');
	const weightValue = $derived(
		weightEcho
			? weightEcho.exit_weight
			: savedWeight
				? String(inUnit(savedWeight.grams, savedWeight.unit))
				: ''
	);
</script>

<svelte:head>
	<title>Jump preferences · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<p><a href="/profile">Me</a></p>
<h1>Jump preferences</h1>
<p class="lede">Only you can see these. They only change what your own pages show.</p>

<section class="setting" aria-labelledby="licence-heading">
	<h2 id="licence-heading">Licence</h2>
	<p>Set it to see your jump currency and progress toward your next licence.</p>
	<details class="about">
		<summary>How it is used</summary>
		<p>
			Currency uses the number of days USPA recommends for your licence (USPA SIM 5-2), counted from
			your most recent logged jump. Progress uses the jump and freefall time requirements for the
			next licence (USPA SIM 3-1).
		</p>
	</details>
	<form method="POST" action="?/licence" class="form" novalidate>
		{#if doneFor('licence')}
			<p role="status" class="ok">Licence saved.</p>
		{:else if form && form.form === 'licence' && 'error' in form}
			<p class="form-error" role="alert">{licenceMessage(form.error)}</p>
		{/if}
		{#if data.licence === null}
			<p class="hint">Your current licence could not be loaded. Saving sets it again.</p>
		{/if}
		<div class="field">
			<label for="licence">Licence</label>
			<select id="licence" name="licence">
				{#each LICENCES as value (value)}
					<option {value} selected={(data.licence ?? 'none') === value}>{LICENCE_LABEL[value]}</option>
				{/each}
			</select>
		</div>
		<div class="form-actions">
			<button class="button" type="submit">Save licence</button>
		</div>
	</form>
</section>

<section class="setting" aria-labelledby="weight-heading">
	<h2 id="weight-heading">Exit weight</h2>
	<p>Your weight with your gear on, for the wing loading of your jumps.</p>
	<details class="about">
		<summary>How it is used</summary>
		<p>
			Wing loading is your exit weight in pounds divided by your main canopy size in square feet.
			A jump can have its own exit weight; this one is used for all your other jumps.
		</p>
	</details>
	<form method="POST" action="?/exitWeight" class="form" novalidate>
		{#if doneFor('exitWeight')}
			<p role="status" class="ok">
				{form && 'cleared' in form && form.cleared ? 'Exit weight removed.' : 'Exit weight saved.'}
			</p>
		{:else if weightError}
			<p class="form-error" role="alert" id="exit-weight-error">{weightError}</p>
		{/if}
		{#if data.exitWeight === null}
			<p class="hint">Your current exit weight could not be loaded. Saving sets it again.</p>
		{/if}
		<div class="pair">
			<div class="field">
				<label for="exit_weight">Exit weight (optional)</label>
				<input
					id="exit_weight"
					name="exit_weight"
					inputmode="decimal"
					maxlength="6"
					autocomplete="off"
					defaultValue={weightValue}
					aria-describedby={weightError ? 'exit-weight-error exit-weight-hint' : 'exit-weight-hint'}
					aria-invalid={weightError ? 'true' : undefined}
				/>
				<p class="hint" id="exit-weight-hint">30 to 250 kg (67 to 551 lb). Leave empty to remove it.</p>
			</div>
			<fieldset class="field">
				<legend>Unit</legend>
				{#each Object.entries(UNIT_NAME) as [value, name] (value)}
					<label class="choice"
						><input type="radio" name="exit_weight_unit" {value} defaultChecked={weightUnit === value} />
						{name}</label
					>
				{/each}
			</fieldset>
		</div>
		<div class="form-actions">
			<button class="button" type="submit">Save exit weight</button>
		</div>
	</form>
</section>

<style>
	/* Two settings, each a heading, one line on what it does, the detail folded, then its form.
	   Separated by a rule rather than two cards of equal weight. */
	.setting {
		max-width: var(--measure);
		padding: 1rem 0 1.25rem;
	}

	.setting + .setting {
		border-top: 1px solid var(--border);
	}

	h2 {
		margin: 0 0 0.35rem;
		font-size: 1.15rem;
	}

	.setting > p {
		margin: 0 0 0.25rem;
	}

	.about {
		margin: 0 0 0.75rem;
		color: var(--muted);
	}

	.about summary {
		display: inline-flex;
		align-items: center;
		min-height: 44px;
		color: var(--accent);
		font-weight: 600;
		cursor: pointer;
	}

	.about p {
		margin: 0 0 0.5rem;
	}

	.pair {
		display: grid;
		gap: 1rem;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 12rem), 1fr));
	}
</style>
