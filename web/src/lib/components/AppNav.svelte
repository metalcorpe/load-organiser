<script lang="ts">
	import { page } from '$app/state';
	import { PRIMARY_NAV, isCurrentTab } from '#lib/navigation.ts';
	import NavIcon from './NavIcon.svelte';
</script>

<nav aria-label="Primary">
	<ul>
		{#each PRIMARY_NAV as item (item.href)}
			{@const current = isCurrentTab(item, page.url.pathname)}
			<li>
				<a href={item.href} aria-current={current ? 'page' : undefined}>
					<NavIcon name={item.icon} />
					<span>{item.label}</span>
				</a>
			</li>
		{/each}
	</ul>
</nav>

<style>
	nav {
		position: fixed;
		inset: auto 0 0 0;
		z-index: 10;
		background: var(--surface);
		border-top: 1px solid var(--border);
		padding-bottom: env(safe-area-inset-bottom);
	}

	ul {
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		max-width: 40rem;
		margin: 0 auto;
		padding: 0;
		list-style: none;
	}

	a {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 2px;
		min-height: var(--nav-height);
		padding: 6px 2px;
		color: var(--muted);
		font-size: 0.72rem;
		line-height: 1.15;
		text-align: center;
		text-decoration: none;
	}

	/* A label never breaks inside its word. On a phone it shrinks with the tab's width
	   (3.4vw) down to a floor that still grows with the text size, so at 320px and 200%
	   text "Explore" stays whole. */
	a span {
		white-space: nowrap;
		overflow-wrap: normal;
		word-break: keep-all;
		font-size: clamp(0.55rem, 3.4vw, 1em);
	}

	a[aria-current='page'] {
		color: var(--accent);
		font-weight: 750;
		/* The bar across the top of the tab (phones) or the bottom (large screens), drawn as a
		   background: an inset shadow on a tab whose edge falls on a half pixel left a thin
		   accent line down its side. */
		background: linear-gradient(var(--accent), var(--accent)) top / 100% 3px no-repeat;
	}

	@media (min-width: 48rem) {
		nav {
			position: static;
			border-top: 0;
			border-bottom: 1px solid var(--border);
			padding-bottom: 0;
		}

		a span {
			font-size: inherit;
		}

		a {
			flex-direction: row;
			gap: 6px;
			min-height: 48px;
			font-size: 0.9rem;
		}

		a[aria-current='page'] {
			background-position: bottom;
		}

		/* Same size and place on every page: centred in the bar, so switching pages, whatever
		   their width, never moves or resizes the tabs. */
		ul {
			max-width: none;
			padding: 0 1rem;
			grid-template-columns: repeat(4, 9rem);
			justify-content: center;
		}
	}
</style>
