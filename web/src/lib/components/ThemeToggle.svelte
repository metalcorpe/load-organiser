<script lang="ts">
	import { page } from '$app/state';
	import { nextTheme, themeLabel, type Theme } from '#lib/theme.ts';

	/**
	 * The one theme control, in the header for guests and members: each press moves to the next
	 * choice (device setting, light, dark). A plain form, so it works without JavaScript; the
	 * full page load that follows is rendered by the server in the new theme, without a flash.
	 */
	let { theme }: { theme: Theme } = $props();
	const next = $derived(nextTheme(theme));
	const returnTo = $derived(`${page.url.pathname}${page.url.search}`);
</script>

<form method="POST" action="/appearance" class="theme">
	<input type="hidden" name="theme" value={next} />
	<input type="hidden" name="returnTo" value={returnTo} />
	<button
		type="submit"
		aria-label="Theme: {themeLabel(theme)}. Change to {themeLabel(next)}"
		title="Theme: {themeLabel(theme)}"
	>
		<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
			{#if theme === 'light'}
				<circle cx="12" cy="12" r="4" />
				<path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
			{:else if theme === 'dark'}
				<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z" />
			{:else}
				<circle cx="12" cy="12" r="8" />
				<path d="M12 4a8 8 0 0 1 0 16z" fill="currentColor" />
			{/if}
		</svg>
	</button>
</form>

<style>
	.theme {
		display: contents;
	}

	/* A 44px icon button, quiet like the account link beside it. */
	button {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 44px;
		height: 44px;
		padding: 0;
		border: 1px solid transparent;
		border-radius: 999px;
		background: transparent;
		color: var(--muted);
		cursor: pointer;
	}

	button:hover {
		color: var(--fg);
		background: var(--surface-soft);
	}
</style>
