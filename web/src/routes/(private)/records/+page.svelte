<script lang="ts">
	import PrivacyLabel from '#lib/components/PrivacyLabel.svelte';
	import RecordTiles from '#lib/components/RecordTiles.svelte';
	import { formatDay } from '#lib/listings.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const s = $derived(data.summary);
	const n = (value: number) => value.toLocaleString('en-GB');
	const jumps = (value: number) => `${n(value)} ${value === 1 ? 'jump' : 'jumps'}`;

</script>

<svelte:head>
	<title>Records · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<h1>Records</h1>
<PrivacyLabel />
<p class="lede">Private to you.</p>

{#if s}
	<section class="summary" aria-label="Summary">
		{#if s.recorded === 0 && !s.prior}
			<p><a href="/jumps/new">Log your first jump</a>. Only the date, place and type are needed.</p>
		{:else}
			<p class="total">
				{#if s.lifetime !== null}
					<strong>{jumps(s.lifetime)}</strong>
					<span class="hint">({n(s.prior ?? 0)} declared + {n(s.since ?? 0)} recorded)</span>
				{:else}
					<strong>{jumps(s.recorded)}</strong> recorded
				{/if}
			</p>
			{#if s.lastJumpOn}<p class="hint">Last jump {formatDay(s.lastJumpOn)}</p>{/if}
		{/if}
	</section>
{/if}

<RecordTiles />

<style>
	.summary {
		margin: 0.5rem 0 1.25rem;
		padding: 0.85rem 1rem;
		border-radius: var(--radius);
		background: var(--accent-soft);
	}

	.summary p {
		margin: 0;
	}

	.total strong {
		font-size: 1.35rem;
	}

</style>
