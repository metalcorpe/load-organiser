<script lang="ts">
	import { page } from '$app/state';

	/**
	 * The public area's two views as plain links styled as segments: each keeps its own address,
	 * history entry and server render, for guests and members alike.
	 */
	const views = [
		{ href: '/', label: 'Events' },
		{ href: '/dz', label: 'Dropzones' }
	];
	const current = (href: string) =>
		href === '/' ? page.url.pathname === '/' : page.url.pathname.startsWith(href);
</script>

<nav class="switch" aria-label="Explore">
	{#each views as view (view.href)}
		<a href={view.href} aria-current={current(view.href) ? 'page' : undefined}>{view.label}</a>
	{/each}
</nav>

<style>
	.switch {
		display: inline-grid;
		grid-auto-flow: column;
		grid-auto-columns: 1fr;
		gap: 0.25rem;
		margin: 0.25rem 0 0.75rem;
		padding: 0.25rem;
		border-radius: 999px;
		background: var(--surface-soft);
		box-shadow: 0 0 0 1px var(--border);
	}

	a {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-height: 44px;
		min-width: 7.5rem;
		padding: 0 1rem;
		border-radius: 999px;
		color: var(--muted);
		font-weight: 600;
		text-decoration: none;
	}

	a[aria-current='page'] {
		background: var(--brand);
		color: var(--brand-fg);
	}

	a:focus-visible {
		outline-offset: 1px;
	}
</style>
