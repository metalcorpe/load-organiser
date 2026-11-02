<script lang="ts">
	import type { NavIcon } from '#lib/navigation.ts';

	let { name }: { name: NavIcon } = $props();
</script>

<svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true" focusable="false">
	{#if name === 'discover'}
		<circle cx="11" cy="11" r="7" />
		<path d="m20 20-4-4" />
	{:else if name === 'activity'}
		<path d="M3 12h4l3-8 4 16 3-8h4" />
	{:else if name === 'add'}
		<circle cx="12" cy="12" r="9" />
		<path d="M12 8v8M8 12h8" />
	{:else if name === 'records'}
		<path d="M5 4h11l3 3v13H5z" />
		<path d="M9 10h6M9 14h6" />
	{:else}
		<circle cx="12" cy="8" r="4" />
		<path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6" />
	{/if}
</svg>

<style>
	svg {
		fill: none;
		stroke: currentColor;
		stroke-width: 1.8;
		stroke-linecap: round;
		stroke-linejoin: round;
		flex: none;
	}
</style>
