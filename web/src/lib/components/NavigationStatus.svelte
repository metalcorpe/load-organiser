<script lang="ts">
	import { navigating } from '$app/state';
</script>

<!-- Polite announcement + visible text: loading is never conveyed by colour alone. -->
<div class="status" role="status" aria-live="polite">
	{#if navigating.to}
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
