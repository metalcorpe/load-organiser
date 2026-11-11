<script lang="ts">
	import '@fontsource/figtree/latin-400.css';
	import '@fontsource/figtree/latin-ext-400.css';
	import '@fontsource/figtree/latin-600.css';
	import '@fontsource/figtree/latin-ext-600.css';
	import '@fontsource/outfit/latin-600.css';
	import '@fontsource/outfit/latin-ext-600.css';
	import '@fontsource/outfit/latin-700.css';
	import '@fontsource/outfit/latin-ext-700.css';
	import '#lib/design/tokens-light.css';
	import '#lib/design/tokens-dark.css';
	import '../app.css';
	import favicon from '#lib/assets/favicon.svg';
	import AppNav from '#lib/components/AppNav.svelte';
	import NavigationStatus from '#lib/components/NavigationStatus.svelte';
	import type { LayoutProps } from './$types';

	let { data, children }: LayoutProps = $props();
	const initials = $derived(
		(data.viewer?.displayName ?? data.viewer?.email ?? '')
			.split(/[\s@._-]+/)
			.filter(Boolean)
			.slice(0, 2)
			.map((part) => part[0]?.toUpperCase() ?? '')
			.join('')
	);
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
			<a class="me" href="/profile">
				<span class="avatar" aria-hidden="true">{initials}</span>
				<span class="visually-hidden">My account:</span>
				<span class="who" data-testid="current-account">{data.viewer.displayName ?? data.viewer.email}</span>
			</a>
		{:else}
			<a href="/sign-in">Sign in</a>
			<a class="button join" href="/register">Join</a>
		{/if}
	</span>
</header>

<!-- The tab bar is the members' app; guests browse the public area (Explore) without it. -->
{#if data.viewer}<AppNav />{/if}

<main id="main" tabindex="-1">
	<!-- A different account (or none) remounts the page: no component state carries over. -->
	{#key data.viewer?.accountId ?? 'anonymous'}
		{@render children()}
	{/key}
</main>

<footer class:with-nav={Boolean(data.viewer)}>
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
		display: flex;
		align-items: center;
		gap: 0.75rem;
		margin-left: auto;
		min-width: 0;
	}

	.account .join {
		min-height: 40px;
		padding: 0.35rem 1rem;
		color: var(--accent-fg);
	}

	.me {
		gap: 0.5rem;
		color: var(--fg);
		text-decoration: none;
	}

	.avatar {
		display: inline-grid;
		place-items: center;
		flex: none;
		width: 2.25rem;
		height: 2.25rem;
		border-radius: 999px;
		background: var(--brand);
		color: var(--brand-fg);
		font-family: var(--font-display);
		font-weight: 600;
		font-size: 0.85rem;
	}

	.who {
		overflow: hidden;
		text-overflow: ellipsis;
		color: var(--muted);
		font-size: 0.9rem;
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
		padding: 0 1rem 2rem;
	}

	/* Room for the members' fixed tab bar on phones. */
	footer.with-nav {
		padding-bottom: calc(var(--nav-height) + 1.5rem + env(safe-area-inset-bottom));
	}

	footer a {
		display: inline-flex;
		align-items: center;
		min-height: 44px;
	}

	@media (min-width: 48rem) {
		footer.with-nav {
			padding-bottom: 2rem;
		}
	}
</style>
