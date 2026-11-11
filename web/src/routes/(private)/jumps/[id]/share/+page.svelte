<script lang="ts">
	import TextArea from '#lib/components/TextArea.svelte';
	import { page } from '$app/state';
	import JumpCard from '#lib/components/JumpCard.svelte';
	import type { PostOut } from '#lib/contracts/index.ts';
	import { formatDay } from '#lib/listings.ts';
	import { AUDIENCE_LABEL, SHARE_PARTS, postMessage } from '#lib/posts.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();
	const s = $derived(data.sharing);
	const jump = $derived(s.jump);
	const profile = $derived(s.profile);
	const errorFor = (name: string) =>
		form && form.form === name && 'error' in form ? postMessage(form.error) : undefined;

	// The values of an earlier submit (a preview or a refused publish), else defaults.
	const chosen = $derived(
		form && 'chosen' in form && form.chosen
			? form.chosen
			: { shares: ['type'], caption: '', link: '', audience: 'followers' }
	);
	const previewing = $derived(form?.form === 'preview');
	// The version loaded with this page: the preview shows it and Publish sends it.
	const based = $derived(jump.version);
	const available: Record<string, boolean> = $derived({
		type: jump.jump_type !== 'unspecified',
		venue: jump.listed_venue !== null,
		altitude: jump.exit_altitude !== null,
		freefall: jump.freefall_seconds !== null
	});
	const blocked = $derived(
		!profile
			? 'profile_required'
			: profile.hidden
				? 'profile_hidden'
				: profile.publishing_restricted
					? 'publishing_restricted'
					: null
	);
	const preview: PostOut | null = $derived(
		previewing && profile
			? {
					id: '00000000-0000-0000-0000-000000000000',
					author: { handle: profile.handle, display_name: profile.handle },
					jumped_on: jump.jumped_on,
					jump_type: chosen.shares.includes('type') ? jump.jump_type : null,
					venue: chosen.shares.includes('venue') ? jump.listed_venue : null,
					exit_altitude: chosen.shares.includes('altitude') ? jump.exit_altitude : null,
					freefall_seconds: chosen.shares.includes('freefall') ? jump.freefall_seconds : null,
					caption: chosen.caption.trim() || null,
					link: chosen.link || null,
					published_at: new Date().toISOString(),
					audience: chosen.audience === 'public' ? 'public' : 'followers',
					is_owner: true
				}
			: null
	);
</script>

<svelte:head>
	<title>Share jump on {formatDay(jump.jumped_on)} · Logbook · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<p><a href="/jumps/{jump.id}">Jump on {formatDay(jump.jumped_on)}</a></p>
<h1>Share this jump</h1>
<p class="lede">
	Your logbook stays private. A post shares only the values you choose below, copied from the jump
	as it is now. It does not add a jump or change your totals.
</p>

{#if page.url.searchParams.get('published')}<p role="status" class="ok">Published.</p>{/if}
{#if page.url.searchParams.get('changed')}<p role="status" class="ok">Audience changed.</p>{/if}
{#if page.url.searchParams.get('unpublished')}
	<p role="status" class="ok">Unpublished. The jump stays in your logbook.</p>
{/if}

{#if s.post}
	<h2>Published</h2>
	<JumpCard post={s.post} author={false} />
	<p class="hint">
		If you edit the date{s.post.jump_type ? ', type' : ''}{s.post.venue ? ', dropzone' : ''}{s.post
			.exit_altitude
			? ', exit altitude'
			: ''}{s.post.freefall_seconds !== null ? ', freefall time' : ''} of this jump, the post is withdrawn
		first; you can publish again from a new preview. Other edits leave it as it is.
	</p>

	<h3>Who can see it</h3>
	<form method="POST" action="?/audience" class="form">
		{#if errorFor('audience')}<p class="form-error" role="alert">{errorFor('audience')}</p>{/if}
		<input type="hidden" name="post" value={s.post.id} />
		<input type="hidden" name="version" value={s.post.version} />
		<fieldset>
			<legend>Audience</legend>
			{#each Object.entries(AUDIENCE_LABEL) as [value, label] (value)}
				<label class="choice">
					<input type="radio" name="audience" {value} checked={s.post.audience === value} />
					{label}
				</label>
			{/each}
		</fieldset>
		<div class="form-actions">
			<button class="button secondary" type="submit" disabled={!data.emailVerified}>
				Change audience
			</button>
		</div>
	</form>

	<h3>Unpublish</h3>
	<form method="POST" action="?/unpublish" class="form">
		{#if errorFor('unpublish')}<p class="form-error" role="alert">{errorFor('unpublish')}</p>{/if}
		<input type="hidden" name="post" value={s.post.id} />
		<input type="hidden" name="version" value={s.post.version} />
		<label class="choice"><input type="checkbox" name="confirm" /> Unpublish this post</label>
		<p class="hint">
			It disappears from your profile and its link for everyone. The jump stays in your logbook.
			Copies or screenshots others already made cannot be recalled.
		</p>
		<div class="form-actions">
			<button class="button secondary" type="submit" disabled={!data.emailVerified}>Unpublish</button>
		</div>
	</form>
{:else if blocked}
	<p class="form-error" role="alert">{postMessage(blocked)}</p>
	{#if blocked === 'profile_required'}<p><a href="/profile/public">Create your public profile</a></p>{/if}
{:else}
	{#if !data.emailVerified}
		<p class="hint">Confirm your email address on your <a href="/profile">profile</a> to publish.</p>
	{/if}
	{#if errorFor('share')}<p class="form-error" role="alert">{errorFor('share')}</p>{/if}

	{#if preview}
		<h2>Preview</h2>
		<p class="hint">This is everything that will be shared, under @{profile?.handle}.</p>
		<JumpCard post={preview} link={false} author={false} preview />
		<p class="hint">
			{chosen.audience === 'public'
				? 'Public: anyone can see it, also signed out, while your profile is discoverable. A block stops signed-in access only.'
				: 'Approved followers: everyone you have approved, and people you approve later. Removing a follower or blocking someone removes their access.'}
		</p>
		<!-- Publishes exactly what was previewed, from the jump version previewed. -->
		<form method="POST" action="?/publish" class="form">
			<input type="hidden" name="version" value={based} />
			{#each chosen.shares as part (part)}<input type="hidden" name="shares" value={part} />{/each}
			<input type="hidden" name="caption" value={chosen.caption} />
			<input type="hidden" name="link" value={chosen.link} />
			<input type="hidden" name="audience" value={chosen.audience} />
			<div class="form-actions">
				<button class="button" type="submit" disabled={!data.emailVerified}>Publish</button>
			</div>
		</form>
		<h2>Change what is shared</h2>
	{/if}

	<form method="POST" action="?/preview" class="form">
		<input type="hidden" name="version" value={based} />
		<fieldset>
			<legend>What to share</legend>
			<p class="hint">
				The jump date ({formatDay(jump.jumped_on)}) is always shared. Never shared: notes, your
				links, equipment, serials, jump number, exit time, deployment altitude or a private place.
			</p>
			{#each SHARE_PARTS as part (part.value)}
				<label class="choice">
					<input
						type="checkbox"
						name="shares"
						value={part.value}
						checked={available[part.value] && chosen.shares.includes(part.value)}
						disabled={!available[part.value]}
					/>
					{part.label}{available[part.value]
						? ''
						: part.value === 'venue'
							? ' (only a listed dropzone can be shared)'
							: ' (not recorded)'}
				</label>
			{/each}
		</fieldset>
		<div class="field">
			<label for="caption">Caption (optional, up to 280 characters)</label>
			<TextArea id="caption" name="caption" maxlength={280} rows={3} initial={chosen.caption} />
		</div>
		<div class="field">
			<label for="link">Link (optional, e.g. a video you host elsewhere)</label>
			<input id="link" name="link" type="url" maxlength="2048" value={chosen.link} />
		</div>
		<fieldset>
			<legend>Who can see it</legend>
			<label class="choice">
				<input type="radio" name="audience" value="followers" checked={chosen.audience !== 'public'} />
				Approved followers, including people you approve later
			</label>
			<label class="choice">
				<input
					type="radio"
					name="audience"
					value="public"
					checked={chosen.audience === 'public'}
					disabled={!profile?.discoverable}
				/>
				Public{profile?.discoverable ? '' : ' (needs a discoverable profile)'}
			</label>
		</fieldset>
		<div class="form-actions">
			<button class="button secondary" type="submit">{preview ? 'Update preview' : 'Preview'}</button>
		</div>
	</form>
{/if}
