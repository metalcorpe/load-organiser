<script lang="ts">
	/** The listing type's icon, so the type never depends on its colour alone. Decorative. */
	let { category, size = 15 }: { category: string; size?: number } = $props();
</script>

<svg
	width={size}
	height={size}
	viewBox="0 0 24 24"
	fill="none"
	stroke="currentColor"
	stroke-width="2"
	stroke-linecap="round"
	stroke-linejoin="round"
	aria-hidden="true"
>
	{#if category === 'boogie'}
		<path d="M2 13l8-2 4-8 2 1-2 7 7-1 1 2-7 3-2 6-2-1 1-5-8 1z" />
	{:else if category === 'camp'}
		<path d="M3 20 12 4l9 16zM12 20v-6M9 20l3-6 3 6" />
	{:else if category === 'course'}
		<path d="m2 9 10-5 10 5-10 5zM6 11v5c3 2 9 2 12 0v-5" />
	{:else}
		<path d="M5 21V4h11l-2 4 2 4H5" />
	{/if}
</svg>
