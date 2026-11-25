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
	/* Phones: a bar floating inside the screen edges and above the home indicator (design H).
	   The transparent border is drawn in forced colours, so the bar keeps an edge there. Room
	   for it elsewhere comes from --nav-clearance (app.css). */
	nav {
		position: fixed;
		inset: auto max(12px, env(safe-area-inset-right)) calc(12px + env(safe-area-inset-bottom))
			max(12px, env(safe-area-inset-left));
		z-index: 10;
		border: 1px solid transparent;
		border-radius: 20px;
		background: var(--nav-bg);
		box-shadow: var(--shadow-card), 0 8px 24px rgb(0 0 0 / 12%);
	}

	/* See-through only where the blur works; contrast is checked on the opaque --nav-bg. */
	@supports (backdrop-filter: blur(12px)) {
		nav {
			background: color-mix(in srgb, var(--nav-bg) 90%, transparent);
			backdrop-filter: blur(12px);
		}
	}

	ul {
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
		gap: 2px;
		max-width: 40rem;
		margin: 0 auto;
		padding: 4px;
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

	/* The current tab is a filled pill: light on graphite, dark on light (design H). */
	a[aria-current='page'] {
		border-radius: 16px;
		background: var(--nav-pill);
		color: var(--nav-pill-fg);
		font-weight: 750;
	}

	/* Forced colours drop background colours: mark the current tab with the system highlight. */
	@media (forced-colors: active) {
		a[aria-current='page'] {
			forced-color-adjust: none;
			background: Highlight;
			color: HighlightText;
		}
	}

	@media (min-width: 48rem) {
		/* Large screens: a static bar under the header, not floating. */
		nav {
			position: static;
			border-width: 0 0 1px;
			border-radius: 0;
			background: var(--nav-bg);
			box-shadow: none;
			backdrop-filter: none;
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
			border-radius: 12px;
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
