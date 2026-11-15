<script lang="ts">
	import Disclosure from '#lib/components/Disclosure.svelte';
	import PrivacyLabel from '#lib/components/PrivacyLabel.svelte';
	import { page } from '$app/state';
	import { CATEGORY_LABEL, formatRange, listingMessage, statusLabel } from '#lib/listings.ts';
	import { safeReturnPath } from '#lib/safe-return.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();

	const errorFor = (name: string, id?: string) =>
		form && form.form === name && 'error' in form && (!id || ('id' in form && form.id === id))
			? listingMessage(form.error)
			: undefined;
	const created = $derived(page.url.searchParams.get('created') === '1');
	// Where the new plan was started from: an event or a dropzone page on this site.
	const back = $derived.by(() => {
		const path = safeReturnPath(page.url.searchParams.get('back'));
		if (path?.startsWith('/events/')) return { href: path, label: 'Back to the event' };
		if (path?.startsWith('/dz/')) return { href: path, label: 'Back to the dropzone' };
		return null;
	});
	// The new-plan form is open when a page sent you here to plan, or it has something to say.
	const planning = $derived(Boolean(data.start) || Boolean(errorFor('create')));
</script>

<svelte:head>
	<title>Plans and saved events · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<p><a href="/profile">Me</a></p>
<h1>Plans and saved events</h1>
<PrivacyLabel />
<p class="lede">
	A plan is dates you mean to be somewhere; a saved event is a bookmark. Neither registers you,
	is shared, or becomes a logged jump.
</p>

{#if created}
	<p role="status" class="ok">
		Plan saved privately.{#if back}
			<a href={back.href}>{back.label}</a>{/if}
	</p>
{/if}

{#snippet newPlan()}
	{#if !data.emailVerified}
		<p class="hint">Confirm your email address (see Me) to save plans.</p>
	{/if}
	<form method="POST" action="?/create" class="form" novalidate>
		{#if errorFor('create')}<p class="form-error" role="alert">{errorFor('create')}</p>{/if}
		{#if data.start?.kind === 'opportunity'}
			<input type="hidden" name="opportunity_id" value={data.start.id} />
			<p class="hint">
				Dates below start from the listing's dates; change them to your own. Registering is still
				done with the organizer.
			</p>
		{:else if data.start?.kind === 'venue'}
			<input type="hidden" name="venue_id" value={data.start.id} />
		{/if}
		<div class="field">
			<label for="new-title">Title</label>
			<input
				id="new-title"
				name="title"
				required
				maxlength="120"
				defaultValue={data.start?.title ?? ''}
				autocomplete="off"
			/>
		</div>
		<div class="dates">
			<div class="field">
				<label for="new-start">First day</label>
				<input id="new-start" name="starts_on" type="date" required defaultValue={data.start?.startsOn ?? ''} />
			</div>
			<div class="field">
				<label for="new-end">Last day</label>
				<input id="new-end" name="ends_on" type="date" required defaultValue={data.start?.endsOn ?? ''} />
			</div>
		</div>
		{#if !data.start && data.places.length > 0}
			<div class="field">
				<label for="new-place">Private place (optional)</label>
				<select id="new-place" name="place_id">
					<option value="">None</option>
					{#each data.places as place (place.id)}
						<option value={place.id}>{place.name}</option>
					{/each}
				</select>
			</div>
		{/if}
		<div class="field">
			<label for="new-note">Note (optional, private)</label>
			<textarea id="new-note" name="note" maxlength="500" rows="2"></textarea>
		</div>
		<div class="form-actions"><button class="button" type="submit">Save plan</button></div>
	</form>
{/snippet}

<!-- Sent here from an event or a dropzone to plan: the form comes first. -->
{#if data.start}
	<section class="card" aria-labelledby="new-heading">
		<h2 id="new-heading">Plan a visit: {data.start.title}</h2>
		{@render newPlan()}
		<p class="hint">
			<a href={data.start.kind === 'opportunity' ? `/events/${data.start.id}` : `/dz/${data.start.id}`}
				>{data.start.kind === 'opportunity' ? 'Back to the event' : 'Back to the dropzone'}</a
			> without planning.
		</p>
	</section>
{/if}

<section class="part" aria-labelledby="plans-heading">
<h2 id="plans-heading">Visit plans</h2>
{#if errorFor('remove')}<p class="form-error" role="alert">{errorFor('remove')}</p>{/if}
{#if !data.plans.ok}
	<p class="form-error" role="alert">{listingMessage(data.plans.reason)}</p>
{:else if data.plans.items.length === 0}
	<p class="hint">
		No plans yet. Plan a visit from an event or a dropzone page, or add one here.
	</p>
{:else}
	<ul class="results rows" aria-label="Your plans">
		{#each data.plans.items as plan (plan.id)}
			{@const item = plan.opportunity}
			<!-- The Logbook's "Coming up" links here. -->
			<li id="plan-{plan.id}">
				<span class="title">{plan.title}</span>
				<span class="meta">Your dates: {formatRange(plan.starts_on, plan.ends_on)}</span>
				{#if item}
					<span class="meta">
						Listing: <a href="/events/{item.id}">{item.title}</a>
						{#if statusLabel(item.status, item.ended)}
							<span class="tag">{statusLabel(item.status, item.ended)}</span>
						{/if}
					</span>
					{#if item.starts_on !== plan.starts_on || item.ends_on !== plan.ends_on}
						<span class="meta changed"
							>The listing's dates are {formatRange(item.starts_on, item.ends_on)}. Your plan is
							unchanged.</span
						>
					{/if}
				{:else if plan.opportunity_id}
					<span class="meta">The linked listing is no longer published.</span>
				{:else if plan.venue}
					<span class="meta">Dropzone: <a href="/dz/{plan.venue.id}">{plan.venue.name}</a></span>
				{:else if plan.place}
					<span class="meta">Private place: {plan.place.name}</span>
				{/if}
				{#if plan.note}<span class="meta note">{plan.note}</span>{/if}
				<details>
					<summary>Edit or delete</summary>
					<form method="POST" action="?/update" class="form" novalidate>
						{#if errorFor('update', plan.id)}
							<p class="form-error" role="alert">{errorFor('update', plan.id)}</p>
						{/if}
						<input type="hidden" name="id" value={plan.id} />
						<div class="field">
							<label for="title-{plan.id}">Title</label>
							<input id="title-{plan.id}" name="title" maxlength="120" defaultValue={plan.title} />
						</div>
						<div class="dates">
							<div class="field">
								<label for="start-{plan.id}">First day</label>
								<input id="start-{plan.id}" name="starts_on" type="date" defaultValue={plan.starts_on} />
							</div>
							<div class="field">
								<label for="end-{plan.id}">Last day</label>
								<input id="end-{plan.id}" name="ends_on" type="date" defaultValue={plan.ends_on} />
							</div>
						</div>
						<div class="field">
							<label for="note-{plan.id}">Note</label>
							<textarea id="note-{plan.id}" name="note" maxlength="500" rows="2"
								>{plan.note ?? ''}</textarea
							>
						</div>
						<div class="form-actions">
							<button class="button" type="submit">Save changes</button>
						</div>
					</form>
					<form method="POST" action="?/remove">
						<input type="hidden" name="id" value={plan.id} />
						<button class="button danger" type="submit">Delete plan</button>
					</form>
				</details>
			</li>
		{/each}
	</ul>
{/if}

{#if !data.start}
	<Disclosure class="new-plan" open={planning}>
		{#snippet summary()}Plan a visit{/snippet}
		{@render newPlan()}
	</Disclosure>
{/if}
</section>

<section class="part" id="saved" aria-labelledby="saved-heading">
	<h2 id="saved-heading">Saved events</h2>
	{#if errorFor('unsave')}<p class="form-error" role="alert">{errorFor('unsave')}</p>
	{:else if form && form.form === 'unsave' && 'done' in form}<p role="status">Removed from saved.</p>{/if}
	{#if !data.saved.ok}
		<p class="form-error" role="alert">{listingMessage(data.saved.reason)}</p>
	{:else if data.saved.items.length === 0}
		<p class="hint">
			Nothing saved. Save an event from its page to keep it here; saving does not register you.
			<a href="/">Browse events</a>
		</p>
	{:else}
		<ul class="results rows" aria-label="Saved events">
			{#each data.saved.items as entry (entry.opportunity_id)}
				{@const item = entry.opportunity}
				<li>
					{#if item}
						<a class="title" href="/events/{item.id}">{item.title}</a>
						<span class="meta"
							>{CATEGORY_LABEL[item.category]} · {formatRange(item.starts_on, item.ends_on)}</span
						>
						{#if statusLabel(item.status, item.ended)}
							<span class="tag">{statusLabel(item.status, item.ended)}</span>
						{/if}
					{:else}
						<span class="title">{entry.title}</span>
						<span class="meta">No longer published. The organizer's own page may still have details.</span>
					{/if}
					<span class="row">
						{#if item}<a href="/plans?opportunity={item.id}">Plan a visit</a>{/if}
						<form method="POST" action="?/unsave">
							<input type="hidden" name="id" value={entry.opportunity_id} />
							<button class="button secondary small" type="submit">Remove</button>
						</form>
					</span>
				</li>
			{/each}
		</ul>
	{/if}
</section>

<style>
	.dates {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 10rem), 1fr));
		gap: 1rem;
	}

	.title {
		font-weight: 600;
		flex-basis: 100%;
	}

	.meta {
		color: var(--muted);
		flex-basis: 100%;
		overflow-wrap: anywhere;
	}

	.changed {
		color: var(--warn-fg);
	}

	.note {
		white-space: pre-line;
	}

	details {
		flex-basis: 100%;
	}

	/* The two collections, one after the other, each under its own heading. */
	.part {
		margin: 1.5rem 0;
	}

	.part > h2 {
		margin: 0 0 0.5rem;
	}

	.row {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.5rem 1rem;
		flex-basis: 100%;
	}

	.row form {
		margin: 0;
	}

	.tag {
		justify-self: start;
		border: 1px solid var(--border);
		border-radius: 999px;
		padding: 0 0.5rem;
		font-size: 0.85rem;
		color: var(--muted);
	}

	.part :global(details.new-plan) {
		margin-top: 1rem;
	}

	.part :global(details.new-plan > summary) {
		display: inline-flex;
		align-items: center;
		min-height: 44px;
		color: var(--accent);
		font-weight: 650;
		cursor: pointer;
	}
</style>
