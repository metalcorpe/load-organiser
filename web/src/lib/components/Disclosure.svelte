<script lang="ts">
	import type { Snippet } from 'svelte';

	/**
	 * A <details> whose initial `open` is rendered by the server (so it works without
	 * JavaScript) and then left to the person.
	 *
	 * - Inlined in a larger component, Svelte would set `open` again in the same update as
	 *   that component's other dynamic parts (a wing loading note appearing, say), folding a
	 *   section that had just been opened. Here it depends on this component alone.
	 * - On hydration it keeps what the person did before the page became interactive: the
	 *   server-rendered element is read (by its id) before Svelte applies `open`.
	 */
	let {
		open = false,
		class: className = '',
		summaryClass = undefined,
		summary,
		children
	}: {
		open?: boolean;
		class?: string;
		summaryClass?: string;
		summary: Snippet;
		children: Snippet;
	} = $props();
	const id = $props.id();
	// Read once: the element already in the page (hydration) wins over the prop.
	// svelte-ignore state_referenced_locally
	const initial = (() => {
		if (typeof document === 'undefined') return open;
		const rendered = document.getElementById(id);
		return rendered instanceof HTMLDetailsElement ? rendered.open : open;
	})();
</script>

<details {id} class={className} open={initial}>
	<summary class={summaryClass}>{@render summary()}</summary>
	{@render children()}
</details>
