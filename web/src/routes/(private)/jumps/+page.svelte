<script lang="ts">
	import { JUMP_TYPE_LABEL, jumpMessage } from '#lib/jumps.ts';
	import { formatDay } from '#lib/listings.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
</script>

<svelte:head>
	<title>Logbook · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<p><a href="/records">Records</a></p>
<h1>Logbook</h1>
<p class="lede">Your private jump entries. Only you can see them.</p>
<p class="actions"><a class="button" href="/jumps/new">Add jump</a></p>

{#if !data.page.ok}
	<p class="form-error" role="alert">{jumpMessage(data.page.reason)}</p>
{:else}
	<p role="status">
		<strong>{data.page.recorded_total.toLocaleString('en-GB')}</strong>
		{data.page.recorded_total === 1 ? 'jump' : 'jumps'} recorded here. This counts the entries you
		logged, not your lifetime total.
	</p>
	<p><a href="/history">History and totals</a></p>
	{#if data.page.items.length === 0}
		<p class="hint">
			{data.older ? 'No older entries.' : 'No jumps yet. Add your first one; no gear or history is needed.'}
		</p>
	{:else}
		<ul class="results" aria-label="Jumps">
			{#each data.page.items as jump (jump.id)}
				<li>
					<a class="title" href="/jumps/{jump.id}"
						>{formatDay(jump.jumped_on)}{jump.jump_number ? ` · #${jump.jump_number}` : ''}</a
					>
					<span class="meta"
						>{JUMP_TYPE_LABEL[jump.jump_type]} · {jump.location.name ?? 'Dropzone no longer listed'}{jump
							.location.kind === 'place'
							? ' (private place)'
							: ''}</span
					>
					{#if jump.components.length > 0}
						<span class="meta">Gear: {jump.components.map((c) => c.label).join(', ')}</span>
					{/if}
				</li>
			{/each}
		</ul>
	{/if}
	<p class="actions">
		{#if data.older}<a href="/jumps">Newest</a>{/if}
		{#if data.page.next_cursor}
			<a href="/jumps?cursor={encodeURIComponent(data.page.next_cursor)}">Older jumps</a>
		{/if}
	</p>
{/if}
