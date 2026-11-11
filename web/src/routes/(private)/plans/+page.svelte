<script lang="ts">
	import { page } from '$app/state';
	import { formatRange, listingMessage, statusLabel } from '#lib/listings.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();

	const errorFor = (name: string, id?: string) =>
		form && form.form === name && 'error' in form && (!id || ('id' in form && form.id === id))
			? listingMessage(form.error)
			: undefined;
	const created = $derived(page.url.searchParams.get('created') === '1');
</script>

<svelte:head>
	<title>Visit plans · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<p><a href="/records">Records</a></p>
<h1>Visit plans</h1>
<p class="lede">
	Private dated plans. Nobody else sees them: they are not shared, not a registration and never turn
	into a logged jump.
</p>

{#if created}<p role="status">Plan saved privately.</p>{/if}

<section class="card" aria-labelledby="new-heading">
	<h2 id="new-heading">
		{data.start ? `Plan a visit: ${data.start.title}` : 'Plan a visit'}
	</h2>
	{#if !data.emailVerified}
		<p class="hint">Confirm your email address on your <a href="/profile">profile</a> to save plans.</p>
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
</section>

<h2>Your plans</h2>
{#if errorFor('remove')}<p class="form-error" role="alert">{errorFor('remove')}</p>{/if}
{#if !data.plans.ok}
	<p class="form-error" role="alert">{listingMessage(data.plans.reason)}</p>
{:else if data.plans.items.length === 0}
	<p>No plans yet.</p>
{:else}
	<ul class="results rows" aria-label="Your plans">
		{#each data.plans.items as plan (plan.id)}
			{@const item = plan.opportunity}
			<li>
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
						<button class="button secondary" type="submit">Delete plan</button>
					</form>
				</details>
			</li>
		{/each}
	</ul>
{/if}

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
</style>
