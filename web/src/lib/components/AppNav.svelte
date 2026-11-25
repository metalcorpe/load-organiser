<script lang="ts">
	import { navigating, page } from '$app/state';
	import { PRIMARY_NAV, isCurrentTab, tabSwitch } from '#lib/navigation.ts';
	import NavIcon from './NavIcon.svelte';

	// The tab being opened takes the pill at once; aria-current stays on the page still shown
	// until the new one arrives (the layout marks main busy meanwhile).
	const opening = $derived(tabSwitch(page.url.pathname, navigating.to?.url.pathname));
</script>

<nav aria-label="Primary">
	<ul class:moving={opening !== undefined}>
		{#each PRIMARY_NAV as item (item.href)}
			{@const current = isCurrentTab(item, page.url.pathname)}
			<li>
				<!-- Each tab's code loads while the bar is on screen; its data only on a tap
				     (private data is never fetched speculatively: architecture.md). -->
				<a
					href={item.href}
					aria-current={current ? 'page' : undefined}
					data-pending={opening === item ? 'true' : undefined}
					data-sveltekit-preload-code="viewport"
				>
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

	/* See-through only where the blur works (and color-mix, or the bar would be clear);
	   tokens.spec.ts checks the labels at this share over white and black. */
	@supports (backdrop-filter: blur(12px)) and (background: color-mix(in srgb, red 50%, transparent)) {
		nav {
			background: color-mix(in srgb, var(--nav-bg) 94%, transparent);
			backdrop-filter: blur(12px);
		}
	}

	ul {
		display: grid;
		grid-template-columns: repeat(4, minmax(0, 1fr));
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

	/* While another tab opens, the pill moves to it at once. */
	.moving a[aria-current='page'] {
		background: transparent;
		color: var(--muted);
		font-weight: inherit;
	}

	.moving a[data-pending='true'] {
		border-radius: 16px;
		background: var(--nav-pill);
		color: var(--nav-pill-fg);
		font-weight: 750;
	}

	/* Forced colours drop background colours: mark the current tab with the system highlight. */
	@media (forced-colors: active) {
		a[aria-current='page'],
		.moving a[data-pending='true'] {
			forced-color-adjust: none;
			background: Highlight;
			color: HighlightText;
		}

		.moving a[aria-current='page'] {
			background: Canvas;
			color: LinkText;
		}
	}

	/* Under 360px the four tabs share less room: the labels at 200% text need every pixel of
	   each tab, so the bar sits 8px from the edges and the pill gives up its side padding. */
	@media (max-width: 22.49rem) {
		nav {
			inset: auto max(8px, env(safe-area-inset-right)) calc(12px + env(safe-area-inset-bottom))
				max(8px, env(safe-area-inset-left));
		}

		ul {
			padding-inline: 2px;
		}

		a {
			padding-inline: 0;
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

		a[aria-current='page'],
		.moving a[data-pending='true'] {
			border-radius: 12px;
		}

		/* Same size and place on every page: centred in the bar, so switching pages, whatever
		   their width, never moves or resizes the tabs. */
		ul {
			max-width: none;
			/* Room above and below so the current tab reads as a pill, not a full-height tab. */
			padding: 4px 1rem;
			grid-template-columns: repeat(4, 9rem);
			justify-content: center;
		}
	}
</style>
