<script lang="ts">
	import TextArea from '#lib/components/TextArea.svelte';
	import { page } from '$app/state';
	import { countryName } from '#lib/countries.ts';
	import { DISCIPLINES, disciplineLabel, socialMessage } from '#lib/social.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();
	const own = $derived(data.profile);
	const echoed = $derived(
		form && form.form === 'save' && 'values' in form && form.values ? form.values : null
	);
	const v = (name: string, saved: string) => (echoed ? (echoed[name] ?? '') : saved);
	const chosen = $derived(
		new Set(echoed ? (echoed.disciplines ?? '').split(',').filter(Boolean) : (own?.disciplines ?? []))
	);
	const discoverable = $derived(echoed ? echoed.discoverable === 'on' : (own?.discoverable ?? false));
	const home = $derived(echoed ? (echoed.home ?? '') : (own?.home_venue?.id ?? ''));
	// A refused edit keeps the version it was based on (a stale tab conflicts again).
	const based = $derived(
		(echoed && form && 'based' in form && form.based) || own?.version || null
	);
	const error = $derived(
		form && form.form === 'save' && 'error' in form ? socialMessage(form.error) : undefined
	);
	// From someone's profile: saving goes back there (the server checks it is a local path).
	const returnTo = $derived(page.url.searchParams.get('returnTo'));
</script>

<svelte:head>
	<title>Public profile · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<p><a href="/profile">Profile</a> · <a href="/people">People</a></p>
<h1>Public profile</h1>
<p class="lede">
	Optional. Only what you enter here is shown: never your email, registration name, logbook, gear,
	totals or prior jump count.
</p>

{#if page.url.searchParams.get('saved')}<p role="status" class="ok">Saved.</p>{/if}
{#if !data.profileOk}
	<p class="form-error" role="alert">{socialMessage('unavailable')}</p>
{:else}
	{#if own?.hidden}
		<p class="form-error" role="alert">
			A reviewer has hidden your profile; no one else can see it. Reason: {own.moderation_reason}
		</p>
	{:else if own?.publishing_restricted}
		<p class="hint" role="note">A reviewer has restricted publishing for your profile. Reason: {own.moderation_reason}</p>
	{/if}
	{#if own}<p><a href="/people/{own.handle}">View as others see it</a></p>{/if}

	<form method="GET" class="form search" role="search">
		<div class="field">
			<label for="q">Find your home dropzone (optional)</label>
			<input id="q" name="q" type="search" maxlength="80" defaultValue={data.q} />
			{#if returnTo}<input type="hidden" name="returnTo" value={returnTo} />{/if}
		</div>
		<div class="form-actions"><button class="button secondary" type="submit">Search</button></div>
	</form>

	<form method="POST" action={returnTo ? `?returnTo=${encodeURIComponent(returnTo)}&/save` : '?/save'} class="form" novalidate>
		{#if error}<p class="form-error" role="alert">{error}</p>{/if}
		{#if based}<input type="hidden" name="version" value={based} />{/if}
		<div class="field">
			<label for="handle">Handle</label>
			{#if own}
				<input id="handle" value="@{own.handle}" disabled />
				<p class="hint">Your handle is fixed, so links to your profile keep working.</p>
			{:else}
				<input id="handle" name="handle" maxlength="30" autocomplete="off" autocapitalize="none" required defaultValue={v('handle', '')} />
				<p class="hint">3 to 30 lowercase letters, digits or underscores. It cannot be changed later.</p>
			{/if}
		</div>
		<div class="field">
			<label for="display_name">Display name</label>
			<input id="display_name" name="display_name" maxlength="60" required defaultValue={v('display_name', own?.display_name ?? '')} />
		</div>
		<div class="field">
			<label for="bio">Bio (optional)</label>
			<TextArea id="bio" name="bio" rows={3} maxlength={280} initial={v('bio', own?.bio ?? '')} />
		</div>
		<fieldset class="field">
			<legend>Disciplines (optional, up to five)</legend>
			{#each DISCIPLINES as value (value)}
				<label class="choice"><input type="checkbox" name="disciplines" {value} checked={chosen.has(value)} /> {disciplineLabel(value)}</label>
			{/each}
		</fieldset>
		<fieldset class="field">
			<legend>Home dropzone (optional)</legend>
			<label class="choice"><input type="radio" name="home" value="" checked={home === ''} /> None shown</label>
			{#if own?.home_venue}
				<label class="choice">
					<input type="radio" name="home" value={own.home_venue.id} checked={home === own.home_venue.id} />
					{own.home_venue.name}, {countryName(own.home_venue.country)}
				</label>
			{/if}
			{#each data.venues ?? [] as venue (venue.id)}
				{#if venue.id !== own?.home_venue?.id}
					<label class="choice">
						<input type="radio" name="home" value={venue.id} checked={home === venue.id} />
						{venue.name}, {countryName(venue.country)}
					</label>
				{/if}
			{/each}
			{#if data.venues && data.venues.length === 0}<p class="hint">No listed dropzone matches.</p>{/if}
		</fieldset>
		<label class="choice">
			<input type="checkbox" name="discoverable" checked={discoverable} />
			Let people find my profile (search and public link)
		</label>
		<p class="hint">
			Off: only people you have approved as followers can see your profile. You can change this at
			any time.
		</p>
		<div class="form-actions">
			<button class="button" type="submit" disabled={!data.emailVerified}>
				{own ? 'Save profile' : 'Create profile'}
			</button>
		</div>
		{#if !data.emailVerified}<p class="hint">Confirm your email address first.</p>{/if}
	</form>
{/if}
