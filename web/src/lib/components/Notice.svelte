<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		title,
		tone = 'info',
		children
	}: { title: string; tone?: 'info' | 'ok' | 'warn' | 'bad'; children: Snippet } = $props();
	const id = $props.id();
</script>

<section class="notice {tone}" aria-labelledby="{id}-title">
	<h2 id="{id}-title">{title}</h2>
	{@render children()}
</section>

<style>
	.notice {
		border: 1px solid var(--border);
		border-radius: var(--radius);
		background: var(--surface-soft);
		padding: 1rem;
		margin: 1rem 0;
	}

	h2 {
		font-size: 1.05rem;
		margin: 0 0 0.35rem;
	}

	.notice :global(p) {
		margin: 0.35rem 0;
	}

	.warn {
		background: var(--warn-bg);
		border-color: var(--warn-border);
		color: var(--warn-fg);
	}

	.ok {
		background: var(--ok-bg);
		color: var(--ok-fg);
	}

	.bad {
		background: var(--bad-bg);
		color: var(--bad-fg);
	}
</style>
