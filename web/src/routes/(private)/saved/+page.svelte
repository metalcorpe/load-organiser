<script lang="ts">
	import PrivacyLabel from '#lib/components/PrivacyLabel.svelte';
	import { CATEGORY_LABEL, formatRange, listingMessage, statusLabel } from '#lib/listings.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();
</script>

<svelte:head>
	<title>Saved listings · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<p><a href="/records">Records</a></p>
<h1>Saved listings</h1>
<PrivacyLabel />
<p class="lede">
	Bookmarks only you can see. Saving does not register you, reserve a place or tell the organizer
	anything.
</p>

{#if form && 'error' in form}
	<p class="form-error" role="alert">{listingMessage(form.error)}</p>
{:else if form && 'removed' in form}
	<p role="status">Removed from saved.</p>
{/if}

{#if !data.saved.ok}
	<p class="form-error" role="alert">{listingMessage(data.saved.reason)}</p>
{:else if data.saved.items.length === 0}
	<p>You have not saved any listings. <a href="/">Browse listings</a>.</p>
{:else}
	<ul class="results rows" aria-label="Saved listings">
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
					<form method="POST" action="?/remove">
						<input type="hidden" name="id" value={entry.opportunity_id} />
						<button class="button secondary small" type="submit">Remove</button>
					</form>
				</span>
			</li>
		{/each}
	</ul>
{/if}

<style>
	.title {
		font-weight: 600;
		flex-basis: 100%;
	}

	.meta {
		color: var(--muted);
		flex-basis: 100%;
	}

	.row {
		display: flex;
		gap: 1rem;
		align-items: center;
		flex-basis: 100%;
	}

</style>
