<script lang="ts">
	import { coordinatesText, formatCoordinates, osmLink } from '#lib/dz-map.ts';

	/**
	 * Where a dropzone is, in the order a visitor uses it: the place name, a map link, and the
	 * raw coordinates folded away for those who need them.
	 *
	 * - The map is a plain link: nothing from OpenStreetMap loads on this page.
	 * - The point is the listed location, as the source gives it. It is never described as an
	 *   entrance or landing area, which the data does not establish.
	 * - Copy needs JavaScript and a clipboard; without either the button is not shown and the
	 *   coordinates stay selectable text.
	 */
	let {
		place,
		latitude = null,
		longitude = null
	}: { place: string; latitude?: number | null; longitude?: number | null } = $props();

	let canCopy = $state(false);
	let copyStatus = $state('');

	$effect(() => {
		canCopy = typeof navigator !== 'undefined' && Boolean(navigator.clipboard?.writeText);
	});

	async function copy() {
		if (latitude === null || longitude === null) return;
		try {
			await navigator.clipboard.writeText(coordinatesText(latitude, longitude));
			copyStatus = 'Coordinates copied.';
		} catch {
			copyStatus = 'Could not copy. Select the coordinates above instead.';
		}
	}
</script>

<div class="location">
	<p class="place">{place}</p>
	{#if latitude !== null && longitude !== null}
		<p class="map">
			<a href={osmLink(latitude, longitude)} rel="external noopener noreferrer">View on map</a>
			<span class="hint">Opens OpenStreetMap at the listed point</span>
		</p>
		<details class="coordinates">
			<summary>Coordinates</summary>
			<p class="value">{formatCoordinates(latitude, longitude)}</p>
			{#if canCopy}
				<p class="copy">
					<button type="button" class="button secondary" onclick={copy}>Copy coordinates</button>
					<span role="status" class="hint">{copyStatus}</span>
				</p>
			{/if}
			<p class="hint">The point the listing gives for this dropzone. Ask the dropzone how to get in.</p>
		</details>
	{:else}
		<p class="hint">No map location listed.</p>
	{/if}
</div>

<style>
	.location {
		margin: -0.25rem 0 0.75rem;
	}

	.location p {
		margin: 0 0 0.35rem;
	}

	.place {
		color: var(--muted);
	}

	.map {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0 0.75rem;
	}

	/* A full-size tap target for the one location action. */
	.map a {
		display: inline-flex;
		align-items: center;
		min-height: 44px;
		font-weight: 600;
	}

	/* Padding, not flex, for the tap height: a flex summary loses its disclosure marker. */
	.coordinates summary {
		padding-block: 0.65rem;
		color: var(--muted);
		cursor: pointer;
	}

	.value {
		overflow-wrap: anywhere;
		font-variant-numeric: tabular-nums;
	}

	.copy {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.25rem 0.75rem;
	}
</style>
