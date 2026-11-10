<script lang="ts">
	import Notice from '#lib/components/Notice.svelte';
	import { countryName } from '#lib/countries.ts';
	import {
		AUDIENCE_LABEL,
		CATEGORY_LABEL,
		DISCIPLINE_LABEL,
		formatDay,
		formatPrice,
		formatRange,
		hostOf,
		languageName,
		listingMessage,
		statusLabel
	} from '#lib/listings.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();
	const item = $derived(data.item);
	const status = $derived(statusLabel(item.status, item.ended));
	const price = $derived(formatPrice(item.price_amount, item.price_currency, item.price_basis));
	const isSaved = $derived(
		form && 'saved' in form ? true : form && 'removed' in form ? false : Boolean(data.saved.savedAt)
	);
	const signedIn = $derived(Boolean(data.viewer));
	// What the source does not say, named once instead of a row of "Not stated" each.
	const unstated = $derived(
		[
			!item.disciplines.length && 'disciplines',
			!item.audience.length && 'who it is for',
			!item.prerequisites && 'prerequisites',
			!item.languages.length && 'languages',
			!price && !item.price_note && 'price'
		].filter((v): v is string => Boolean(v))
	);
	const signInToSave = $derived(
		`/sign-in?returnTo=${encodeURIComponent(`/events/${item.id}?save=1`)}`
	);
</script>

<svelte:head>
	<title>{item.title} · Discover · Load Organiser</title>
	<meta
		name="description"
		content="{CATEGORY_LABEL[item.category]} in {countryName(item.country)}, {formatRange(
			item.starts_on,
			item.ends_on
		)}. Source-backed listing; register with the organizer."
	/>
</svelte:head>

<p><a href="/">All listings</a></p>
<h1>{item.title}</h1>
<p class="lede headline">
	<span class="badge">{CATEGORY_LABEL[item.category]}</span>
	{#if status}<span class="badge status">{status}</span>{/if}
	<span>{formatRange(item.starts_on, item.ends_on)}</span>
</p>

{#if item.status === 'cancelled'}
	<Notice title="Cancelled" tone="warn">
		<p>The organizer's source says this was cancelled. Check with them about any registration.</p>
	</Notice>
{:else if item.status === 'postponed'}
	<Notice title="Postponed" tone="warn">
		<p>New dates have not been announced in the source. Check with the organizer.</p>
	</Notice>
{:else if item.ended}
	<Notice title="Ended" tone="info">
		<p>This listing has ended. It stays here so links and saved items keep working.</p>
	</Notice>
{/if}

<section class="actions" aria-label="Register or save">
	<a class="button" href={item.registration_url} rel="external noopener noreferrer nofollow">
		Open organizer registration
	</a>
	<p class="hint">
		Opens {hostOf(item.registration_url)}. Availability is not tracked here: places, registration and
		payment are with the organizer.
	</p>

	{#if form && 'error' in form}
		<p class="form-error" role="alert">{listingMessage(form.error)}</p>
	{/if}
	{#if !signedIn}
		<a class="button secondary" href={signInToSave}>Sign in to save this privately</a>
	{:else if isSaved}
		<p role="status" class="ok">Saved privately — you are not registered.</p>
		<form method="POST" action="?/unsave">
			<button class="button secondary" type="submit">Remove from saved</button>
		</form>
	{:else}
		{#if data.saveIntent}
			<p role="status">
				You signed in to save this listing. Its current status is shown above; save it if you
				still want to.
			</p>
		{/if}
		<form method="POST" action="?/save">
			<button class="button secondary" type="submit">Save privately</button>
		</form>
	{/if}
	{#if signedIn}
		<p class="hint">
			Saved items are visible only to you. <a href="/saved">Your saved listings</a> ·
			<a href="/plans?opportunity={item.id}">Plan a visit</a>
		</p>
	{/if}
</section>

{#if item.summary}
	<p class="summary">{item.summary}</p>
{/if}

<dl>
	<dt>Where</dt>
	<dd>
		<!-- One grid item: the dd is a grid, so bare text would start a new row. -->
		<span>
			{#if item.venue}
				<a href="/dz/{item.venue.id}">{item.venue.name}</a>{item.venue.closed ? ' (closed)' : ''},
			{/if}
			{#if item.location_note}{item.location_note},{/if}
			{countryName(item.country)}
		</span>
	</dd>
	<dt>Dates</dt>
	<dd>
		{formatRange(item.starts_on, item.ends_on)}
		{#if item.time_zone && item.starts_on}<span class="hint">({item.time_zone} local dates)</span>{/if}
	</dd>
	<dt>Organizer</dt>
	<dd>
		{#if item.provider}
			<a href="/organizers/{item.provider.id}">{item.provider.name}</a>
		{:else}
			<span class="hint">No longer listed</span>
		{/if}
	</dd>
	{#if price || item.price_note}
		<dt>Price</dt>
		<dd>
			{#if price}<span>{price}</span>{/if}
			{#if item.price_note}<span class="hint">{item.price_note}</span>{/if}
		</dd>
	{/if}
	{#if item.disciplines.length}
		<dt>Disciplines</dt>
		<dd>{item.disciplines.map((d) => DISCIPLINE_LABEL[d]).join(', ')}</dd>
	{/if}
	{#if item.audience.length}
		<dt>Intended for</dt>
		<dd>{item.audience.map((a) => AUDIENCE_LABEL[a]).join(', ')}</dd>
	{/if}
	{#if item.prerequisites}
		<dt>Prerequisites</dt>
		<dd>
			<span class="quote">{item.prerequisites}</span>
			<span class="hint">As stated by the source. Eligibility is decided by the organizer.</span>
		</dd>
	{/if}
	{#if item.languages.length}
		<dt>Languages</dt>
		<dd>{item.languages.map(languageName).join(', ')}</dd>
	{/if}
	<dt>Source</dt>
	<dd>
		<a href={item.source_url} rel="external noopener noreferrer nofollow">{hostOf(item.source_url)}</a>
		{#if item.source_note}<span class="hint">({item.source_note})</span>{/if}
		<span class="hint">Last checked {formatDay(item.checked_on)}</span>
	</dd>
</dl>

{#if unstated.length}
	<p class="hint unstated">
		Not stated by the source: {unstated.join(', ')}. Ask the organizer.
	</p>
{/if}



<p>
	<a href="/submit?kind=correction&target_kind=opportunity&target_id={item.id}&title={encodeURIComponent(item.title)}"
		>Suggest a correction or report a problem</a
	>
</p>

<p class="hint">Summarized from the source. A listing is not an endorsement by the dropzone or by Load Organiser.</p>

<style>
	.headline {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.4rem 0.6rem;
	}

	.unstated {
		margin: -0.25rem 0 1rem;
	}

	.actions {
		display: grid;
		gap: 0.6rem;
		justify-items: start;
		margin: 1rem 0;
	}

	.ok {
		color: var(--ok-fg);
		font-weight: 600;
		margin: 0;
	}

	dl {
		display: grid;
		grid-template-columns: max-content 1fr;
		gap: 0.35rem 1rem;
		margin: 1rem 0;
	}

	dt {
		color: var(--muted);
	}

	dd {
		margin: 0;
		overflow-wrap: anywhere;
		display: grid;
		gap: 0.2rem;
		justify-items: start;
	}

	.quote,
	.summary {
		white-space: pre-line;
	}

	@media (max-width: 30rem) {
		dl {
			grid-template-columns: 1fr;
		}

		dd {
			margin-bottom: 0.5rem;
		}
	}
</style>
