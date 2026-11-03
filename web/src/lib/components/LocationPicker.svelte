<script lang="ts">
	import { COUNTRY_OPTIONS, countryName } from '#lib/countries.ts';
	import type { PlaceOut, VenueOut } from '#lib/contracts/index.ts';

	/**
	 * Choose where a jump happened: a listed dropzone or one of the viewer's private
	 * places, or add a private place on the spot (#153). Choosing navigates to
	 * `{base}?venue=…` / `{base}?place=…`; nothing typed in a jump form is lost
	 * because the form is shown only after this step.
	 */
	let {
		base,
		q,
		matches,
		places,
		error,
		keep = {}
	}: {
		base: string;
		q: string;
		matches: { ok: true; items: VenueOut[] } | { ok: false } | null;
		places: PlaceOut[];
		error?: string;
		keep?: Record<string, string>;
	} = $props();
</script>

<section aria-labelledby="pick-dz">
	<h2 id="pick-dz">Where did you jump?</h2>
	<form method="GET" action={base} class="form inline" role="search">
		{#each Object.entries(keep) as [name, value] (name)}
			<input type="hidden" {name} {value} />
		{/each}
		<div class="field">
			<label for="q">Search listed dropzones</label>
			<input id="q" name="q" type="search" maxlength="80" defaultValue={q} autocomplete="off" />
		</div>
		<div class="form-actions"><button class="button secondary" type="submit">Search</button></div>
	</form>
	{#if matches}
		{#if !matches.ok}
			<p class="form-error" role="alert">Search is unavailable right now. Use a private place instead.</p>
		{:else if matches.items.length === 0}
			<p class="hint">No listed dropzone matches “{q}”. Add it as a private place below.</p>
		{:else}
			<ul class="results" aria-label="Matching dropzones">
				{#each matches.items as venue (venue.id)}
					<li>
						<a class="title" href="{base}?venue={venue.id}">{venue.name}</a>
						<span class="meta"
							>{venue.locality ? `${venue.locality}, ` : ''}{countryName(venue.country)}{venue.status ===
							'closed'
								? ' · closed'
								: ''}</span
						>
					</li>
				{/each}
			</ul>
		{/if}
	{/if}

	{#if places.length > 0}
		<h3>Your private places</h3>
		<ul class="results" aria-label="Your private places">
			{#each places as place (place.id)}
				<li>
					<a class="title" href="{base}?place={place.id}">{place.name}</a>
					<span class="meta">{countryName(place.country)} · private</span>
				</li>
			{/each}
		</ul>
	{/if}

	<h3>Not listed?</h3>
	<p class="hint">
		Add a private place: only you see it, and you can log the jump straight away. Suggesting it
		for the public directory is a separate step.
	</p>
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
</section>
