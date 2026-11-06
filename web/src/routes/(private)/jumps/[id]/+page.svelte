<script lang="ts">
	import { page } from '$app/state';
	import JumpForm from '#lib/components/JumpForm.svelte';
	import LocationPicker from '#lib/components/LocationPicker.svelte';
	import { countryName } from '#lib/countries.ts';
	import { directoryMessage } from '#lib/directory-messages.ts';
	import { JUMP_TYPE_LABEL, altitudeText, jumpMessage } from '#lib/jumps.ts';
	import { formatDay } from '#lib/listings.ts';
	import { AUDIENCE_LABEL, postEventText } from '#lib/posts.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();
	const jump = $derived(data.detail.jump);
	const base = $derived(`/jumps/${jump.id}`);
	const echoed = $derived(
		form && form.form === 'save' && 'values' in form && form.values ? form.values : null
	);
	const saved = $derived<Record<string, string>>({
		jumped_on: jump.jumped_on,
		jump_type: jump.jump_type,
		jump_number: jump.jump_number?.toString() ?? '',
		exit_time: jump.exit_time?.slice(0, 5) ?? '',
		time_zone: jump.time_zone ?? '',
		exit_altitude: jump.exit_altitude?.toString() ?? '',
		deployment_altitude: jump.deployment_altitude?.toString() ?? '',
		altitude_unit: jump.altitude_unit ?? '',
		altitude_datum: jump.altitude_datum,
		freefall_seconds: jump.freefall_seconds?.toString() ?? '',
		other_gear: jump.other_gear ?? '',
		notes: jump.notes ?? '',
		links: jump.links.join('\n')
	});
	const values = $derived(echoed ?? saved);
	const selected = $derived(
		echoed
			? (echoed.component_ids ?? '').split(',').filter(Boolean)
			: jump.components.map((c) => c.id)
	);
	const current = $derived({
		name: jump.location.name ?? 'Dropzone no longer listed',
		detail:
			(jump.location.country ? countryName(jump.location.country) : '') +
			(jump.location.kind === 'place' ? ' · private place' : jump.location.closed ? ' · closed' : ''),
		venueId: jump.location.kind === 'venue' ? jump.location.id : null,
		placeId: jump.location.kind === 'place' ? jump.location.id : null
	});
	const location = $derived({ ...(data.override ?? current), changeHref: `${base}?change=1` });
	const query = $derived(
		[...page.url.searchParams]
			.filter(([k]) => k === 'venue' || k === 'place')
			.map(([k, val]) => `${k}=${encodeURIComponent(val)}`)
			.join('&')
	);
	const errorFor = (name: string) =>
		form && form.form === name && 'error' in form ? jumpMessage(form.error) : undefined;
	const heights = $derived(
		altitudeText(jump.exit_altitude, jump.deployment_altitude, jump.altitude_unit, jump.altitude_datum)
	);
	const FIELD: Record<string, string> = {
		jumped_on: 'Date',
		venue_id: 'Dropzone',
		place_id: 'Private place',
		jump_type: 'Type',
		jump_number: 'Jump number',
		exit_time: 'Exit time',
		time_zone: 'Time zone',
		exit_altitude: 'Exit altitude',
		deployment_altitude: 'Deployment altitude',
		altitude_unit: 'Altitude unit',
		altitude_datum: 'Altitude measured from',
		freefall_seconds: 'Freefall',
		other_gear: 'Other equipment',
		notes: 'Notes',
		links: 'Links',
		equipment: 'Equipment used'
	};
</script>

<svelte:head>
	<title>Jump on {formatDay(jump.jumped_on)} · Logbook · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<p><a href="/jumps">Logbook</a></p>
<h1>Jump on {formatDay(jump.jumped_on)}</h1>
<p class="lede">
	{JUMP_TYPE_LABEL[jump.jump_type]} · {current.name} · {jump.source === 'restored'
		? 'restored from your export'
		: 'entered by you'}, not verified
</p>
{#if page.url.searchParams.get('saved')}<p role="status" class="ok">Saved privately.</p>{/if}
{#if data.detail.same_number.length > 0}
	<p class="hint" role="note">
		Another entry has jump number {jump.jump_number}:
		{#each data.detail.same_number as other, i (other)}{i ? ', ' : ''}<a href="/jumps/{other}">view</a>{/each}.
		Check for a typing mistake or a duplicate.
	</p>
{/if}

<dl class="facts">
	<dt>Where</dt>
	<dd>{current.name}{current.detail ? ` (${current.detail.replace(/^ · /, '')})` : ''}</dd>
	{#if jump.jump_number}<dt>Jump number</dt><dd>{jump.jump_number}</dd>{/if}
	{#if jump.exit_time}<dt>Exit time</dt><dd>{jump.exit_time.slice(0, 5)} ({jump.time_zone})</dd>{/if}
	{#if heights}<dt>Altitudes</dt><dd>{heights}{jump.altitude_datum === 'unspecified' ? ' (reference not stated)' : ''}</dd>{/if}
	{#if jump.freefall_seconds !== null}<dt>Freefall</dt><dd>{jump.freefall_seconds} s</dd>{/if}
	<dt>Equipment</dt>
	<dd>
		{#if jump.components.length === 0 && !jump.other_gear}Not recorded{/if}
		{#each jump.components as c, i (c.id)}{i ? ', ' : ''}<a href="/gear/{c.id}">{c.label}</a>{c.archived ? ' (archived)' : ''}{/each}{#if jump.other_gear}{jump.components.length ? '; ' : ''}{jump.other_gear}{/if}
	</dd>
	{#if jump.links.length > 0}
		<dt>Links</dt>
		<dd>
			{#each jump.links as link (link)}<a href={link} rel="noopener noreferrer nofollow" target="_blank">{link}</a><br />{/each}
		</dd>
	{/if}
</dl>

<h2>Sharing</h2>
{#if data.post}
	<p>
		Published to {AUDIENCE_LABEL[data.post.audience].toLowerCase()}:
		<a href="/posts/{data.post.id}">view post</a> · <a href="{base}/share">change or unpublish</a>
	</p>
	<p class="hint">Editing a value the post shares withdraws it first.</p>
{:else}
	<p>
		{data.sharingOk ? 'Private: not shared with anyone.' : ''}
		<a href="{base}/share">Share a summary of this jump</a>
	</p>
{/if}

<h2>Edit</h2>
{#if !data.emailVerified}
	<p class="hint">Confirm your email address on your <a href="/profile">profile</a> to edit jumps.</p>
{/if}
{#if data.changing}
	<LocationPicker
		base={base}
		q={data.picker?.q ?? ''}
		matches={data.picker?.matches ?? null}
		places={data.places}
		keep={{ change: '1' }}
		error={form && form.form === 'place' && 'error' in form ? directoryMessage(form.error) : undefined}
	/>
	<p><a href={base}>Keep the current place</a></p>
{:else}
	{#if data.override}<p class="hint" role="status">New place chosen; save to apply it.</p>{/if}
	{#if errorFor('save')}<p class="form-error" role="alert">{errorFor('save')}</p>{/if}
	<JumpForm
		action="?{query}&/save"
		{values}
		{location}
		gear={data.gear.items}
		{selected}
		keys={{ component: echoed?.new_component_key || data.componentKey }}
		version={(echoed && form && 'based' in form && form.based) || jump.version}
		submitLabel="Save changes"
	/>
{/if}

{#if data.detail.events.length > 0}
	<h2>History</h2>
	<p class="hint">Your private record of changes. Earlier notes and links are not kept.</p>
	<ul class="results" aria-label="History">
		{#each data.detail.events as event, i (i)}
			<li>
				<span class="title"
						>{postEventText(event.kind, event.detail) ??
							(event.kind === 'created'
								? 'Logged'
								: event.kind === 'from_export'
									? 'Restored from your export'
									: 'Corrected')} on {formatDay(event.created_at.slice(0, 10))}</span
					>
				{#if event.kind === 'corrected'}
					{#each Object.entries(event.detail) as [name, change] (name)}
						<span class="meta"
							>{FIELD[name] ?? name}: {typeof change === 'object' && change !== null && !name.endsWith('_id')
								? `${(change as { from: unknown }).from ?? 'none'} → ${(change as { to: unknown }).to ?? 'none'}`
								: 'changed'}</span
						>
					{/each}
				{/if}
			</li>
		{/each}
	</ul>
{/if}

<h2>Delete</h2>
<form method="POST" action="?/delete" class="form">
	{#if errorFor('delete')}<p class="form-error" role="alert">{errorFor('delete')}</p>{/if}
	<input type="hidden" name="version" value={jump.version} />
	<label class="choice"><input type="checkbox" name="confirm" /> Delete this jump and its history</label>
	<p class="hint">This cannot be undone. Your gear and places are kept.</p>
	<div class="form-actions"><button class="button secondary" type="submit">Delete jump</button></div>
</form>

