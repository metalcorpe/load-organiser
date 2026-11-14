<script lang="ts">
	import { browser } from '$app/env';
	import { onMount, tick } from 'svelte';
	import type { VenuePointOut } from '#lib/contracts/index.ts';
	import { countryName } from '#lib/countries.ts';
	import { mapChosen, rememberMapChoice } from '#lib/dz-map.ts';
	import type { MapPoint } from '#lib/leaflet-map.ts';

	/**
	 * The Map view of the directory. Nothing third-party loads until the visitor presses "Show
	 * map": then Leaflet (a separate chunk) draws OpenStreetMap tiles, and the choice is kept for
	 * this browser session. Without JavaScript only the note pointing to the list renders.
	 */
	let { points, listHref }: { points: VenuePointOut[]; listHref: string } = $props();

	type Phase = 'server' | 'ask' | 'loading' | 'shown' | 'failed';
	let phase: Phase = $state('server');
	let container: HTMLDivElement | undefined = $state();
	let leaflet: typeof import('#lib/leaflet-map.ts') | undefined = $state.raw();

	const session = () => (browser ? window.sessionStorage : undefined);
	const mapPoints: MapPoint[] = $derived(
		points.map((p) => ({
			id: p.id,
			name: p.name,
			place: p.locality ? `${p.locality}, ${countryName(p.country)}` : countryName(p.country),
			lat: p.lat,
			lon: p.lon,
			closed: p.closed
		}))
	);
	const label = $derived(
		`Map of ${points.length.toLocaleString('en-GB')} ${points.length === 1 ? 'dropzone' : 'dropzones'}`
	);

	async function load(focus: boolean) {
		phase = 'loading';
		try {
			if (browser) leaflet = await import('#lib/leaflet-map.ts');
			phase = 'shown';
			await tick();
			if (focus) container?.focus();
		} catch {
			phase = 'failed';
		}
	}

	function show() {
		rememberMapChoice(session);
		void load(true);
	}

	onMount(() => {
		if (mapChosen(session)) void load(false);
		else phase = 'ask';
	});

	// Drawn once the library is here, and again when the filters change the points.
	$effect(() => {
		if (phase !== 'shown' || !container || !leaflet) return;
		const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
		const handle = leaflet.createDropzoneMap(container, mapPoints, { reducedMotion });
		return () => handle.destroy();
	});
</script>

<section class="map-view" aria-labelledby="map-heading">
	<h2 id="map-heading" class="visually-hidden">Map</h2>
	<p class="hint">
		The map shows the dropzones of the list that have coordinates. The
		<a href={listHref}>list</a> is the accessible equivalent, with the same dropzones and search.
	</p>

	<noscript>
		<p class="notice" data-testid="map-needs-js">
			The map needs JavaScript. <a href={listHref}>Use the list</a>: it has the same dropzones.
		</p>
	</noscript>

	{#if phase === 'ask'}
		<div class="consent">
			<p>
				Map images come from the OpenStreetMap tile servers. Showing the map sends them your IP
				address and this site's address, as loading any image from another site does. Nothing is
				requested until you choose. <a href="/privacy#account">Privacy</a>
			</p>
			<button class="button" type="button" onclick={show}>Show map</button>
		</div>
	{/if}

	{#if phase === 'loading' || phase === 'shown'}
		<div
			class="map"
			bind:this={container}
			role="region"
			aria-label={label}
			aria-busy={phase === 'loading'}
			tabindex="-1"
			data-testid="dz-map"
		></div>
		<ul class="legend" aria-label="Key">
			<li><span class="swatch listed" aria-hidden="true"></span>Dropzone</li>
			<li><span class="swatch closed" aria-hidden="true"></span>Closed</li>
			<li><span class="swatch cluster" aria-hidden="true">3</span>Several: zoom in</li>
		</ul>
		<p class="hint">
			Use the arrow keys to move the map and + or − to zoom. Tab moves through the markers; Enter
			opens one.
		</p>
	{/if}

	{#if phase === 'failed'}
		<p class="form-error" role="alert">
			The map could not be loaded. <a href={listHref}>The list</a> has the same dropzones.
		</p>
	{/if}
</section>

<style>
	.map-view {
		margin: 0 0 1rem;
	}

	.hint {
		max-width: var(--measure);
		color: var(--muted);
	}

	.notice,
	.consent {
		max-width: var(--measure);
		padding: 1rem;
		border-radius: var(--radius);
		background: var(--surface);
		box-shadow: 0 0 0 1px var(--border);
	}

	.consent p {
		margin: 0 0 0.75rem;
	}

	.map {
		height: min(70vh, 40rem);
		min-height: 20rem;
		border-radius: var(--radius);
		box-shadow: 0 0 0 1px var(--border);
		/* Leaflet sets its own background and font; keep the page's. */
		background: var(--surface-soft);
		font-family: var(--font-body);
	}

	.map:focus-visible {
		outline: 3px solid var(--focus);
		outline-offset: 2px;
	}

	.legend {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem 1.25rem;
		margin: 0.75rem 0 0;
		padding: 0;
		list-style: none;
		color: var(--muted);
		font-size: 0.9rem;
	}

	.legend li {
		display: inline-flex;
		align-items: center;
		gap: 0.4rem;
	}

	/* Markers and clusters sit on the map tiles, which stay the same in both themes, so their
	   colours are fixed rather than theme tokens. The legend repeats them. */
	.swatch,
	.map :global(.dz-marker) {
		display: inline-block;
		width: 18px;
		height: 18px;
		border-radius: 50%;
		border: 2px solid #ffffff;
		background: #c4461c;
		box-shadow: 0 0 0 1px rgb(14 34 56 / 0.6);
	}

	.swatch.closed,
	.map :global(.dz-marker-closed) {
		background: #6b7785;
		border-style: dotted;
	}

	.swatch.cluster,
	.map :global(.dz-cluster) {
		display: inline-grid;
		place-items: center;
		border-radius: 50%;
		border: 2px solid #ffffff;
		background: #0e2238;
		color: #ffffff;
		font-weight: 700;
		font-size: 0.85rem;
		box-shadow: 0 0 0 1px rgb(14 34 56 / 0.6);
	}

	.swatch.cluster {
		width: 26px;
		height: 26px;
		font-size: 0.75rem;
	}

	.map :global(.dz-marker:focus-visible),
	.map :global(.dz-cluster:focus-visible) {
		outline: 3px solid var(--focus);
		outline-offset: 2px;
	}

	/* Popups belong to the page rather than the tiles: theme colours, readable in both. */
	.map :global(.leaflet-popup-content-wrapper),
	.map :global(.leaflet-popup-tip) {
		background: var(--surface);
		color: var(--fg);
		box-shadow: 0 0 0 1px var(--border), 0 3px 14px rgb(0 0 0 / 0.3);
	}

	.map :global(.leaflet-popup-content) {
		margin: 0.75rem 1rem;
		font-size: 0.95rem;
		line-height: 1.4;
	}

	.map :global(.dz-popup p) {
		margin: 0;
	}

	.map :global(.dz-popup-name a) {
		color: var(--accent);
		font-weight: 650;
	}

	.map :global(.dz-popup-place),
	.map :global(.dz-popup-closed) {
		color: var(--muted);
	}

	.map :global(a.leaflet-popup-close-button) {
		color: var(--muted);
	}
</style>
