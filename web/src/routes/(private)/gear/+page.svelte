<script lang="ts">
	import { page } from '$app/state';
	import { formatDay } from '#lib/listings.ts';
	import { KIND_LABEL, RELATION_LABEL, gearMessage } from '#lib/gear.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();
	const errorFor = (name: string) =>
		form && form.form === name && 'error' in form ? gearMessage(form.error) : undefined;
</script>

<svelte:head>
	<title>Gear · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<p><a href="/records">Records</a></p>
<h1>Gear</h1>
<p class="lede">
	Your own private record of containers, canopies and AADs. Everything here is what you entered: it
	does not verify ownership, servicing or airworthiness, and nobody else can see it.
</p>

{#if !data.emailVerified}
	<p class="hint">Confirm your email address on your <a href="/profile">profile</a> to save gear.</p>
{/if}

<p class="actions">
	<a class="button" href="/gear/new">Add a component</a>
	{#if data.archived}
		<a href="/gear">Show current gear</a>
	{:else}
		<a href="/gear?archived=1">Show archived gear</a>
	{/if}
</p>

<h2>{data.archived ? 'Archived components' : 'Components'}</h2>
{#if !data.components.ok}
	<p class="form-error" role="alert">{gearMessage(data.components.reason)}</p>
{:else if data.components.items.length === 0}
	<p>{data.archived ? 'No archived components.' : 'No components yet. Gear is optional; logging a jump never requires it.'}</p>
{:else}
	<ul class="results" aria-label="Components">
		{#each data.components.items as item (item.component.id)}
			<li>
				<a class="title" href="/gear/{item.component.id}">{item.component.label}</a>
				<span class="meta">
					{KIND_LABEL[item.component.kind]}{item.component.model ? ` · ${item.component.model}` : ''}
					· {RELATION_LABEL[item.component.relation]}
				</span>
				{#if item.rig}<span class="meta">In {item.rig.rig_label} since {formatDay(item.rig.from_on)}</span>{/if}
				{#if item.next_due}<span class="meta">Next due you entered: {formatDay(item.next_due)}</span>{/if}
			</li>
		{/each}
	</ul>
{/if}

{#if !data.archived}
	<h2>Rigs</h2>
	<p class="hint">A rig is a dated assembly. Moving a component keeps where it was before.</p>
	{#if errorFor('archiveRig')}<p class="form-error" role="alert">{errorFor('archiveRig')}</p>{/if}
	{#if !data.rigs.ok}
		<p class="form-error" role="alert">{gearMessage(data.rigs.reason)}</p>
	{:else}
		<ul class="results" aria-label="Rigs">
			{#each data.rigs.items as rig (rig.id)}
				<li>
					<span class="title">{rig.label}{rig.archived ? ' (archived)' : ''}</span>
					<span class="meta">
						{rig.components.length
							? rig.components.map((c) => c.label).join(', ')
							: 'No components'}
					</span>
					<form method="POST" action="?/archiveRig">
						<input type="hidden" name="id" value={rig.id} />
						<input type="hidden" name="version" value={rig.version} />
						<input type="hidden" name="archived" value={rig.archived ? 'false' : 'true'} />
						<button class="button secondary small" type="submit"
							>{rig.archived ? 'Restore' : 'Archive'}</button
						>
					</form>
				</li>
			{:else}
				<li><span class="meta">No rigs yet.</span></li>
			{/each}
		</ul>
	{/if}
	<form method="POST" action="?/rig" class="form inline">
		{#if errorFor('rig')}<p class="form-error" role="alert">{errorFor('rig')}</p>{/if}
		{#if page.url.searchParams.get('rig')}<p role="status">Rig added.</p>{/if}
		<input type="hidden" name="client_key" value={data.rigKey} />
		<div class="field">
			<label for="rig-label">New rig name</label>
			<input id="rig-label" name="label" maxlength="80" />
		</div>
		<div class="form-actions"><button class="button secondary" type="submit">Add rig</button></div>
	</form>
{/if}

<style>
	.actions {
		display: flex;
		flex-wrap: wrap;
		gap: 1rem;
		align-items: center;
	}

	.title {
		font-weight: 600;
		flex-basis: 100%;
	}

	.meta {
		color: var(--muted);
		flex-basis: 100%;
	}

	.small {
		min-height: 36px;
		padding: 0.25rem 0.75rem;
	}
</style>
