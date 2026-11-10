<script lang="ts">
	import { RUNNING_COSTS, SUPPORT_URL } from '#lib/support.ts';

	const total = RUNNING_COSTS.reduce((sum, cost) => sum + cost.monthlyEur, 0);
	const eur = (value: number) => `€${value.toFixed(2)}`;
</script>

<svelte:head>
	<title>Support the beta · Load Organiser</title>
	<meta
		name="description"
		content="A voluntary way to help pay Load Organiser's running costs, and what those costs are."
	/>
</svelte:head>

<h1>Support the beta</h1>
<p class="lede">
	Load Organiser is free. Support is voluntary and unlocks nothing: your records, export and every
	feature work the same whether or not you give.
</p>

<section aria-labelledby="costs">
	<h2 id="costs">Running costs</h2>
	{#if RUNNING_COSTS.length === 0}
		<p data-testid="no-costs">
			Nothing is paid for yet: the beta has no paid hosting or services. Each cost will be listed
			here, with its monthly amount, when it starts.
		</p>
	{:else}
		<table>
			<thead>
				<tr><th scope="col">Item</th><th scope="col">Per month</th><th scope="col">Since</th></tr>
			</thead>
			<tbody>
				{#each RUNNING_COSTS as cost (cost.item)}
					<tr><td>{cost.item}</td><td>{eur(cost.monthlyEur)}</td><td>{cost.since}</td></tr>
				{/each}
			</tbody>
			<tfoot>
				<tr><th scope="row">Total</th><td>{eur(total)}</td><td></td></tr>
			</tfoot>
		</table>
	{/if}
	<p>Support is meant to cover these costs and a reserve for them, not to pay anyone.</p>
</section>

<section aria-labelledby="give">
	<h2 id="give">How to give</h2>
	<p>
		Through Ko-fi, an outside service:
		<a href={SUPPORT_URL} rel="external noopener noreferrer">support Load Organiser on Ko-fi</a>.
		Ko-fi handles the payment under its own terms and privacy policy. This site does not record
		whether you gave.
	</p>
</section>

<style>
	section {
		margin-top: 1.75rem;
	}

	table {
		border-collapse: collapse;
	}

	th,
	td {
		padding: 0.35rem 1rem 0.35rem 0;
		text-align: left;
	}
</style>
