<script lang="ts">
	import { page } from '$app/state';
	import ReviewHistory from '#lib/components/ReviewHistory.svelte';
	import { COUNTRY_OPTIONS } from '#lib/countries.ts';
	import { reviewMessage } from '#lib/review-messages.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();
	const venue = $derived(data.venue);
	const v = (name: string, current: string | number | null | undefined) =>
		form && 'values' in form && form.values ? (form.values[name] ?? '') : String(current ?? '');
	const errorFor = (name: string) =>
		form && form.form === name && 'error' in form ? reviewMessage(form.error) : undefined;
	const NEXT: Record<string, string[]> = {
		draft: ['listed'],
		listed: ['closed'],
		closed: ['listed'],
		merged: []
	};
</script>

<svelte:head>
	<title>{venue ? venue.name : 'New dropzone'} · Maintenance · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<p><a href="/review">Maintenance</a></p>
<h1>{venue ? venue.name : 'New dropzone'}</h1>
{#if venue}
	<p class="lede">
		{venue.status} · version {venue.version}
		{#if venue.status === 'listed' || venue.status === 'closed'} · <a href="/dz/{venue.id}">public page</a>{/if}
	</p>
{/if}
{#if page.url.searchParams.get('saved') || (form && form.form === 'save' && 'done' in form)}
	<p role="status">Saved.</p>
{/if}
{#if page.url.searchParams.get('merged')}<p role="status">Merged into this dropzone.</p>{/if}

{#if venue?.status === 'merged'}
	<p>Merged into <a href="/review/dropzones/{venue.merged_into_id}">another dropzone</a>.</p>
{:else}
	<form method="POST" action="?/save" class="form" novalidate>
		{#if errorFor('save')}<p class="form-error" role="alert">{errorFor('save')}</p>{/if}
		<input type="hidden" name="version" value={venue?.version ?? ''} />
		<div class="field">
			<label for="name">Name</label>
			<input id="name" name="name" maxlength="120" required defaultValue={v('name', venue?.name)} />
			{#if venue}<p class="hint">Renaming keeps the old name searchable as a former name.</p>{/if}
		</div>
		<div class="field">
			<label for="country">Country</label>
			<select id="country" name="country" required>
				<option value="">Choose a country</option>
				{#each COUNTRY_OPTIONS as option (option.code)}
					<option value={option.code} selected={v('country', venue?.country) === option.code}>{option.name}</option>
				{/each}
			</select>
		</div>
		<div class="field">
			<label for="locality">Locality (optional)</label>
			<input id="locality" name="locality" maxlength="120" defaultValue={v('locality', venue?.locality)} />
		</div>
		<div class="coords">
			<div class="field">
				<label for="latitude">Latitude (optional)</label>
				<input id="latitude" name="latitude" inputmode="decimal" defaultValue={v('latitude', venue?.latitude)} />
			</div>
			<div class="field">
				<label for="longitude">Longitude (optional)</label>
				<input id="longitude" name="longitude" inputmode="decimal" defaultValue={v('longitude', venue?.longitude)} />
			</div>
		</div>
		<div class="field">
			<label for="source_url">Source link</label>
			<input id="source_url" name="source_url" type="url" defaultValue={v('source_url', venue?.source_url)} />
		</div>
		<div class="field">
			<label for="source_note">Source note (optional)</label>
			<input id="source_note" name="source_note" maxlength="280" defaultValue={v('source_note', venue?.source_note)} />
		</div>
		<div class="field">
			<label for="checked_on">Source last checked</label>
			<input id="checked_on" name="checked_on" type="date" defaultValue={v('checked_on', venue?.checked_on)} />
		</div>
		{#if !venue}
			<label class="choice"><input type="checkbox" name="listed" checked /> List publicly now (needs source and check date)</label>
		{/if}
		<div class="form-actions"><button class="button" type="submit">Save</button></div>
	</form>

	{#if venue}
		<h2>Other names</h2>
		{#if venue.aliases.length}
			<ul>
				{#each venue.aliases as alias (alias.kind + alias.name)}<li>{alias.name} <span class="hint">({alias.kind})</span></li>{/each}
			</ul>
		{/if}
		{#if errorFor('alias')}<p class="form-error" role="alert">{errorFor('alias')}</p>{/if}
		<form method="POST" action="?/alias" class="form inline">
			<input type="hidden" name="version" value={venue.version} />
			<div class="field">
				<label for="alias">Add an alternate name</label>
				<input id="alias" name="name" maxlength="120" />
			</div>
			<div class="form-actions"><button class="button secondary" type="submit">Add name</button></div>
		</form>

		<h2>Status</h2>
		{#if errorFor('status')}<p class="form-error" role="alert">{errorFor('status')}</p>{/if}
		<form method="POST" action="?/status" class="form-actions">
			<input type="hidden" name="version" value={venue.version} />
			{#each NEXT[venue.status] ?? [] as status (status)}
				<button class="button secondary" type="submit" name="status" value={status}>Make {status}</button>
			{/each}
		</form>
		<p class="hint">A listed dropzone cannot return to draft; close it instead so records keep working.</p>

		<h2>Merge a duplicate</h2>
		<form method="GET" class="form inline">
			<div class="field">
				<label for="merge_q">Find the dropzone to keep</label>
				<input id="merge_q" name="merge_q" type="search" maxlength="80" defaultValue={data.mergeQ} />
			</div>
			<div class="form-actions"><button class="button secondary" type="submit">Search</button></div>
		</form>
		{#if data.mergeQ}
			{#if errorFor('merge')}<p class="form-error" role="alert">{errorFor('merge')}</p>{/if}
			<form method="POST" action="?/merge" class="form">
				<input type="hidden" name="version" value={venue.version} />
				<div class="field">
					<label for="into">Keep</label>
					<select id="into" name="into">
						{#each data.mergeTargets as target (target.id)}
							<option value={target.id}>{target.name} ({target.country})</option>
						{:else}
							<option value="">No listed dropzone matches</option>
						{/each}
					</select>
				</div>
				<div class="form-actions"><button class="button secondary" type="submit">Merge this one into it</button></div>
			</form>
		{/if}

		<ReviewHistory events={venue.events} />
	{/if}
{/if}

<style>
	.coords {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 10rem), 1fr));
		gap: 1rem;
	}

</style>
