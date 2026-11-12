<script lang="ts">
	/** Progress toward the next USPA licence (USPA SIM 3-1) from the jumper's own entries. Shown on History. */
	import { OTHER_REQUIREMENTS, progressLines, type ProgressIn } from '#lib/licence-progress.ts';

	let {
		progress,
		priorInconsistent = false
	}: { progress: ProgressIn; priorInconsistent?: boolean } = $props();
	const lines = $derived(progressLines(progress));
	const id = $props.id();
</script>

<section class="progress" id="next-licence" aria-labelledby="{id}-title">
	<h2 id="{id}-title">Next licence</h2>
	{#if lines.highest}
		<p>{lines.highest}</p>
	{:else}
		<p><strong>{lines.toward}</strong> (USPA SIM 3-1)</p>
		<ul>
			<li>{lines.jumps}</li>
			{#if lines.freefall}<li>{lines.freefall}</li>{/if}
		</ul>
		{#if lines.missing}<p>{lines.missing}</p>{/if}
		{#if lines.prior}<p>{lines.prior}</p>{/if}
		{#if priorInconsistent}
			<p>Your prior jump count does not match your entries yet, so only your entries count.</p>
		{/if}
		<p class="hint">{OTHER_REQUIREMENTS}</p>
	{/if}
</section>

<style>
	.progress {
		margin: 0.75rem 0 1rem;
		padding: 0.75rem 1rem;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		background: var(--surface);
	}

	h2 {
		font-size: 1rem;
		margin: 0 0 0.25rem;
	}

	p {
		margin: 0.25rem 0 0;
	}

	ul {
		margin: 0.25rem 0 0;
		padding-left: 1.1rem;
	}
</style>
