<script lang="ts">
	import type { PostOut } from '#lib/contracts/index.ts';
	import { countryName } from '#lib/countries.ts';
	import { JUMP_TYPE_LABEL, altitudeText } from '#lib/jumps.ts';
	import { formatDay } from '#lib/listings.ts';
	import { AUDIENCE_LABEL } from '#lib/posts.ts';

	let {
		post,
		link = true,
		author = true,
		preview = false
	}: { post: PostOut; link?: boolean; author?: boolean; preview?: boolean } = $props();
	const altitude = $derived(
		post.exit_altitude
			? altitudeText(post.exit_altitude.value, null, post.exit_altitude.unit, post.exit_altitude.datum)
			: null
	);
	const published = $derived(post.published_at.slice(0, 10));
</script>

<article class="card" aria-label="Jump on {formatDay(post.jumped_on)}">
	<p class="title">
		{#if link}<a href="/posts/{post.id}">Jump on {formatDay(post.jumped_on)}</a>{:else}Jump on
			{formatDay(post.jumped_on)}{/if}
	</p>
	{#if author}
		<p class="meta">
			by <a href="/people/{post.author.handle}">{post.author.display_name}</a>
			<span class="wrap-anywhere">(@{post.author.handle})</span>
		</p>
	{/if}
	<dl class="facts">
		{#if post.jump_type}<dt>Type</dt><dd>{JUMP_TYPE_LABEL[post.jump_type] ?? post.jump_type}</dd>{/if}
		{#if post.venue}
			<dt>Dropzone</dt>
			<dd><a href="/dz/{post.venue.id}">{post.venue.name}</a>, {countryName(post.venue.country)}</dd>
		{/if}
		{#if altitude}<dt>Exit altitude</dt><dd>{altitude}</dd>{/if}
		{#if post.freefall_seconds !== null}<dt>Freefall</dt><dd>{post.freefall_seconds} s</dd>{/if}
	</dl>
	{#if post.caption}<p class="caption wrap-anywhere">{post.caption}</p>{/if}
	{#if post.link}
		<p class="wrap-anywhere">
			<a href={post.link} rel="noopener noreferrer nofollow ugc" target="_blank">{post.link}</a>
		</p>
	{/if}
	<p class="meta">
		Self-reported, not verified · jumped {formatDay(post.jumped_on)} ·
		{#if preview}not published yet{:else}published {formatDay(published)}{/if}{post.is_owner
			? ` · ${AUDIENCE_LABEL[post.audience]}`
			: ''}
	</p>
</article>
