<script lang="ts">
	/**
	 * Dates and jump-count limits coming due on the owner's own gear, each linked to its
	 * component. Shown compactly on the Logbook (due soon or overdue) and in full on Gear.
	 */
	import { dueBasis, dueText, itemState, type DueIn } from '#lib/gear.ts';

	let {
		items,
		today,
		label,
		detailed = false
	}: { items: DueIn[]; today: string; label: string; detailed?: boolean } = $props();
</script>

<ul class="due" aria-label={label}>
	{#each items as item (item.component.id + item.kind + (item.service_kind ?? ''))}
		{@const state = itemState(item, today)}
		<li class={state}>
			{#if state === 'overdue'}<strong>{dueText(item, today)}</strong>{:else}<span
					>{dueText(item, today)}</span
				>{/if}
			<a href="/gear/{item.component.id}">{item.component.label}</a>
			{#if detailed}<span class="basis">{dueBasis(item)}</span>{/if}
		</li>
	{/each}
</ul>

<style>
	.due {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 0.4rem;
	}

	li {
		display: flex;
		flex-wrap: wrap;
		column-gap: 0.5rem;
		align-items: baseline;
		padding-left: 0.6rem;
		border-left: 3px solid var(--border);
	}

	li.overdue {
		border-left-color: var(--bad-fg);
	}

	.basis {
		flex-basis: 100%;
		color: var(--muted);
		font-size: 0.9rem;
	}
</style>
