<script lang="ts">
	/** Jump currency guidance (USPA SIM 5-2) from the jumper's own entries. Shown on Logbook and History. */
	import { onMount } from 'svelte';
	import type { CurrencyOut } from '#lib/contracts/index.ts';
	import { currencyState, localToday } from '#lib/currency.ts';
	import { progressSummary, type ProgressIn } from '#lib/licence-progress.ts';

	let {
		currency,
		today: serverToday,
		progress = null
	}: {
		currency: CurrencyOut;
		today: string;
		/** The Logbook's compact next-licence line (History shows the full section instead). */
		progress?: ProgressIn | null;
	} = $props();
	const nextLicence = $derived(progress ? progressSummary(progress) : null);
	// The server's UTC day until the browser gives the jumper's own calendar day.
	// svelte-ignore state_referenced_locally
	let today = $state(serverToday);
	onMount(() => {
		today = localToday();
	});
	const status = $derived(currencyState(currency, today));
	const id = $props.id();
</script>

<section class="currency {status.kind}" aria-labelledby="{id}-title">
	<h2 id="{id}-title">Jump currency</h2>
	{#if status.kind === 'no_licence'}
		<p><a href="/profile#licence-heading">Set your licence</a> to see your jump currency.</p>
	{:else if status.kind === 'no_jumps'}
		<p>No jumps recorded yet, so there is no currency to show.</p>
	{:else}
		<p data-testid="currency-status"><strong>{status.text}</strong></p>
	{/if}
	{#if nextLicence}
		<p data-testid="licence-progress">
			{nextLicence} <a href="/history#next-licence">Next licence details</a>
		</p>
	{/if}
	<p class="hint">
		Guidance computed from your own entries, not a verified status (USPA SIM 5-2).
		<!-- The details matter only once there is a computed status to read them against. -->
		{#if status.kind !== 'no_licence' && status.kind !== 'no_jumps'}
			Every jump type counts, tandem included: the logbook does not record whether you were the
			instructor or the passenger. A prior jump count has no dates and adds nothing.
		{/if}
	</p>
</section>

<style>
	.currency {
		margin: 0.75rem 0 1rem;
		padding: 0.75rem 1rem;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		background: var(--surface);
	}

	.currency.lapsed {
		border-color: var(--bad-fg);
	}

	h2 {
		font-size: 1rem;
		margin: 0 0 0.25rem;
	}

	p {
		margin: 0.25rem 0 0;
	}
</style>
