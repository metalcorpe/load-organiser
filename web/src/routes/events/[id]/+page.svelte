<script lang="ts">
	import Notice from '#lib/components/Notice.svelte';
	import TypeIcon from '#lib/components/TypeIcon.svelte';
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
	const audienceLine = $derived(
		[
			item.audience.map((a) => AUDIENCE_LABEL[a]).join(', '),
			item.disciplines.map((d) => DISCIPLINE_LABEL[d].toLowerCase()).join(', ')
		]
			.filter(Boolean)
			.join(' · ')
			.replace(/^./, (c) => c.toUpperCase())
	);
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
	// The board search this was opened from stays with the page through sign-in and saving.
	const signInToSave = $derived(data.signInToSave);
	const actionHref = (name: string) =>
		data.results ? `?/${name}&results=${encodeURIComponent(data.results)}` : `?/${name}`;
</script>

<svelte:head>
	<title>{item.title} · Events · Load Organiser</title>
	<link rel="canonical" href={data.canonical} />
	<meta
		name="description"
		content="{CATEGORY_LABEL[item.category]} in {countryName(item.country)}, {formatRange(
			item.starts_on,
			item.ends_on
		)}. Source-backed listing; register with the organizer."
	/>
</svelte:head>

<!-- What it is, when and where: said once, here. -->
<section class="hero type-{item.category}" aria-labelledby="listing-title">
	<!-- "Back to results" only with a search to return to; "All events" always starts afresh. -->
	<p class="back-links">
		{#if data.results}
			<a class="back" href={data.results}>Back to results</a>
		{/if}
		<a class="back" href="/">All events</a>
	</p>
	<p class="pills">
		<span class="type-pill"><TypeIcon category={item.category} />{CATEGORY_LABEL[item.category]}</span>
		{#if status}<span class="badge status">{status}</span>{/if}
	</p>
	<h1 id="listing-title">{item.title}</h1>
	<p class="when">
		{formatRange(item.starts_on, item.ends_on)}
		{#if item.time_zone && item.starts_on}<span class="tz">({item.time_zone} local dates)</span>{/if}
	</p>
	<!-- A listed dropzone links to its page; a place the source only names stays text. -->
	<p class="where">
		{#if item.venue}<a href="/dz/{item.venue.id}">{item.venue.name}</a
			>{item.venue.closed ? ' (closed)' : ''}{', '}{/if}{#if item.location_note}{item.location_note}{', '}{/if}{countryName(
			item.country
		)}
	</p>
</section>

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

{#if item.summary}
	<p class="summary">{item.summary}</p>
{/if}

<!-- What a jumper needs to decide: cost, who it is for, what it asks, who runs it. -->
<dl class="facts">
	{#if price || item.price_note}
		<dt>Price</dt>
		<dd>{price ?? ''}{price && item.price_note ? '. ' : ''}{item.price_note ?? ''}</dd>
	{/if}
	{#if audienceLine}
		<dt>For</dt>
		<dd>{audienceLine}</dd>
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
	<dt>Organizer</dt>
	<dd>
		{#if item.provider}
			<a href="/organizers/{item.provider.id}">{item.provider.name}</a>
		{:else}
			<span class="hint">No longer listed</span>
		{/if}
	</dd>
</dl>

{#if unstated.length}
	<p class="hint unstated">
		Not stated by the source: {unstated.join(', ')}. Ask the organizer.
	</p>
{/if}

<!-- Registering happens with the organizer; saving is private and registers nothing. Two
     separate blocks so one is never mistaken for the other. -->
<section class="action register" aria-label="Register with the organizer">
	<a class="button" href={item.registration_url} rel="external noopener noreferrer nofollow">
		Open organizer registration
	</a>
	<p class="hint">
		Opens <span class="wrap-anywhere">{hostOf(item.registration_url)}</span>. Availability is not
		tracked here: places, registration and payment are with the organizer.
	</p>
</section>

<section class="action save" aria-label="Save privately">
	{#if form && 'error' in form}
		<p class="form-error" role="alert">{listingMessage(form.error)}</p>
	{/if}
	{#if !signedIn}
		<a class="button secondary" href={signInToSave} data-sign-in>Sign in to save this privately</a>
	{:else if isSaved}
		<p role="status" class="ok">Saved privately — you are not registered.</p>
		<form method="POST" action={actionHref('unsave')}>
			<button class="button secondary" type="submit">Remove from saved</button>
		</form>
	{:else}
		{#if data.saveIntent}
			<p role="status">
				You signed in to save this listing. Its current status is shown above; save it if you
				still want to.
			</p>
		{/if}
		<form method="POST" action={actionHref('save')}>
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

<!-- Where this came from: quieter, still readable. -->
<footer class="provenance">
	<p>
		Source: <a class="wrap-anywhere" href={item.source_url} rel="external noopener noreferrer nofollow"
			>{hostOf(item.source_url)}</a
		>{#if item.source_note}{' '}({item.source_note}){/if}. Last checked {formatDay(item.checked_on)}.
	</p>
	<p>
		Summarized from the source. A listing is not an endorsement by the dropzone or by Load
		Organiser.
	</p>
	<p>
		<a
			href="/submit?kind=correction&target_kind=opportunity&target_id={item.id}&title={encodeURIComponent(
				item.title
			)}">Suggest a correction or report a problem</a
		>
	</p>
</footer>

<style>
	/* The navy header: the one brand block on this page. */
	.hero {
		display: grid;
		/* One column no wider than the card: a title word too long for it breaks instead of
		   widening the page. */
		grid-template-columns: minmax(0, 1fr);
		gap: 0.4rem;
		margin: 0 -1rem 1rem;
		padding: 0.75rem 1.25rem 1.4rem;
		border-radius: 0 0 26px 26px;
		background: var(--brand);
		color: var(--brand-fg);
	}

	/* Edge to edge on a phone; on a larger screen it starts at the content edge, like the
	   header and tabs above it. */
	@media (min-width: 48rem) {
		.hero {
			margin-inline: 0;
		}
	}

	.hero p {
		margin: 0;
	}

	.back-links {
		display: flex;
		flex-wrap: wrap;
		gap: 0 1.25rem;
	}

	.back {
		display: inline-flex;
		align-items: center;
		min-height: 44px;
		color: var(--brand-fg);
	}

	.pills {
		display: flex;
		flex-wrap: wrap;
		gap: 0.4rem;
	}

	/* The title is the strongest type on the page; the dates come second. */
	.hero h1 {
		margin: 0.15rem 0 0.1rem;
		font-size: 2rem;
		line-height: 1.1;
	}

	.when {
		font-family: var(--font-display);
		font-weight: 600;
		font-size: 1.15rem;
	}

	.tz {
		font-family: var(--font-body);
		font-weight: 400;
		font-size: 0.9rem;
		color: var(--brand-muted);
	}

	.where {
		color: var(--brand-muted);
	}

	.where a {
		color: var(--brand-fg);
	}

	.summary {
		font-size: 1.05rem;
		line-height: 1.55;
	}

	.facts {
		margin: 1rem 0;
	}

	.facts dd {
		display: grid;
		gap: 0.2rem;
		justify-items: start;
	}

	.unstated {
		margin: -0.25rem 0 1rem;
	}

	.action {
		display: grid;
		gap: 0.6rem;
		justify-items: start;
		margin: 1rem 0;
	}

	.action p,
	.action form {
		margin: 0;
	}

	/* Saving sits apart from registering, under a rule. */
	.save {
		padding-top: 1rem;
		border-top: 1px solid var(--border);
	}

	.ok {
		color: var(--ok-fg);
		font-weight: 600;
	}

	.provenance {
		margin: 2rem 0 0.5rem;
		padding-top: 0.75rem;
		border-top: 1px solid var(--border);
		color: var(--muted);
		font-size: 0.9rem;
	}

	.provenance p {
		margin: 0 0 0.5rem;
	}

	.provenance p:last-child a {
		display: inline-flex;
		align-items: center;
		min-height: 44px;
	}

	.quote,
	.summary {
		white-space: pre-line;
	}
</style>
