<script lang="ts">
	/**
	 * Stands in for a tab's page while its data loads (the layout shows it after a short grace
	 * period, so a quick switch never flashes it). Decorative: the layout marks main busy and
	 * NavigationStatus announces the loading, so it is hidden from assistive technology.
	 */
	let { label }: { label: string } = $props();
</script>

<div class="skeleton" aria-hidden="true" data-testid="tab-skeleton" data-tab={label}>
	<div class="bar title"></div>
	<div class="bar line"></div>
	<div class="bar line short"></div>
	{#each [0, 1, 2] as row (row)}
		<div class="block">
			<div class="bar"></div>
			<div class="bar short"></div>
		</div>
	{/each}
</div>

<style>
	.skeleton {
		display: grid;
		gap: 0.75rem;
		padding-top: 0.5rem;
	}

	.bar {
		height: 0.9rem;
		border-radius: 6px;
		background: var(--surface-soft);
	}

	.title {
		width: 45%;
		height: 2rem;
		margin-bottom: 0.25rem;
	}

	.line {
		width: 85%;
	}

	.short {
		width: 55%;
	}

	.block {
		display: grid;
		gap: 0.6rem;
		padding: 1rem;
		border: 1px solid transparent;
		border-radius: var(--radius);
		background: var(--surface);
		box-shadow: var(--shadow-card);
	}

	/* A slow pulse, not a sweep; none for those who ask for less motion. */
	@media (prefers-reduced-motion: no-preference) {
		.bar {
			animation: pulse 1.4s ease-in-out infinite;
		}
	}

	@keyframes pulse {
		50% {
			opacity: 0.55;
		}
	}
</style>
