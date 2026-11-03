<script lang="ts">
	import { page } from '$app/state';
	import { formatDay } from '#lib/listings.ts';
	import { reviewMessage } from '#lib/review-messages.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();

	const KIND_LABEL: Record<string, string> = {
		suggest_venue: 'Suggest a dropzone',
		suggest_listing: 'Suggest an event, camp or course',
		correction: 'Correct information',
		report: 'Report a problem'
	};
	const STATUS_LABEL: Record<string, string> = {
		open: 'Waiting for review',
		accepted: 'Accepted',
		declined: 'Not taken up'
	};
	const sent = $derived(page.url.searchParams.get('sent') === '1');
	const kinds = $derived(
		data.target ? ['correction', 'report'] : ['suggest_listing', 'suggest_venue']
	);
</script>

<svelte:head>
	<title>Suggest or report · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<h1>Suggest or report</h1>
<p class="lede">
	Tell the maintainer about a missing listing, outdated details or a problem. Nothing changes until a
	person reviews it against a source. Your name and email are not shown to the reviewer.
</p>

{#if sent}<p role="status" class="ok">Sent. You can follow its status below.</p>{/if}

<section aria-labelledby="form-heading">
	<h2 id="form-heading">{data.target && data.title ? `About: ${data.title}` : 'New submission'}</h2>
	{#if !data.emailVerified}
		<p class="hint">Confirm your email address on your <a href="/profile">profile</a> first.</p>
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
			<p class="hint">The organizer's or dropzone's own page that shows this.</p>
		</div>
		<div class="form-actions"><button class="button" type="submit">Send</button></div>
	</form>
</section>

<h2>Your submissions</h2>
{#if !data.mine.ok}
	<p class="form-error" role="alert">{reviewMessage(data.mine.reason)}</p>
{:else if data.mine.items.length === 0}
	<p>You have not sent anything yet.</p>
{:else}
	<ul class="results" aria-label="Your submissions">
		{#each data.mine.items as item (item.id)}
			<li>
				<span class="title">{KIND_LABEL[item.kind]}</span>
				<span class="tag">{STATUS_LABEL[item.status]}</span>
				<span class="meta">Sent {formatDay(item.created_at.slice(0, 10))}</span>
				<span class="meta message">{item.message}</span>
				{#if item.resolution_note}<span class="meta">Reviewer: {item.resolution_note}</span>{/if}
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

	.choice {
		display: flex;
		gap: 0.5rem;
		align-items: center;
		min-height: 44px;
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
