<script lang="ts">
	import { navigating } from '$app/state';

	/**
	 * Only a navigation still running after SLOW_MS shows (and announces) "Loading…": a quick
	 * one would flash the pill for a few frames. Tab switches answer at once anyway (AppNav moves
	 * the pill, the layout shows a skeleton after 150ms and marks main busy).
	 */
	const SLOW_MS = 400;
	let slow = $state(false);

	$effect(() => {
		if (!navigating.to) {
			slow = false;
			return;
		}
		const timer = setTimeout(() => (slow = true), SLOW_MS);
		return () => clearTimeout(timer);
	});
</script>

<!-- Polite announcement + visible text: loading is never conveyed by colour alone. -->
<div class="status" role="status" aria-live="polite">
	{#if navigating.to && slow}
		<span class="pill" data-testid="navigation-loading">Loading…</span>
	{/if}
</div>

<style>
	.status {
		position: fixed;
		top: 0.5rem;
		left: 50%;
		transform: translateX(-50%);
		z-index: 20;
		pointer-events: none;
	}

	.pill {
		display: inline-block;
		padding: 0.25rem 0.75rem;
		border-radius: 999px;
		background: var(--fg);
		color: var(--bg);
		font-size: 0.85rem;
		font-weight: 600;
	}
</style>
