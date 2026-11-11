<script lang="ts">
	import { page } from '$app/state';
	import JumpForm from '#lib/components/JumpForm.svelte';
	import LocationPicker from '#lib/components/LocationPicker.svelte';
	import Notice from '#lib/components/Notice.svelte';
	import { directoryMessage } from '#lib/directory-messages.ts';
	import { jumpMessage } from '#lib/jumps.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();
	const saveForm = $derived(form && form.form === 'save' ? form : null);
	const values = $derived(
		(saveForm && 'values' in saveForm ? saveForm.values : null) ?? ({} as Record<string, string>)
	);
	const duplicateOf = $derived(saveForm && 'duplicateOf' in saveForm ? saveForm.duplicateOf : null);
	// Keep the search and chosen place in the action URL so a refusal re-renders here.
	const query = $derived(
		[...page.url.searchParams].filter(([k]) => k === 'venue' || k === 'place').map(([k, val]) => `${k}=${encodeURIComponent(val)}`).join('&')
	);
</script>

<svelte:head>
	<title>Add jump · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<p><a href="/jumps">Logbook</a></p>
<h1>Add jump</h1>
<p class="lede">A private entry in your own logbook. Only the date, place and type are needed.</p>
{#if !data.emailVerified}
	<p class="hint">Confirm your email address on your <a href="/profile">profile</a> to save jumps.</p>
{/if}
{#if !data.placesOk}
	<p class="form-error" role="alert">Your private places could not be loaded right now.</p>
{/if}

{#if data.chosen}
	{#if saveForm && 'error' in saveForm}
		{#if saveForm.error === 'likely_duplicate' && duplicateOf}
			<Notice title="This looks like a jump you already logged" tone="warn">
				<p role="alert">
					Two jumps on the same day are fine. Check the earlier entry, or save this one as a distinct jump.
				</p>
				<p><a href="/jumps/{duplicateOf}">View the earlier entry</a></p>
			</Notice>
		{:else}
			<p class="form-error" role="alert">{jumpMessage(saveForm.error)}</p>
		{/if}
	{/if}
	<JumpForm
		action="?{query}&/save"
		{values}
		location={{ ...data.chosen, changeHref: '/jumps/new' }}
		gear={data.gear.items}
		selected={(values.component_ids ?? '').split(',').filter(Boolean)}
		keys={{
			jump: values.client_key || data.keys.jump,
			component: values.new_component_key || data.keys.component
		}}
		submitLabel={duplicateOf ? 'Save as a distinct jump' : 'Save private jump'}
		confirmDistinct={Boolean(duplicateOf)}
	/>
	{#if !data.gear.ok}<p class="hint">Your gear could not be loaded; you can still save the jump.</p>{/if}
{:else}
	<LocationPicker
		base="/jumps/new"
		q={data.picker?.q ?? ''}
		matches={data.picker?.matches ?? null}
		places={data.places}
		recent={data.recent}
		error={form && form.form === 'place' && 'error' in form ? directoryMessage(form.error) : undefined}
	/>
{/if}
