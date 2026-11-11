<script lang="ts">
	import '@fontsource/figtree/latin-400.css';
	import '@fontsource/figtree/latin-ext-400.css';
	import '@fontsource/figtree/latin-600.css';
	import '@fontsource/figtree/latin-ext-600.css';
	import '@fontsource/outfit/latin-600.css';
	import '@fontsource/outfit/latin-ext-600.css';
	import '@fontsource/outfit/latin-700.css';
	import '@fontsource/outfit/latin-ext-700.css';
	import '../app.css';
	import favicon from '#lib/assets/favicon.svg';
	import AppNav from '#lib/components/AppNav.svelte';
	import NavigationStatus from '#lib/components/NavigationStatus.svelte';
	import type { LayoutProps } from './$types';

	let { data, children }: LayoutProps = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<a class="skip-link" href="#main">Skip to content</a>
<NavigationStatus />

<header>
	<a class="brand" href="/">Load Organiser</a>
	<span class="badge">Preview</span>
	<span class="account">
		{#if data.viewer}
			<a href="/profile" data-testid="current-account">{data.viewer.displayName ?? data.viewer.email}</a>
		{:else}
			<a href="/sign-in">Sign in</a>
		{/if}
	</span>
</header>

<AppNav />

<main id="main" tabindex="-1">
	<!-- A different account (or none) remounts the page: no component state carries over. -->
	{#key data.viewer?.accountId ?? 'anonymous'}
		{@render children()}
	{/key}
</main>

<footer>
	<a href="/privacy">Privacy and the beta</a>
	<a href="/status">Service status</a>
	<a href="/support">Support the beta</a>
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

	.account {
		margin-left: auto;
		min-width: 0;
	}

	.account a {
		display: inline-flex;
		align-items: center;
		min-height: 44px;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
		max-width: 14rem;
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
		display: flex;
		flex-wrap: wrap;
		gap: 0 1.25rem;
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
