<script lang="ts">
	import { page } from '$app/state';
	import { PRIMARY_NAV, isCurrentTab } from '#lib/navigation.ts';
	import type { PageWidth } from '#lib/navigation.ts';
	import NavIcon from './NavIcon.svelte';

	/** The page's measure, so the tabs line up with the header and content on large screens. */
	let { width = 'narrow' }: { width?: PageWidth } = $props();
</script>

<nav aria-label="Primary">
	<ul class="w-{width}">
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

	ul.w-medium {
		max-width: 60rem;
	}

	ul.w-wide {
		max-width: 70rem;
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

	a[aria-current='page'] {
		color: var(--accent);
		font-weight: 750;
		box-shadow: inset 0 3px var(--accent);
	}

	@media (min-width: 48rem) {
		nav {
			position: static;
			border-top: 0;
			border-bottom: 1px solid var(--border);
			padding-bottom: 0;
		}

		a {
			flex-direction: row;
			gap: 6px;
			min-height: 48px;
			font-size: 0.9rem;
		}

		a[aria-current='page'] {
			box-shadow: inset 0 -3px var(--accent);
		}

		/* The tabs start at the content's edge, like the header and the page. */
		ul {
			padding: 0 1rem;
		}

		/* On a wide page they keep their size instead of spreading across it. */
		ul.w-medium,
		ul.w-wide {
			grid-template-columns: repeat(4, minmax(0, 9rem));
		}
	}
</style>
