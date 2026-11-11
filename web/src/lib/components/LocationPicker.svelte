<script lang="ts">
	import { goto } from '$app/navigation';
	import { COUNTRY_OPTIONS, countryName } from '#lib/countries.ts';
	import type { PlaceOut, VenueOut } from '#lib/contracts/index.ts';

	/**
	 * Choose where a jump happened: a recent location, a listed dropzone or one of the
	 * viewer's private places, or add a private place on the spot (#153). Choosing
	 * navigates to `{base}?venue=…` / `{base}?place=…`; nothing typed in a jump form is
	 * lost because the form is shown only after this step.
	 */
	let {
		base,
		q,
		matches,
		places,
		recent = [],
		error,
		keep = {}
	}: {
		base: string;
		q: string;
		matches: { ok: true; items: VenueOut[] } | { ok: false } | null;
		places: PlaceOut[];
		recent?: { kind: 'venue' | 'place'; id: string; name: string; country: string | null }[];
		error?: string;
		keep?: Record<string, string>;
	} = $props();

	function href(kind: 'venue' | 'place', id: string): string {
		const params = new URLSearchParams(keep);
		params.set(kind, id);
		return `${base}?${params}`;
	}

	// A first-time user has nothing to pick from yet, so the private-place form starts open.
	const newcomer = $derived(recent.length === 0 && places.length === 0);
	const recentIds = $derived(new Set(recent.map((r) => r.id)));
	const otherPlaces = $derived(places.filter((p) => !recentIds.has(p.id)));

	// Search as you type, on top of the plain GET form (which still works without JS).
	let timer: ReturnType<typeof setTimeout> | undefined;
	// A pending search must never fire after a choice or a submit: it would navigate back.
	const cancel = () => clearTimeout(timer);
	$effect(() => cancel);
	function typed(event: Event & { currentTarget: HTMLInputElement }) {
		const value = event.currentTarget.value.trim();
		clearTimeout(timer);
		if (value.length === 1) return;
		timer = setTimeout(() => {
			const params = new URLSearchParams(keep);
			if (value) params.set('q', value);
			goto(`${base}?${params}`, { replace: true, reset: false });
		}, 300);
	}
</script>

<section aria-labelledby="pick-dz">
	<h2 id="pick-dz">Where did you jump?</h2>

	{#if recent.length > 0}
		<h3 class="sub">Recent</h3>
		<ul class="picks" aria-label="Recent places">
			{#each recent as loc (loc.kind + loc.id)}
				<li>
					<a class="pick" href={href(loc.kind, loc.id)} onclick={cancel}>
						<span class="pick-name">{loc.name}</span>
						<span class="pick-meta"
							>{loc.country ? countryName(loc.country) : ''}{loc.kind === 'place'
								? ' · private'
								: ''}</span
						>
					</a>
				</li>
			{/each}
		</ul>
	{/if}

	<form method="GET" action={base} class="search" role="search" onsubmit={cancel}>
		{#each Object.entries(keep) as [name, value] (name)}
			<input type="hidden" {name} {value} />
		{/each}
		<label for="q">Search listed dropzones</label>
		<div class="search-row">
			<input
				id="q"
				name="q"
				type="search"
				maxlength="80"
				defaultValue={q}
				autocomplete="off"
				placeholder="Dropzone or town"
				oninput={typed}
			/>
			<button class="button secondary" type="submit">Search</button>
		</div>
	</form>

	<div aria-live="polite">
		{#if matches}
			{#if !matches.ok}
				<p class="form-error" role="alert">Search is unavailable right now. Use a private place instead.</p>
			{:else if matches.items.length === 0}
				<p class="hint">No listed dropzone matches “{q}”. Add it as a private place below.</p>
			{:else}
				<ul class="picks" aria-label="Matching dropzones">
					{#each matches.items as venue (venue.id)}
						<li>
							<a class="pick" href={href('venue', venue.id)} onclick={cancel}>
								<span class="pick-name">{venue.name}</span>
								<span class="pick-meta"
									>{venue.locality ? `${venue.locality}, ` : ''}{countryName(venue.country)}{venue.status ===
									'closed'
										? ' · closed'
										: ''}</span
								>
							</a>
						</li>
					{/each}
				</ul>
			{/if}
		{/if}
	</div>

	{#if otherPlaces.length > 0}
		<h3>Your private places</h3>
		<ul class="picks" aria-label="Your private places">
			{#each otherPlaces as place (place.id)}
				<li>
					<a class="pick" href={href('place', place.id)} onclick={cancel}>
						<span class="pick-name">{place.name}</span>
						<span class="pick-meta">{countryName(place.country)} · private</span>
					</a>
				</li>
			{/each}
		</ul>
	{/if}

	<details class="new-place" open={newcomer || Boolean(error)}>
		<summary class="disclosure">Not listed? Add a private place</summary>
		<p class="hint">Only you see it, and you can log the jump straight away.</p>
		<form method="POST" action="?/place" class="form">
			{#if error}<p class="form-error" role="alert">{error}</p>{/if}
			<div class="pair">
				<div class="field">
					<label for="place-name">Place name</label>
					<input id="place-name" name="name" maxlength="120" required />
				</div>
				<div class="field">
					<label for="place-country">Country</label>
					<select id="place-country" name="country" required>
						<option value="">Choose a country</option>
						{#each COUNTRY_OPTIONS as option (option.code)}
							<option value={option.code}>{option.name}</option>
						{/each}
					</select>
				</div>
			</div>
			<div class="form-actions"><button class="button secondary" type="submit">Use this place</button></div>
		</form>
	</details>
</section>

<style>
	.search {
		display: grid;
		gap: 0.3rem;
		margin: 0.75rem 0;
	}

	.search label {
		font-weight: 650;
	}

	.search-row {
		display: flex;
		gap: 0.5rem;
	}

	.search-row input {
		flex: 1;
		min-width: 0;
		min-height: 44px;
		padding: 0.5rem 0.75rem;
		border: 1px solid var(--border);
		border-radius: 9px;
		background: var(--surface);
		color: var(--fg);
		font: inherit;
	}

	.picks {
		display: grid;
		gap: 0.5rem;
		list-style: none;
		padding: 0;
		margin: 0.5rem 0 1rem;
	}

	/* Each choice is one tap target. */
	.pick {
		display: grid;
		gap: 0.1rem;
		min-height: 44px;
		padding: 0.65rem 0.85rem;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		background: var(--surface);
		color: var(--fg);
		text-decoration: none;
	}

	.pick:hover {
		border-color: var(--accent);
	}

	.pick-name {
		font-weight: 650;
		overflow-wrap: anywhere;
	}

	.pick-meta {
		color: var(--muted);
		font-size: 0.9rem;
	}

	.new-place {
		margin-top: 1rem;
	}

	.sub {
		margin: 0.75rem 0 0;
		font-size: 1rem;
		color: var(--muted);
	}

	.pair {
		display: grid;
		gap: 1rem;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 12rem), 1fr));
	}
</style>
