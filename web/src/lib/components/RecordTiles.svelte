<script lang="ts" module>
	export type RecordLink = { href: string; name: string; text: string };
	export type RecordGroup = { id: string; heading: string; items: RecordLink[] };
</script>

<script lang="ts">
	/**
	 * Where a member's own records live. Records shows them as tiles with a line each; the Me
	 * tab shows the same groups as a compact list of links (`compact`), with its own groups
	 * (people, account) added after them (`extra`).
	 */
	let { compact = false, extra = [] }: { compact?: boolean; extra?: RecordGroup[] } = $props();

	const records: RecordGroup[] = [
		{
			id: 'jumps',
			heading: 'Jumps',
			items: [
				{ href: '/jumps', name: 'Logbook', text: 'Every jump you logged, wherever you jumped.' },
				{ href: '/history', name: 'History', text: 'Totals, recent months and gear use.' },
				{ href: '/stats', name: 'Statistics', text: 'Your jumps by type, year and place.' },
				{
					href: '/records/print',
					name: 'Printable logbook',
					text: 'Your jumps on paper or as a PDF, with a column for signatures.'
				},
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
				{
					href: '/records/import',
					name: 'Import from a spreadsheet',
					text: 'Bring the jumps you already logged in from a CSV file.'
				},
				{ href: '/submit', name: 'Suggestions and reports', text: 'What you sent and what happened to it.' }
			]
		}
	];
	const groups = $derived([...records, ...extra]);
</script>

{#if compact}
	<!-- One card: each group a short heading over its links, which wrap on as many lines as
	     they need; side by side from 40rem. -->
	<dl class="compact">
		{#each groups as group (group.id)}
			<div class="group">
				<dt id="links-{group.id}">{group.heading}</dt>
				<dd>
					<ul class="links" aria-labelledby="links-{group.id}">
						{#each group.items as item (item.href)}
							<li><a href={item.href}>{item.name}</a></li>
						{/each}
					</ul>
				</dd>
			</div>
		{/each}
	</dl>
{:else}
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
{/if}

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

	/* Compact: one card, groups separated by a rule; each link is a 44px-tall target. */
	/* Not the page's label/value grid (app.css dl): a block of groups. */
	.compact {
		container-type: inline-size;
		display: block;
		margin: 1rem 0;
		padding: 0.25rem 0.9rem;
		border: 1px solid var(--border);
		border-radius: var(--radius);
		background: var(--surface);
	}

	.group {
		padding: 0.35rem 0;
	}

	.group + .group {
		border-top: 1px solid var(--border);
	}

	dt {
		color: var(--muted);
		font-size: 0.85rem;
		font-weight: 650;
	}

	dd {
		margin: 0;
		overflow-wrap: normal;
	}

	.links {
		display: flex;
		flex-wrap: wrap;
		gap: 0 1.1rem;
		list-style: none;
		padding: 0;
		margin: 0;
	}

	.links a {
		display: inline-flex;
		align-items: center;
		min-height: 44px;
		font-weight: 600;
	}

	/* By the card's own width, not the screen's: beside the Me page's main column it stays
	   narrow, heading over links. */
	@container (min-width: 30rem) {
		.group {
			display: grid;
			grid-template-columns: 9rem minmax(0, 1fr);
			column-gap: 1rem;
		}

		/* Level with the first row of links. */
		dt {
			align-self: start;
			line-height: 44px;
		}
	}
</style>
