<script lang="ts">
	import type { Snippet } from 'svelte';

	/**
	 * A <details> whose initial `open` is rendered by the server (so it works without
	 * JavaScript) and then left to the person. In its own component, the `open` assignment
	 * runs only when this prop changes: inlined in a larger form, Svelte groups it with the
	 * form's other dynamic parts and would set it again on any of their updates (a wing
	 * loading note appearing, say), folding a section that had just been opened.
	 */
	let {
		open = false,
		class: className = '',
		summary,
		children
	}: { open?: boolean; class?: string; summary: Snippet; children: Snippet } = $props();
</script>

<details class={className} {open}>
	<summary>{@render summary()}</summary>
	{@render children()}
</details>
