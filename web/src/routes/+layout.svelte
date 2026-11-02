<script lang="ts">
	import '../app.css';
	import favicon from '#lib/assets/favicon.svg';
	import AppNav from '#lib/components/AppNav.svelte';
	import NavigationStatus from '#lib/components/NavigationStatus.svelte';
	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<a class="skip-link" href="#main">Skip to content</a>
<NavigationStatus />

<header>
	<a class="brand" href="/">Load Organiser</a>
	<span class="badge">Preview</span>
</header>

<AppNav />

<main id="main" tabindex="-1">
	{@render children()}
</main>

<footer>
	<a href="/status">Service status</a>
</footer>

<style>
	.skip-link {
		position: absolute;
		left: 0.5rem;
		top: -3rem;
		z-index: 30;
		padding: 0.5rem 1rem;
		background: var(--surface);
		border-radius: 8px;
	}

	.skip-link:focus {
		top: 0.5rem;
	}

	header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		max-width: 40rem;
		margin: 0 auto;
		padding: 0.75rem 1rem;
	}

	.brand {
		display: inline-flex;
		align-items: center;
		min-height: 44px;
		color: var(--fg);
		font-weight: 750;
		text-decoration: none;
	}

	.badge {
		border-radius: 5px;
		background: var(--accent-soft);
		color: var(--fg);
		padding: 2px 7px;
		font-size: 0.75rem;
		font-weight: 700;
	}

	main {
		max-width: 40rem;
		margin: 0 auto;
		padding: 0.5rem 1rem 1rem;
	}

	main:focus {
		outline: none;
	}

	footer {
		max-width: 40rem;
		margin: 0 auto;
		padding: 0 1rem calc(var(--nav-height) + 1.5rem + env(safe-area-inset-bottom));
	}

	footer a {
		display: inline-flex;
		align-items: center;
		min-height: 44px;
	}

	@media (min-width: 48rem) {
		footer {
			padding-bottom: 2rem;
		}
	}
</style>
