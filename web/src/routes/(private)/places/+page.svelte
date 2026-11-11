<script lang="ts">
	import PrivacyLabel from '#lib/components/PrivacyLabel.svelte';
	import Notice from '#lib/components/Notice.svelte';
	import { COUNTRY_OPTIONS, countryName } from '#lib/countries.ts';
	import { directoryMessage } from '#lib/directory-messages.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();

	const errorFor = (name: string, id?: string) =>
		form && form.form === name && 'error' in form && (!id || ('id' in form && form.id === id))
			? directoryMessage(form.error)
			: undefined;
</script>

<svelte:head>
	<title>Private places · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<h1>Private places</h1>
<PrivacyLabel />
<p class="lede">
	Places only you can see. Use one when a dropzone is not listed, so logging never waits for a
	listing. Adding a place does not publish it, suggest it or notify anyone.
</p>

<section class="card" aria-labelledby="add-heading">
	<h2 id="add-heading">Add a place</h2>
	{#if !data.emailVerified}
		<p class="hint">Confirm your email address on your <a href="/profile">profile</a> to save places.</p>
	{/if}
	<form method="POST" action="?/create" class="form" novalidate>
		{#if errorFor('create')}
			<p class="form-error" role="alert">{errorFor('create')}</p>
		{:else if form?.form === 'create' && 'done' in form}
			<p role="status">Place saved.</p>
		{/if}
		<div class="field">
			<label for="new-name">Name</label>
			<input id="new-name" name="name" required maxlength="120" autocomplete="off" />
		</div>
		<div class="field">
			<label for="new-country">Country</label>
			<select id="new-country" name="country" required>
				<option value="">Choose a country</option>
				{#each COUNTRY_OPTIONS as option (option.code)}
					<option value={option.code}>{option.name}</option>
				{/each}
			</select>
		</div>
		<div class="form-actions"><button class="button" type="submit">Save place</button></div>
	</form>
</section>

{#if !data.places.ok}
	<p class="form-error" role="alert">{directoryMessage(data.places.reason)}</p>
{:else if data.places.items.length === 0}
	<p>You have no private places yet.</p>
{:else}
	<ul class="places" aria-label="Your private places">
		{#each data.places.items as place (place.id)}
			<li class="card" data-testid="place">
				<h2>{place.name}</h2>
				<p class="meta">
					{countryName(place.country)}
					{#if place.venue}
						· linked to <a href="/dz/{place.venue.id}">{place.venue.name}</a>
						{#if place.venue.status === 'closed'}(closed){/if}
					{:else}
						· not linked to a listed dropzone
					{/if}
				</p>

				<details>
					<summary>Edit</summary>
					<form method="POST" action="?/rename" class="form" novalidate>
						{#if errorFor('rename', place.id)}<p class="form-error" role="alert">{errorFor('rename', place.id)}</p>{/if}
						<input type="hidden" name="id" value={place.id} />
						<div class="field">
							<label for="name-{place.id}">Name</label>
							<input id="name-{place.id}" name="name" maxlength="120" defaultValue={place.name} />
						</div>
						<div class="field">
							<label for="country-{place.id}">Country</label>
							<select id="country-{place.id}" name="country">
								{#each COUNTRY_OPTIONS as option (option.code)}
									<option value={option.code} selected={option.code === place.country}>{option.name}</option>
								{/each}
							</select>
						</div>
						<div class="form-actions"><button class="button secondary" type="submit">Save changes</button></div>
					</form>
				</details>

				<div class="actions">
					{#if place.venue}
						<form method="POST" action="?/unlink">
							<input type="hidden" name="id" value={place.id} />
							<button class="button secondary" type="submit">Unlink</button>
						</form>
					{:else}
						<a class="button secondary" href="/places?link={place.id}&q={encodeURIComponent(place.name)}">Link to a listed dropzone</a>
					{/if}
					<form method="POST" action="?/remove">
						<input type="hidden" name="id" value={place.id} />
						<button class="button secondary" type="submit">Remove</button>
					</form>
				</div>
				{#if errorFor('link', place.id) || errorFor('unlink', place.id) || errorFor('remove', place.id)}
					<p class="form-error" role="alert">
						{errorFor('link', place.id) ?? errorFor('unlink', place.id) ?? errorFor('remove', place.id)}
					</p>
				{/if}

				{#if data.linking === place.id}
					<section aria-label="Find a listed dropzone">
						<form method="GET" class="form" role="search">
							<input type="hidden" name="link" value={place.id} />
							<div class="field">
								<label for="link-q">Search listed dropzones</label>
								<input id="link-q" name="q" type="search" maxlength="80" defaultValue={data.q} />
							</div>
							<div class="form-actions"><button class="button secondary" type="submit">Search</button></div>
						</form>
						{#if data.matches && !data.matches.ok}
							<p class="form-error" role="alert">{directoryMessage(data.matches.reason)}</p>
						{:else if data.matches && data.matches.items.length === 0}
							<p>No listed dropzone matches. Your place stays private and usable as it is.</p>
						{:else if data.matches}
							<ul class="matches">
								{#each data.matches.items as venue (venue.id)}
									<li>
										<form method="POST" action="?/link">
											<input type="hidden" name="id" value={place.id} />
											<input type="hidden" name="venue_id" value={venue.id} />
											<button class="button secondary" type="submit">
												Link to {venue.name}, {countryName(venue.country)}
											</button>
										</form>
									</li>
								{/each}
							</ul>
						{/if}
					</section>
				{/if}
			</li>
		{/each}
	</ul>
{/if}

<p class="hint">Linking only affects your own records. It does not tell the dropzone or anyone else.</p>

<style>
	.card {
		border: 1px solid var(--border);
		border-radius: var(--radius);
		background: var(--surface);
		padding: 1rem;
		margin: 1rem 0;
	}

	h2 {
		font-size: 1.1rem;
		margin: 0 0 0.25rem;
	}

	.places,
	.matches {
		list-style: none;
		padding: 0;
		margin: 0;
	}

	.meta {
		color: var(--muted);
		margin: 0 0 0.5rem;
	}

	.actions {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
		margin-top: 0.75rem;
	}

	.matches li {
		margin: 0.5rem 0;
	}
</style>
