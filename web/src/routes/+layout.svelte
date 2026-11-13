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
	import FormGuard from '#lib/components/FormGuard.svelte';
	import SignInSheet from '#lib/components/SignInSheet.svelte';
	import { page } from '$app/state';
	import { pageLayout } from '#lib/navigation.ts';
	import type { LayoutProps } from './$types';

	let { data, children }: LayoutProps = $props();
	// Sign in from the header returns to this page, except from the account pages themselves.
	const onAccountPage = $derived(
		['/sign-in', '/register', '/forgot-password', '/reset-password', '/sign-out', '/verify-email'].some((p) =>
			page.url.pathname.startsWith(p)
		)
	);
	// A page may name its own return path (an event page keeps a long board search that way).
	const signInHref = $derived(
		onAccountPage
			? '/sign-in'
			: `/sign-in?returnTo=${encodeURIComponent(
					typeof page.data.signInReturn === 'string'
						? page.data.signInReturn
						: page.url.pathname + page.url.search
				)}`
	);
	// The primary pages share the header's frame on large screens; every other page is one
	// narrow, centred column (navigation.ts, pageLayout).
	const layout = $derived(pageLayout(page.url.pathname, Boolean(page.error)));
	// On the registration page itself, Join would only point back at the form.
	const onRegister = $derived(page.url.pathname.startsWith('/register'));
	// Two initials from a display name; from an email address only its first letter
	// ("firstuse-1794@…" is not "F1").
	const initials = $derived(
		data.viewer?.displayName
			? data.viewer.displayName
					.split(/\s+/)
					.filter(Boolean)
					.slice(0, 2)
					.map((part) => Array.from(part)[0]?.toUpperCase() ?? '')
					.join('')
			: (Array.from(data.viewer?.email ?? '')[0]?.toUpperCase() ?? '')
	);
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<a class="skip-link" href="#main">Skip to content</a>
<NavigationStatus />
<FormGuard />

<header class:guest={!data.viewer}>
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
			<a href={signInHref} data-sign-in>Sign in</a>
			{#if !onRegister}<a class="button secondary join" href="/register">Join</a>{/if}
		{/if}
	</span>
</header>

<!-- The tab bar is the members' app; guests browse the public area (Explore) without it. -->
{#if data.viewer}<AppNav />{:else if !onAccountPage}<SignInSheet />{/if}

<main id="main" tabindex="-1" class={layout}>
	<!-- A different account (or none) remounts the page: no component state carries over. -->
	{#key data.viewer?.accountId ?? 'anonymous'}
		{@render children()}
	{/key}
</main>

<footer class={layout} class:with-nav={Boolean(data.viewer)}>
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

	/* The layout rule (navigation.ts, pageLayout). The header spans the frame on every page.
	   The primary pages fill the same frame, so their headings start at the header's edge;
	   every other page is one narrow column, centred. --measure is the longest line for
	   paragraphs and forms, in either. */
	:global(:root) {
		--frame: 70rem;
		--narrow: 40rem;
		--measure: 40rem;
	}

	header {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		max-width: var(--frame);
		margin: 0 auto;
		padding: 0.75rem 1rem;
	}

	/* With very large text, Sign in and Join move under the name instead of off the screen. A
	   member's name shortens instead. */
	header.guest {
		flex-wrap: wrap;
	}

	.brand {
		display: inline-flex;
		align-items: center;
		min-height: 44px;
		white-space: nowrap;
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

	/* An outlined button: the page's own main action keeps the filled orange. */
	.account .join {
		min-height: 44px;
		padding: 0.35rem 1rem;
	}

	.me {
		min-width: 0;
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
		min-width: 0;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		color: var(--muted);
		font-size: 0.9rem;
	}

	.account a {
		display: inline-flex;
		align-items: center;
		min-height: 44px;
		white-space: nowrap;
	}

	/* Only a member's name may be shortened; Sign in and Join always show in full. */
	.me {
		min-width: 0;
		max-width: 14rem;
	}

	/* The smallest phones need the room for Sign in and Join. */
	@media (max-width: 22.5rem) {
		.badge {
			display: none;
		}
	}

	.badge {
		flex: none;
		white-space: nowrap;
		border-radius: 5px;
		background: var(--accent-soft);
		color: var(--fg);
		padding: 2px 7px;
		font-size: 0.75rem;
		font-weight: 700;
	}

	/* Same box and padding as the header, so a frame page's content edge is the header's. */
	main {
		max-width: var(--narrow);
		margin: 0 auto;
		padding: 0.5rem 1rem 1rem;
	}

	main.frame,
	footer.frame {
		max-width: var(--frame);
	}

	main:focus {
		outline: none;
	}

	/* Quiet links: muted and smaller than the page's own, still underlined. */
	footer {
		display: flex;
		flex-wrap: wrap;
		gap: 0 1.25rem;
		max-width: var(--narrow);
		margin: 1rem auto 0;
		padding: 0.25rem 1rem 2rem;
		/* A rule along the content edge, not the padding. */
		background: linear-gradient(var(--border), var(--border)) 1rem 0 / calc(100% - 2rem) 1px no-repeat;
		font-size: 0.9rem;
	}

	footer a {
		color: var(--muted);
	}

	footer a:hover {
		color: var(--fg);
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
