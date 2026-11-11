<script lang="ts">
	/** Where a member's own records live: shown on Records and on the Me tab. */
	const groups = [
		{
			id: 'jumps',
			heading: 'Jumps',
			items: [
				{ href: '/jumps', name: 'Logbook', text: 'Every jump you logged, wherever you jumped.' },
				{ href: '/history', name: 'History', text: 'Totals, recent months and gear use.' },
				{ href: '/gear', name: 'Gear', text: 'Containers, canopies, AADs, rigs and service dates.' }
			]
		},
		{
			id: 'trips',
			heading: 'Trips',
			items: [
				{ href: '/saved', name: 'Saved listings', text: 'Events you bookmarked.' },
				{ href: '/plans', name: 'Visit plans', text: 'Dates you plan to be somewhere.' },
				{ href: '/places', name: 'Private places', text: 'Fields only you can see.' }
			]
		},
		{
			id: 'data',
			heading: 'Your data',
			items: [
				{ href: '/profile/data', name: 'Export or restore', text: 'A copy of all your records as a file.' },
				{ href: '/submit', name: 'Suggestions and reports', text: 'What you sent and what happened to it.' }
			]
		}
	];
</script>

{#each groups as group (group.id)}
	<section aria-labelledby="tiles-{group.id}">
		<h2 id="tiles-{group.id}">{group.heading}</h2>
		<ul class="tiles">
			{#each group.items as item (item.href)}
				<li>
					<a class="tile" href={item.href}>
						<span class="tile-name">{item.name}</span>
						<span class="tile-text">{item.text}</span>
					</a>
				</li>
			{/each}
		</ul>
	</section>
{/each}

<style>
	h2 {
		font-size: 1rem;
		color: var(--muted);
		margin: 1.25rem 0 0.5rem;
	}

	.tiles {
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(min(100%, 14rem), 1fr));
		gap: 0.5rem;
		list-style: none;
		padding: 0;
		margin: 0;
	}

	.tile {
		display: grid;
		gap: 0.15rem;
		height: 100%;
		min-height: 44px;
		padding: 0.75rem 0.9rem;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		background: var(--surface);
		color: var(--fg);
		text-decoration: none;
	}

	.tile:hover {
		border-color: var(--accent);
	}

	.tile-name {
		font-weight: 650;
		color: var(--accent);
	}

	.tile-text {
		color: var(--muted);
		font-size: 0.92rem;
	}
</style>
