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

		/* The same frame and tab size on every page, so switching tabs never moves the bar.
		   The tabs start at the frame's edge, where the header and every page begin. */
		ul {
			max-width: var(--frame);
			padding: 0 1rem;
			grid-template-columns: repeat(4, minmax(0, 9rem));
		}
	}
</style>
