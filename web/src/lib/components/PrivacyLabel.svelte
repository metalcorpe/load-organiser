<script lang="ts">
	/** Who can see this page's content. Private records, or the audience of a shared copy. */
	let { text = 'Private — only you can see this' }: { text?: string } = $props();
</script>

<p class="privacy">
	<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
		<rect x="5" y="11" width="14" height="10" rx="2" />
		<path d="M8 11V8a4 4 0 0 1 8 0v3" />
	</svg>
	{text}
</p>

<style>
	.privacy {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
		margin: -0.25rem 0 0.75rem;
		padding: 0.2rem 0.65rem;
		border-radius: 999px;
		background: var(--surface-soft);
		color: var(--muted);
		font-size: 0.85rem;
		font-weight: 600;
	}

	svg {
		fill: none;
		stroke: currentColor;
		stroke-width: 2;
		stroke-linecap: round;
	}
</style>
