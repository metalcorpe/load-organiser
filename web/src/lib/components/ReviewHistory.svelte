<script lang="ts">
	let { events }: { events: { kind: string; detail: Record<string, unknown>; created_at: string }[] } =
		$props();
	const when = (iso: string) => iso.slice(0, 16).replace('T', ' ') + ' UTC';
</script>

<details>
	<summary>History ({events.length})</summary>
	<ol class="history">
		{#each [...events].reverse() as event, index (index)}
			<li>
				<span class="kind">{event.kind.replaceAll('_', ' ')}</span>
				<span class="when">{when(event.created_at)}</span>
				<code>{JSON.stringify(event.detail)}</code>
			</li>
		{/each}
	</ol>
</details>

<style>
	.history {
		padding-left: 1.2rem;
	}

	.history li {
		margin: 0.35rem 0;
	}

	.kind {
		font-weight: 600;
	}

	.when {
		color: var(--muted);
		margin-left: 0.5rem;
	}

	code {
		display: block;
		overflow-wrap: anywhere;
		font-size: 0.85rem;
		color: var(--muted);
	}
</style>
