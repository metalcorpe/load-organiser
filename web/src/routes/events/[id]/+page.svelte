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
	// The header's big dates: "24–31" with "December 2026", or the full range across months.
	const MONTH_YEAR = new Intl.DateTimeFormat('en-GB', {
		month: 'long',
		year: 'numeric',
		timeZone: 'UTC'
	});
	const bigDates = $derived.by(() => {
		const { starts_on: s, ends_on: e } = item;
		if (!s || !e) return null;
		if (s.slice(0, 7) !== e.slice(0, 7)) return { big: '', small: formatRange(s, e) };
		const d = (v: string) => String(Number(v.slice(8)));
		return {
			big: s === e ? d(s) : `${d(s)}–${d(e)}`,
			small: MONTH_YEAR.format(new Date(`${s}T00:00:00Z`))
		};
	});
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
	const signInToSave = $derived(
		`/sign-in?returnTo=${encodeURIComponent(`/events/${item.id}?save=1`)}`
	);
</script>

<svelte:head>
	<title>{item.title} · Events · Load Organiser</title>
	<meta
		name="description"
		content="{CATEGORY_LABEL[item.category]} in {countryName(item.country)}, {formatRange(
			item.starts_on,
			item.ends_on
		)}. Source-backed listing; register with the organizer."
	/>
</svelte:head>

<section class="hero type-{item.category}" aria-labelledby="listing-title">
	<a class="back" href="/">All listings</a>
	<p class="pills">
		<span class="type-pill"><TypeIcon category={item.category} />{CATEGORY_LABEL[item.category]}</span>
		{#if status}<span class="badge status">{status}</span>{/if}
	</p>
	<h1 id="listing-title">{item.title}</h1>
	{#if bigDates}
		<p class="dates">
			{#if bigDates.big}<span class="big">{bigDates.big}</span>{/if}
			<span class="small">{bigDates.small}</span>
		</p>
	{:else}
		<p class="dates"><span class="small">Dates not announced</span></p>
	{/if}
	<p class="where-line">
		{item.venue ? item.venue.name : (item.location_note ?? '')}{item.venue || item.location_note
			? ', '
			: ''}{countryName(item.country)}
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

<ul class="facts">
	<li>
		<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 21s7-6.2 7-12a7 7 0 0 0-14 0c0 5.8 7 12 7 12z" /><circle cx="12" cy="9" r="2.5" /></svg>
		<span
			>{#if item.venue}<a href="/dz/{item.venue.id}">{item.venue.name}</a
				>{item.venue.closed ? ' (closed)' : ''}{', '}{/if}{#if item.location_note}{item.location_note}{', '}{/if}{countryName(
				item.country
			)}</span
		>
	</li>
	{#if price || item.price_note}
		<li>
			<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M15 9.2A3.5 3.5 0 0 0 9 11h0a3.5 3.5 0 0 0 6 1.8M7.5 11h5M7.5 13.5h5" /></svg>
			<span>{price ?? ''}{price && item.price_note ? '. ' : ''}{item.price_note ?? ''}</span>
		</li>
	{/if}
	{#if audienceLine}
		<li>
			<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></svg>
			<span>{audienceLine}</span>
		</li>
	{/if}
</ul>

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

<dl>
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
	/* The navy header: the one brand block on this page. */
	.hero {
		display: grid;
		gap: 0.5rem;
		margin: 0 -1rem 1rem;
		padding: 0.75rem 1.25rem 1.4rem;
		border-radius: 0 0 26px 26px;
		background: var(--brand);
		color: var(--brand-fg);
	}

	.hero p {
		margin: 0;
	}

	.back {
		justify-self: start;
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

	.hero h1 {
		margin: 0.1rem 0 0;
		font-size: 1.9rem;
		line-height: 1.1;
	}

	.dates {
		display: flex;
		flex-wrap: wrap;
		align-items: baseline;
		gap: 0.25rem 0.6rem;
	}

	.big {
		font-family: var(--font-display);
		font-weight: 700;
		font-size: 3.1rem;
		line-height: 0.95;
		color: var(--highlight);
		font-variant-numeric: tabular-nums;
	}

	.small {
		font-family: var(--font-display);
		font-weight: 600;
		font-size: 1.15rem;
		color: var(--brand-muted);
	}

	.where-line {
		color: var(--brand-muted);
	}

	.summary {
		font-size: 1.05rem;
		line-height: 1.55;
	}

	/* B's fact list: place, price, who it is for. */
	.facts {
		list-style: none;
		padding: 0;
		margin: 0 0 1rem;
		display: grid;
		gap: 0.6rem;
	}

	.facts li {
		display: grid;
		grid-template-columns: 1.4rem 1fr;
		gap: 0.7rem;
		align-items: start;
	}

	.facts svg {
		width: 1.25rem;
		height: 1.25rem;
		margin-top: 0.1rem;
		fill: none;
		stroke: var(--icon);
		stroke-width: 2;
		stroke-linecap: round;
		stroke-linejoin: round;
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
