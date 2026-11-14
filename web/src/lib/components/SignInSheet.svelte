<script lang="ts">
	import { tick } from 'svelte';
	import { enhance } from '$app/forms';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import type { SubmitFunction } from '$app/forms';
	import PasswordInput from '#lib/components/PasswordInput.svelte';
	import {
		errorSummary,
		fieldMessage,
		firstInvalid,
		signInErrors,
		type FieldErrors
	} from '#lib/account-form.ts';
	import { authMessage } from '#lib/auth-messages.ts';
	import { OFFLINE_MESSAGE } from '#lib/offline.ts';
	import { safeReturnPath } from '#lib/safe-return.ts';

	/**
	 * Sign-in as a sheet over the current page, for guests (#public-member split, part 2).
	 *
	 * Progressive enhancement: triggers are ordinary links to `/sign-in?returnTo=…` marked
	 * `data-sign-in`. Without JavaScript, or with a modifier click, they open the full page. With
	 * JavaScript a plain click opens this native modal <dialog> (focus trap, inert page, Escape),
	 * adds a shallow history entry so Back closes it, and posts to the same `/sign-in` action, which
	 * validates `returnTo` and redirects there.
	 *
	 * The form is enhanced: empty or malformed fields are reported here before anything is sent,
	 * and a refusal from the server (wrong details, too many attempts, service down) is shown in
	 * the sheet, keeping the email. A successful sign-in loads the return page in full, as the
	 * plain form post did, so nothing from the guest page carries over. Triggers are only placed
	 * where nothing has been typed, so that load loses nothing. Closing the sheet abandons a
	 * request still in flight: its answer is ignored and nothing navigates.
	 *
	 * Announcements, each message once: a field problem is shown under the field, which gets
	 * focus and is described by it (as FormGuard does on the full page). A problem with the
	 * whole attempt is an alert inserted into the sheet, announced by its role; focus stays put.
	 */
	let dialog: HTMLDialogElement | undefined = $state();
	let opener: HTMLElement | null = null;
	let password: HTMLInputElement | undefined = $state();
	let fields: FieldErrors = $state({});
	let failure: string | undefined = $state();
	let busy = $state(false);
	// The details were refused (one answer for a wrong password and an unknown account): both
	// fields are marked. Throttling, offline or an outage say nothing about the fields.
	let refused = $state(false);
	let inFlight: AbortController | null = null;

	/** Forget any request still in flight (the sheet opened or closed). */
	function abandon() {
		inFlight?.abort();
		inFlight = null;
		busy = false;
	}
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
			if (page.state.signIn) return; // already open, or opening: one history entry only
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
			abandon();
			fields = {};
			failure = undefined;
			refused = false;
			dialog.showModal();
			// Start at the first field rather than the Close button.
			dialog.querySelector<HTMLInputElement>('#sheet-email')?.focus();
		}
		if (!returnTo && dialog.open) {
			abandon();
			dialog.close();
			opener?.focus();
		}
	});

	function close() {
		if (page.state.signIn) history.back();
	}

	/** Focus the first field with a problem; a whole-form alert announces itself instead. */
	async function focusField() {
		await tick();
		const name = firstInvalid(fields);
		if (name) dialog?.querySelector<HTMLElement>(`#sheet-${name}`)?.focus();
	}

	const submit: SubmitFunction = ({ formData, cancel, controller }) => {
		const value = (name: string) => {
			const raw = formData.get(name);
			return typeof raw === 'string' ? raw : '';
		};
		if (busy) {
			cancel(); // one attempt at a time
			return;
		}
		failure = undefined;
		refused = false;
		fields = signInErrors({ email: value('email').trim(), password: value('password') });
		if (firstInvalid(fields)) {
			cancel();
			void focusField();
			return;
		}
		if (!navigator.onLine) {
			// enhance has already stopped the plain post, so FormGuard cannot catch this one.
			cancel();
			// After the clearing above has rendered, so the alert is inserted anew and announced.
			void tick().then(() => (failure = OFFLINE_MESSAGE));
			return;
		}
		busy = true;
		inFlight = controller;
		return async ({ result }) => {
			// Closed (or reopened) while this was in flight: the answer belongs to nobody.
			if (controller.signal.aborted || inFlight !== controller) return;
			inFlight = null;
			busy = false;
			if (result.type === 'redirect') {
				// A full load, like the plain post: the new session's pages, nothing kept from before.
				location.assign(result.location);
				return;
			}
			if (result.type === 'failure') {
				// Refused: the password goes, the email stays.
				if (password) password.value = '';
				const data = result.data ?? {};
				const code = typeof data.error === 'string' ? data.error : 'unavailable';
				fields = (data.fields as FieldErrors | undefined) ?? {};
				failure = errorSummary(fields) ? undefined : authMessage(code);
				refused = code === 'invalid_credentials';
			} else {
				// No answer (network or server error): nothing was decided, so nothing is cleared.
				failure = authMessage('unavailable');
			}
			await focusField();
		};
	};

	function onCancel(event: Event) {
		event.preventDefault();
		close();
	}

	// The browser can close a modal dialog itself (for example a second Escape, or Android's back
	// gesture) without a cancel event. Drop the history entry too, or the next open would be ignored.
	function onClose() {
		if (page.state.signIn) history.back();
	}
</script>

<dialog bind:this={dialog} aria-labelledby="sheet-title" oncancel={onCancel} onclose={onClose}>
	<!-- Rendered only while open: no duplicate form fields on the page underneath. -->
	{#if returnTo}
	<div class="sheet">
		<div class="top">
			<h2 id="sheet-title">Sign in</h2>
			<button type="button" class="close" onclick={close}>Close</button>
		</div>
		<form method="POST" action={action} class="form" novalidate use:enhance={submit} aria-busy={busy}>
			{#if failure}
				<p class="form-error" role="alert" id="sheet-error">{failure}</p>
			{/if}
			<div class="field">
				<label for="sheet-email">Email</label>
				<input
					id="sheet-email"
					name="email"
					type="email"
					autocomplete="username"
					required
					maxlength="254"
					aria-invalid={fields.email || refused ? 'true' : undefined}
					aria-describedby={fields.email ? 'sheet-email-error' : refused ? 'sheet-error' : undefined}
				/>
				{#if fields.email}
					<p class="field-error" id="sheet-email-error">{fieldMessage(fields.email)}</p>
				{/if}
			</div>
			<div class="field">
				<label for="sheet-password">Password</label>
				<PasswordInput
					id="sheet-password"
					name="password"
					autocomplete="current-password"
					required
					maxlength={1024}
					invalid={Boolean(fields.password || refused)}
					describedby={fields.password ? 'sheet-password-error' : refused ? 'sheet-error' : undefined}
					bind:input={password}
				/>
				{#if fields.password}
					<p class="field-error" id="sheet-password-error">{fieldMessage(fields.password)}</p>
				{/if}
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

	/* No scrolling of the page behind the open sheet. */
	:global(html:has(dialog[open])) {
		overflow: hidden;
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
