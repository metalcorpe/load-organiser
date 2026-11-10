<script lang="ts">
	import { formatDay } from '#lib/listings.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const s = $derived(data.summary);
	const n = (value: number) => value.toLocaleString('en-GB');
	const jumps = (value: number) => `${n(value)} ${value === 1 ? 'jump' : 'jumps'}`;

	const groups = [
		{
			heading: 'Jumps',
			items: [
				{ href: '/jumps', name: 'Logbook', text: 'Every jump you logged, wherever you jumped.' },
				{ href: '/history', name: 'History', text: 'Totals, recent months and gear use.' },
				{ href: '/gear', name: 'Gear', text: 'Containers, canopies, AADs, rigs and service dates.' }
			]
		},
		{
			heading: 'Trips',
			items: [
				{ href: '/saved', name: 'Saved listings', text: 'Events you bookmarked on Discover.' },
				{ href: '/plans', name: 'Visit plans', text: 'Dates you plan to be somewhere.' },
				{ href: '/places', name: 'Private places', text: 'Fields only you can see.' }
			]
		},
		{
			heading: 'Your data',
			items: [
				{ href: '/profile/data', name: 'Export or restore', text: 'A copy of all your records as a file.' },
				{ href: '/submit', name: 'Suggestions and reports', text: 'What you sent and what happened to it.' }
			]
		}
	];
</script>

<svelte:head>
	<title>Records · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<h1>Records</h1>
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

{#each groups as group (group.heading)}
	<section aria-labelledby="g-{group.heading}">
		<h2 id="g-{group.heading}">{group.heading}</h2>
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
