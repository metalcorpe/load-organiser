<script lang="ts">
	import { page } from '$app/state';
	import Notice from '#lib/components/Notice.svelte';
	import { formatDay } from '#lib/listings.ts';
	import { reviewMessage } from '#lib/review-messages.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();

	const KIND_LABEL: Record<string, string> = {
		suggest_venue: 'Suggest a dropzone',
		suggest_listing: 'Suggest an event, camp or course',
		correction: 'Correct information',
		report: 'Report a problem',
		feedback: 'Feedback about the beta'
	};
	const STATUS_LABEL: Record<string, string> = {
		open: 'Waiting for review',
		accepted: 'Accepted',
		declined: 'Not taken up'
	};
	const sent = $derived(page.url.searchParams.get('sent') === '1');
	const kinds = $derived(
		data.target ? ['correction', 'report'] : ['suggest_listing', 'suggest_venue', 'feedback']
	);
</script>

<svelte:head>
	<title>Suggest or report · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<h1>Suggest or report</h1>
<p class="lede">
	Tell us about a missing listing, outdated details or a problem, or send feedback about the beta.
	We check each one before changing a listing. The people who check it don't see your name or email.
</p>

{#if sent}<p role="status" class="ok">Received. We'll review it. You can follow it below.</p>{/if}

<section aria-labelledby="form-heading">
	<h2 id="form-heading">{data.target && data.title ? `About: ${data.title}` : 'New submission'}</h2>
	{#if data.paused}
		<Notice title="Sending is paused" tone="warn">
			<p>You can't send anything right now. Try again later. What you sent before is below.</p>
		</Notice>
	{:else}
	{#if !data.emailVerified}
		<p class="hint">Confirm your email address on your <a href="/profile">profile</a> to send.</p>
	{/if}
	<form method="POST" class="form" novalidate>
		{#if form && 'error' in form}
			<p class="form-error" role="alert">{reviewMessage(form.error)}</p>
		{/if}
		<input
			type="hidden"
			name="client_key"
			value={(form && 'values' in form && form.values?.client_key) || data.clientKey}
		/>
		{#if data.target}
			<input type="hidden" name="target_kind" value={data.target.kind} />
			<input type="hidden" name="target_id" value={data.target.id} />
		{/if}
		<fieldset class="field">
			<legend>What is this?</legend>
			{#each kinds as kind (kind)}
				<label class="choice">
					<input type="radio" name="kind" value={kind} checked={kind === data.kind || (!kinds.includes(data.kind) && kind === kinds[0])} />
					{KIND_LABEL[kind]}
				</label>
			{/each}
		</fieldset>
		<div class="field">
			<label for="message">Details</label>
			<textarea id="message" name="message" maxlength="1000" rows="5" required
				>{form && 'values' in form ? form.values.message : ''}</textarea
			>
			<p class="hint">Up to 1,000 characters. Do not include anyone's private details.</p>
		</div>
		<div class="field">
			<label for="source_url">Source link (optional)</label>
			<input
				id="source_url"
				name="source_url"
				type="url"
				maxlength="2048"
				defaultValue={form && 'values' in form ? form.values.source_url : ''}
			/>
			<p class="hint">A link to the organizer's or dropzone's own page helps us check it.</p>
		</div>
		<div class="form-actions"><button class="button" type="submit">Send</button></div>
	</form>
	{/if}
</section>

<h2>Your submissions</h2>
{#if !data.mine.ok}
	<p class="form-error" role="alert">{reviewMessage(data.mine.reason)}</p>
{:else if data.mine.items.length === 0}
	<p>You have not sent anything yet.</p>
{:else}
	<ul class="results rows" aria-label="Your submissions">
		{#each data.mine.items as item (item.id)}
			<li>
				<span class="title">{KIND_LABEL[item.kind]}</span>
				<span class="tag">{STATUS_LABEL[item.status]}</span>
				<span class="meta">Sent {formatDay(item.created_at.slice(0, 10))}</span>
				<span class="meta message">{item.message}</span>
				{#if item.resolution_note}<span class="meta">Reply: {item.resolution_note}</span>{/if}
			</li>
		{/each}
	</ul>
{/if}

<style>
	.ok {
		color: var(--ok-fg);
		font-weight: 600;
	}

	fieldset {
		border: 0;
		padding: 0;
		margin: 0;
	}

	legend {
		font-weight: 650;
		margin-bottom: 0.3rem;
	}


	.title {
		font-weight: 600;
	}

	.meta {
		color: var(--muted);
		flex-basis: 100%;
		overflow-wrap: anywhere;
	}

	.message {
		white-space: pre-line;
	}
</style>
