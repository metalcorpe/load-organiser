<script lang="ts">
	import { page } from '$app/state';
	import ReviewHistory from '#lib/components/ReviewHistory.svelte';
	import { COUNTRY_OPTIONS } from '#lib/countries.ts';
	import { reviewMessage } from '#lib/review-messages.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();
	const p = $derived(data.provider);
	const v = (name: string, current: string | null | undefined) =>
		form && 'values' in form && form.values ? (form.values[name] ?? '') : (current ?? '');
	const errorFor = (name: string) =>
		form && form.form === name && 'error' in form ? reviewMessage(form.error) : undefined;
	const NEXT: Record<string, string[]> = {
		draft: ['published', 'archived'],
		published: ['archived'],
		archived: ['draft', 'published'],
		merged: []
	};
</script>

<svelte:head>
	<title>{p ? p.name : 'New organizer'} · Maintenance · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<p><a href="/review">Maintenance</a></p>
<h1>{p ? p.name : 'New organizer'}</h1>
{#if p}
	<p class="lede">
		{p.status} · version {p.version}
		{#if p.status === 'published'} · <a href="/organizers/{p.id}">public page</a>{/if}
	</p>
{/if}
{#if page.url.searchParams.get('saved') || (form && form.form === 'save' && 'done' in form)}
	<p role="status">Saved.</p>
{/if}
{#if page.url.searchParams.get('merged')}<p role="status">Merged into this organizer.</p>{/if}

{#if p?.status === 'merged'}
	<p>Merged into <a href="/review/organizers/{p.merged_into_id}">another organizer</a>.</p>
{:else}
	<form method="POST" action="?/save" class="form" novalidate>
		{#if errorFor('save')}<p class="form-error" role="alert">{errorFor('save')}</p>{/if}
		<input type="hidden" name="version" value={p?.version ?? ''} />
		<div class="field">
			<label for="name">Name</label>
			<input id="name" name="name" maxlength="120" required defaultValue={v('name', p?.name)} />
		</div>
		<div class="field">
			<label for="kind">Kind</label>
			<select id="kind" name="kind">
				{#each [['organization', 'Organization'], ['person', 'Person (coach or individual)']] as [value, label] (value)}
					<option {value} selected={v('kind', p?.kind ?? 'organization') === value}>{label}</option>
				{/each}
			</select>
		</div>
		<div class="field">
			<label for="country">Based in (optional)</label>
			<select id="country" name="country">
				<option value="">Not stated</option>
				{#each COUNTRY_OPTIONS as option (option.code)}
					<option value={option.code} selected={v('country', p?.country) === option.code}>{option.name}</option>
				{/each}
			</select>
		</div>
		<div class="field">
			<label for="website_url">Website (optional)</label>
			<input id="website_url" name="website_url" type="url" defaultValue={v('website_url', p?.website_url)} />
		</div>
		<div class="field">
			<label for="source_url">Source link</label>
			<input id="source_url" name="source_url" type="url" defaultValue={v('source_url', p?.source_url)} />
		</div>
		<div class="field">
			<label for="source_note">Source note (optional)</label>
			<input id="source_note" name="source_note" maxlength="280" defaultValue={v('source_note', p?.source_note)} />
		</div>
		<div class="field">
			<label for="checked_on">Source last checked</label>
			<input id="checked_on" name="checked_on" type="date" defaultValue={v('checked_on', p?.checked_on)} />
		</div>
		{#if !p}
			<label class="choice"><input type="checkbox" name="publish" /> Publish now (needs source and check date)</label>
		{/if}
		<div class="form-actions"><button class="button" type="submit">Save</button></div>
	</form>

	{#if p}
		<h2>Status</h2>
		{#if errorFor('status')}<p class="form-error" role="alert">{errorFor('status')}</p>{/if}
		<form method="POST" action="?/status" class="form-actions">
			<input type="hidden" name="version" value={p.version} />
			{#each NEXT[p.status] ?? [] as status (status)}
				<button class="button secondary" type="submit" name="status" value={status}>Make {status}</button>
			{/each}
		</form>

		<h2>Merge a duplicate</h2>
		<p class="hint">Moves this organizer's listings to the one you choose; this address keeps working.</p>
		{#if errorFor('merge')}<p class="form-error" role="alert">{errorFor('merge')}</p>{/if}
		<form method="POST" action="?/merge" class="form">
			<input type="hidden" name="version" value={p.version} />
			<div class="field">
				<label for="into">Keep this organizer instead</label>
				<select id="into" name="into">
					<option value="">Choose…</option>
					{#each data.mergeTargets as target (target.id)}
						<option value={target.id}>{target.name}</option>
					{/each}
				</select>
			</div>
			<div class="form-actions"><button class="button secondary" type="submit">Merge into it</button></div>
		</form>

		<ReviewHistory events={p.events} />
	{/if}
{/if}

<style>
	.choice {
		display: flex;
		gap: 0.5rem;
		align-items: center;
		min-height: 44px;
	}
</style>
