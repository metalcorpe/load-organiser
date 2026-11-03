<script lang="ts">
	import { page } from '$app/state';
	import ReviewHistory from '#lib/components/ReviewHistory.svelte';
	import { COUNTRY_OPTIONS } from '#lib/countries.ts';
	import {
		AUDIENCE_VALUES,
		CATEGORY_VALUES,
		DISCIPLINE_VALUES
	} from '#lib/listing-filters.ts';
	import {
		AUDIENCE_LABEL,
		CATEGORY_LABEL,
		DISCIPLINE_LABEL,
		PRICE_BASIS_LABEL
	} from '#lib/listings.ts';
	import { reviewMessage } from '#lib/review-messages.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();
	const l = $derived(data.listing);
	const echoed = $derived(form && 'values' in form && form.values ? form.values : null);
	const v = (name: string, current: string | null | undefined) =>
		echoed ? (echoed[name] ?? '') : (current ?? '');
	const has = (name: 'disciplines' | 'audience', value: string) =>
		echoed ? (echoed[name] ?? '').split(',').includes(value) : (l?.[name] ?? []).includes(value);
	const errorFor = (name: string) =>
		form && form.form === name && 'error' in form ? reviewMessage(form.error) : undefined;
	const NEXT: Record<string, string[]> = {
		draft: ['review', 'archived'],
		review: ['draft', 'published', 'archived'],
		published: ['postponed', 'cancelled', 'archived'],
		postponed: ['published', 'cancelled', 'archived'],
		cancelled: ['archived'],
		archived: ['draft'],
		duplicate: []
	};
	const PUBLIC = ['published', 'postponed', 'cancelled'];
	const providerKnown = $derived(!l || data.providers.some((p) => p.id === l.provider_id));
	const venueKnown = $derived(!l?.venue_id || data.venues.some((x) => x.id === l.venue_id));
</script>

<svelte:head>
	<title>{l ? l.title : 'New listing'} · Maintenance · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<p><a href="/review">Maintenance</a></p>
<h1>{l ? l.title : 'New listing'}</h1>
{#if l}
	<p class="lede">
		{l.status} · version {l.version}
		{#if PUBLIC.includes(l.status)} · <a href="/events/{l.id}">public page</a>{/if}
	</p>
{/if}
{#if page.url.searchParams.get('saved') || (form && form.form === 'save' && 'done' in form)}
	<p role="status">Saved.</p>
{/if}
{#if page.url.searchParams.get('absorbed')}<p role="status">The duplicate now points here.</p>{/if}

{#if l?.status === 'duplicate'}
	<p>Consolidated into <a href="/review/listings/{l.duplicate_of_id}">the kept listing</a>.</p>
	<ReviewHistory events={l.events} />
{:else}
	<form method="GET" class="form lookups" role="search">
		<div class="field">
			<label for="org_q">Find organizer</label>
			<input id="org_q" name="org_q" type="search" maxlength="80" defaultValue={data.orgQ} />
		</div>
		<div class="field">
			<label for="dz_q">Find dropzone</label>
			<input id="dz_q" name="dz_q" type="search" maxlength="80" defaultValue={data.dzQ} />
		</div>
		<div class="form-actions"><button class="button secondary" type="submit">Update choices</button></div>
	</form>

	<form method="POST" action="?/save" class="form" novalidate>
		{#if errorFor('save')}<p class="form-error" role="alert">{errorFor('save')}</p>{/if}
		<input type="hidden" name="version" value={l?.version ?? ''} />

		<fieldset>
			<legend>What</legend>
			<div class="field">
				<label for="title">Title</label>
				<input id="title" name="title" maxlength="160" required defaultValue={v('title', l?.title)} />
			</div>
			<div class="field">
				<label for="category">Type</label>
				<select id="category" name="category">
					{#each CATEGORY_VALUES as value (value)}
						<option {value} selected={v('category', l?.category ?? 'event') === value}>{CATEGORY_LABEL[value]}</option>
					{/each}
				</select>
			</div>
			<div class="field">
				<label for="provider_id">Organizer</label>
				<select id="provider_id" name="provider_id" required>
					<option value="">Choose…</option>
					{#if l && !providerKnown}<option value={l.provider_id} selected>Current organizer</option>{/if}
					{#each data.providers as provider (provider.id)}
						<option value={provider.id} selected={v('provider_id', l?.provider_id) === provider.id}
							>{provider.name}{provider.status === 'published' ? '' : ` (${provider.status})`}</option
						>
					{/each}
				</select>
				<p class="hint">Shows up to 50; search above to narrow. <a href="/review/organizers/new">New organizer</a></p>
			</div>
			<div class="field">
				<label for="summary">Summary (optional)</label>
				<textarea id="summary" name="summary" maxlength="500" rows="3">{v('summary', l?.summary)}</textarea>
			</div>
		</fieldset>

		<fieldset>
			<legend>Where and when</legend>
			<div class="field">
				<label for="venue_id">Dropzone (optional)</label>
				<select id="venue_id" name="venue_id">
					<option value="">None — describe the location below</option>
					{#if l?.venue_id && !venueKnown}<option value={l.venue_id} selected>Current dropzone</option>{/if}
					{#each data.venues as venue (venue.id)}
						<option value={venue.id} selected={v('venue_id', l?.venue_id) === venue.id}>{venue.name} ({venue.country})</option>
					{/each}
				</select>
			</div>
			<div class="field">
				<label for="location_note">Location note</label>
				<input id="location_note" name="location_note" maxlength="200" defaultValue={v('location_note', l?.location_note)} />
			</div>
			<div class="field">
				<label for="country">Country</label>
				<select id="country" name="country" required>
					<option value="">Choose a country</option>
					{#each COUNTRY_OPTIONS as option (option.code)}
						<option value={option.code} selected={v('country', l?.country) === option.code}>{option.name}</option>
					{/each}
				</select>
			</div>
			<div class="pair">
				<div class="field">
					<label for="starts_on">First day</label>
					<input id="starts_on" name="starts_on" type="date" defaultValue={v('starts_on', l?.starts_on)} />
				</div>
				<div class="field">
					<label for="ends_on">Last day</label>
					<input id="ends_on" name="ends_on" type="date" defaultValue={v('ends_on', l?.ends_on)} />
				</div>
			</div>
			<div class="field">
				<label for="time_zone">Time zone of the dates</label>
				<input id="time_zone" name="time_zone" list="zones" maxlength="64" placeholder="Europe/Madrid" defaultValue={v('time_zone', l?.time_zone)} />
				<datalist id="zones">
					{#each data.zones as zone (zone)}<option value={zone}></option>{/each}
				</datalist>
			</div>
		</fieldset>

		<fieldset>
			<legend>Who it is for</legend>
			<div class="checks" role="group" aria-label="Disciplines">
				{#each DISCIPLINE_VALUES as value (value)}
					<label class="choice"><input type="checkbox" name="disciplines" {value} checked={has('disciplines', value)} /> {DISCIPLINE_LABEL[value]}</label>
				{/each}
			</div>
			<div class="checks" role="group" aria-label="Intended for">
				{#each AUDIENCE_VALUES as value (value)}
					<label class="choice"><input type="checkbox" name="audience" {value} checked={has('audience', value)} /> {AUDIENCE_LABEL[value]}</label>
				{/each}
			</div>
			<div class="field">
				<label for="languages">Languages (ISO codes, e.g. "en, es")</label>
				<input id="languages" name="languages" maxlength="60" defaultValue={v('languages', l?.languages.join(', '))} />
			</div>
			<div class="field">
				<label for="prerequisites">Prerequisites, as the source states them</label>
				<textarea id="prerequisites" name="prerequisites" maxlength="1000" rows="3">{v('prerequisites', l?.prerequisites)}</textarea>
			</div>
		</fieldset>

		<fieldset>
			<legend>Price (optional)</legend>
			<div class="pair">
				<div class="field">
					<label for="price_amount">Amount</label>
					<input id="price_amount" name="price_amount" inputmode="decimal" defaultValue={v('price_amount', l?.price_amount)} />
				</div>
				<div class="field">
					<label for="price_currency">Currency</label>
					<input id="price_currency" name="price_currency" maxlength="3" placeholder="EUR" defaultValue={v('price_currency', l?.price_currency)} />
				</div>
			</div>
			<div class="field">
				<label for="price_basis">Basis</label>
				<select id="price_basis" name="price_basis">
					<option value="">Not stated</option>
					{#each Object.entries(PRICE_BASIS_LABEL) as [value, label] (value)}
						<option {value} selected={v('price_basis', l?.price_basis) === value}>{label}</option>
					{/each}
				</select>
			</div>
			<div class="field">
				<label for="price_note">Price note</label>
				<input id="price_note" name="price_note" maxlength="280" defaultValue={v('price_note', l?.price_note)} />
			</div>
		</fieldset>

		<fieldset>
			<legend>Links and source</legend>
			<div class="field">
				<label for="registration_url">Registration or contact link</label>
				<input id="registration_url" name="registration_url" type="url" defaultValue={v('registration_url', l?.registration_url)} />
			</div>
			<div class="field">
				<label for="source_url">Source link</label>
				<input id="source_url" name="source_url" type="url" defaultValue={v('source_url', l?.source_url)} />
			</div>
			<div class="field">
				<label for="source_note">Source note</label>
				<input id="source_note" name="source_note" maxlength="280" defaultValue={v('source_note', l?.source_note)} />
			</div>
			<div class="field">
				<label for="checked_on">Source last checked</label>
				<input id="checked_on" name="checked_on" type="date" defaultValue={v('checked_on', l?.checked_on)} />
			</div>
		</fieldset>

		<div class="form-actions">
			<button class="button" type="submit">{l ? 'Save changes' : 'Create draft'}</button>
		</div>
	</form>

	{#if l}
		<h2>Status</h2>
		{#if errorFor('status')}<p class="form-error" role="alert">{errorFor('status')}</p>{/if}
		<form method="POST" action="?/status" class="form-actions">
			<input type="hidden" name="version" value={l.version} />
			{#each NEXT[l.status] ?? [] as status (status)}
				<button class="button secondary" type="submit" name="status" value={status}>Make {status}</button>
			{/each}
		</form>
		<p class="hint">Postponing clears the announced dates (they stay in the history).</p>

		<h2>Mark as a duplicate</h2>
		{#if errorFor('duplicate')}<p class="form-error" role="alert">{errorFor('duplicate')}</p>{/if}
		<form method="POST" action="?/duplicate" class="form">
			<input type="hidden" name="version" value={l.version} />
			<div class="field">
				<label for="of">ID of the listing to keep</label>
				<input id="of" name="of" maxlength="36" autocomplete="off" />
				<p class="hint">Final: this listing's address will point to the kept one, and its source is kept in that listing's history.</p>
			</div>
			<div class="form-actions"><button class="button secondary" type="submit">Consolidate</button></div>
		</form>

		<ReviewHistory events={l.events} />
	{/if}
{/if}

<style>
	fieldset {
		border: 1px solid var(--border);
		border-radius: var(--radius);
		padding: 1rem;
		display: grid;
		gap: 1rem;
		min-width: 0;
	}

	legend {
		font-weight: 700;
		padding: 0 0.3rem;
	}

	.pair,
	.lookups {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 10rem), 1fr));
		gap: 1rem;
	}

	.checks {
		display: flex;
		flex-wrap: wrap;
		gap: 0 1rem;
	}

	.choice {
		display: flex;
		gap: 0.4rem;
		align-items: center;
		min-height: 44px;
	}
</style>
