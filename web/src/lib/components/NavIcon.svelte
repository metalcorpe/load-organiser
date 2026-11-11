<script lang="ts">
	import type { NavIcon } from '#lib/navigation.ts';

	let { name }: { name: NavIcon } = $props();
</script>

<svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true" focusable="false">
	{#if name === 'explore'}
		<circle cx="12" cy="12" r="9" />
		<path d="m15.5 8.5-2 5-5 2 2-5z" />
	{:else if name === 'logbook'}
		<path d="M5 4h11a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z" />
		<path d="M5 17a3 3 0 0 1 3-3h11" />
	{:else if name === 'friends'}
		<circle cx="9" cy="8" r="3" />
		<circle cx="17" cy="9" r="2.5" />
		<path d="M3 20a6 6 0 0 1 12 0M14 20a4 4 0 0 1 7 0" />
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
