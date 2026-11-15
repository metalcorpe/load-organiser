<script lang="ts" module>
	export type Destination = {
		href: string;
		/** Short name of the place or setting. */
		label: string;
		/** What is there now, in a few words ("2 plans · 3 saved", "B licence"); optional. */
		summary?: string | null;
		/** A setting's row ends in this word ("Edit") instead of a chevron. */
		verb?: string;
		/** An anchor id on the row, for links that point at it. */
		id?: string;
	};
	export type DestinationGroup = {
		id: string;
		heading: string;
		items: Destination[];
		/** Supporting links: quieter rows. */
		quiet?: boolean;
	};
</script>

<script lang="ts">
	/**
	 * Where things live, as grouped rows: each row is one link, a 44px target or more, with an
	 * optional summary under its name. A setting ends in its verb ("Edit"); a place, in a
	 * chevron. One column on a phone; groups side by side as the container widens.
	 */
	let { groups }: { groups: DestinationGroup[] } = $props();
</script>

<!-- The outer box is the size container; a container query styles only what is inside it. -->
<div class="destinations">
<div class="groups">
	{#each groups as group (group.id)}
		<section class="group" class:quiet={group.quiet} aria-labelledby="dest-{group.id}">
			<h2 id="dest-{group.id}">{group.heading}</h2>
			<ul>
				{#each group.items as item (item.href + item.label)}
					<li>
						<a href={item.href} id={item.id}>
							<span class="text">
								<!-- The hidden verb ends in a no-break space, which is never trimmed: "Edit Licence". -->
								<span class="label"
									>{#if item.verb}<span class="visually-hidden">{item.verb}&nbsp;</span>{/if}{item.label}</span
								>
								{#if item.summary}<span class="summary">{item.summary}</span>{/if}
							</span>
							{#if item.verb}
								<span class="verb" aria-hidden="true">{item.verb}</span>
							{:else}
								<span class="chevron" aria-hidden="true"></span>
							{/if}
						</a>
					</li>
				{/each}
			</ul>
		</section>
	{/each}
</div>
</div>

<style>
	.destinations {
		container-type: inline-size;
	}

	.groups {
		display: grid;
		gap: 1.25rem;
	}

	/* Two columns of groups when the container has room for two readable rows. */
	@container (min-width: 44rem) {
		.groups {
			grid-template-columns: repeat(2, minmax(0, 1fr));
			align-items: start;
		}
	}

	h2 {
		margin: 0 0 0.4rem;
		color: var(--muted);
		font-size: 0.95rem;
		font-weight: 650;
	}

	ul {
		margin: 0;
		padding: 0;
		list-style: none;
		border-radius: var(--radius);
		background: var(--surface);
		box-shadow: 0 0 0 1px var(--border);
	}

	li + li {
		border-top: 1px solid var(--border);
	}

	a {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		min-height: 52px;
		padding: 0.6rem 0.9rem;
		color: var(--fg);
		text-decoration: none;
	}

	li:first-child a {
		border-radius: var(--radius) var(--radius) 0 0;
	}

	li:last-child a {
		border-radius: 0 0 var(--radius) var(--radius);
	}

	li:only-child a {
		border-radius: var(--radius);
	}

	a:hover {
		background: var(--surface-soft);
	}

	a:hover .label {
		text-decoration: underline;
	}

	a:focus-visible {
		outline-offset: -3px;
	}

	.text {
		display: grid;
		gap: 0.1rem;
		flex: 1;
		min-width: 0;
	}

	.label {
		font-weight: 650;
	}

	/* A summary can hold a handle: one long unbroken string. */
	.summary {
		color: var(--muted);
		font-size: 0.9rem;
		overflow-wrap: anywhere;
	}

	/* A setting's verb: the row's one orange word, the action it leads to. */
	.verb {
		flex: none;
		color: var(--accent);
		font-weight: 650;
	}

	.chevron {
		flex: none;
		width: 0.5rem;
		height: 0.5rem;
		margin-right: 0.2rem;
		border-right: 2px solid var(--muted);
		border-bottom: 2px solid var(--muted);
		transform: rotate(-45deg);
	}

	a:hover .chevron {
		border-color: var(--accent);
	}

	/* Supporting links: no card, smaller rows, so the main groups lead. */
	.quiet ul {
		background: none;
		box-shadow: none;
	}

	.quiet li + li {
		border-top: 0;
	}

	.quiet a {
		min-height: 44px;
		padding: 0.25rem 0;
	}

	.quiet a:hover {
		background: none;
	}

	.quiet .label {
		font-weight: 600;
		color: var(--accent);
	}

	.quiet .chevron {
		display: none;
	}
</style>
