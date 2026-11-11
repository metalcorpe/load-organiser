<script lang="ts">
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { safeReturnPath } from '#lib/safe-return.ts';

	/**
	 * Sign-in as a sheet over the current page, for guests (#public-member split, part 2).
	 *
	 * Progressive enhancement: triggers are ordinary links to `/sign-in?returnTo=…` marked
	 * `data-sign-in`. Without JavaScript, or with a modifier click, they open the full page. With
	 * JavaScript a plain click opens this native modal <dialog> (focus trap, inert page, Escape),
	 * adds a shallow history entry so Back closes it, and posts to the same `/sign-in` action, which
	 * validates `returnTo` and redirects there. Errors fall back to the full sign-in page.
	 * Triggers are only placed where nothing has been typed, so the reload after signing in loses
	 * nothing.
	 */
	let dialog: HTMLDialogElement | undefined = $state();
	let opener: HTMLElement | null = null;
	const returnTo = $derived(page.state.signIn ?? null);
	const action = $derived(
		returnTo ? `/sign-in?returnTo=${encodeURIComponent(returnTo)}` : '/sign-in'
	);
	const registerHref = $derived(
		returnTo ? `/register?returnTo=${encodeURIComponent(returnTo)}` : '/register'
	);

	$effect(() => {
		function onClick(event: MouseEvent) {
			if (event.defaultPrevented || event.button !== 0) return;
			if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
			const link = (event.target as Element | null)?.closest?.('a[data-sign-in]');
			if (!(link instanceof HTMLAnchorElement)) return;
			event.preventDefault();
			opener = link;
			const target = new URL(link.href).searchParams.get('returnTo');
			const back = safeReturnPath(target) ?? `${page.url.pathname}${page.url.search}`;
			goto(page.url.href, { state: { signIn: back }, shallow: true });
		}
		// Capture phase: SvelteKit's router handles link clicks on the way up and would navigate first.
		document.addEventListener('click', onClick, true);
		// Until this runs, a tap follows the plain link to the full sign-in page (the intended
		// fallback). The marker says the sheet is listening; tests wait for it.
		document.documentElement.dataset.signInSheet = 'ready';
		return () => {
			document.removeEventListener('click', onClick, true);
			delete document.documentElement.dataset.signInSheet;
		};
	});

	// Open and close with the history entry, so Back, Close and Escape all agree.
	$effect(() => {
		if (!dialog) return;
		if (returnTo && !dialog.open) {
			dialog.showModal();
			// Start at the first field rather than the Close button.
			dialog.querySelector<HTMLInputElement>('#sheet-email')?.focus();
		}
		if (!returnTo && dialog.open) {
			dialog.close();
			opener?.focus();
		}
	});

	function close() {
		if (page.state.signIn) history.back();
	}

	function onCancel(event: Event) {
		event.preventDefault();
		close();
	}
</script>

<dialog bind:this={dialog} aria-labelledby="sheet-title" oncancel={onCancel}>
	<!-- Rendered only while open: no duplicate form fields on the page underneath. -->
	{#if returnTo}
	<div class="sheet">
		<div class="top">
			<h2 id="sheet-title">Sign in</h2>
			<button type="button" class="close" onclick={close}>Close</button>
		</div>
		<form method="POST" action={action} class="form" novalidate>
			<div class="field">
				<label for="sheet-email">Email</label>
				<input id="sheet-email" name="email" type="email" autocomplete="username" required maxlength="254" />
			</div>
			<div class="field">
				<label for="sheet-password">Password</label>
				<input id="sheet-password" name="password" type="password" autocomplete="current-password" required />
			</div>
			<div class="form-actions">
				<button class="button" type="submit">Sign in</button>
				<a href="/forgot-password">Forgot password?</a>
			</div>
		</form>
		<p class="hint">New here? <a href={registerHref}>Create an account</a></p>
	</div>
	{/if}
</dialog>

<style>
	dialog {
		width: 100%;
		max-width: 28rem;
		max-height: min(90dvh, 40rem);
		margin: auto auto 0;
		padding: 0;
		border: 0;
		border-radius: 22px 22px 0 0;
		background: var(--surface);
		color: var(--fg);
		box-shadow: 0 0 0 1px var(--border);
		overflow: auto;
	}

	dialog::backdrop {
		background: rgb(5 12 22 / 0.55);
	}

	.sheet {
		padding: 1rem 1.25rem calc(1.25rem + env(safe-area-inset-bottom));
	}

	.top {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
	}

	h2 {
		margin: 0;
	}

	.close {
		min-height: 44px;
		padding: 0 0.75rem;
		border: 0;
		background: none;
		color: var(--accent);
		font: inherit;
		font-weight: 600;
		cursor: pointer;
	}

	/* A centred card on wider screens. */
	@media (min-width: 40rem) {
		dialog {
			margin: auto;
			border-radius: 22px;
		}
	}
</style>
