<script lang="ts">
	// Forms are plain posts: they work without JavaScript and each save loads a new page.
	// With JavaScript, two things are added on top:
	//
	// 1. Offline: the browser would replace the page with its own error and the typed
	//    entry could be lost (private pages are no-store, so Back may not restore them).
	//    An offline submit is stopped and the form stays as typed. A connection that
	//    drops while sending is not detectable here.
	// 2. After a POST that comes back to the same page (a refusal), focus moves to the
	//    error of the form that was sent, so a screen reader announces it (an alert
	//    already present at load often is not) and it is in view. When the error code
	//    names a field (field-errors.ts), that field is marked aria-invalid, described
	//    by the alert, and focused instead. Between the two pages only the path and the
	//    form's position on it are kept, never form content. Search (GET) forms, client
	//    navigations and ordinary visits never move focus. A field inside a folded
	//    <details> section is unfolded first, so it can take focus.
	// 3. After a POST that comes back to the same page with a confirmation
	//    (role="status") for the form that was sent, that confirmation is focused and
	//    scrolled into view, so a save lower on the page does not leave you at the top
	//    with the result out of sight. The form must still be the same one (same
	//    action), since a success can remove forms and shift positions.
	import { onMount } from 'svelte';
	import { afterNavigate } from '$app/navigation';
	import { page } from '$app/state';
	import { fieldsFor } from '#lib/field-errors.ts';
	import { OFFLINE_MESSAGE } from '#lib/offline.ts';

	const OFFLINE = OFFLINE_MESSAGE;
	const SUBMITTED = 'form-submitted';
	const ALERT = '.form-error[role="alert"]';
	const STATUS = '[role="status"]';

	type Sent = { path: string; index: number; action?: string };

	const postForms = () =>
		Array.from(document.querySelectorAll<HTMLFormElement>('main form')).filter(
			(form) => form.method.toLowerCase() === 'post'
		);

	function remember(sent: Sent | null) {
		try {
			if (sent) sessionStorage.setItem(SUBMITTED, JSON.stringify(sent));
			else sessionStorage.removeItem(SUBMITTED);
		} catch {
			// Storage blocked: errors stay visible, focus just does not move.
		}
	}

	function recalled(): Sent | null {
		try {
			const raw = sessionStorage.getItem(SUBMITTED);
			const sent = raw ? (JSON.parse(raw) as Sent) : null;
			return sent && typeof sent.path === 'string' && Number.isInteger(sent.index) ? sent : null;
		} catch {
			return null;
		}
	}

	/** The message for `form`: `inside` within it, or `before` placed just before it. */
	function messageOf(form: HTMLFormElement, inside: string, before = inside): HTMLElement | null {
		const within = form.querySelector<HTMLElement>(inside);
		if (within) return within;
		let previous = form.previousElementSibling;
		for (let step = 0; previous && step < 2; step++, previous = previous.previousElementSibling) {
			if (previous.matches(before)) return previous as HTMLElement;
			if (previous.matches('form')) break;
		}
		return null;
	}

	const errorOf = (form: HTMLFormElement) => messageOf(form, ALERT);

	/** A field inside folded sections (<details>) cannot take focus: unfold them first. */
	function reveal(field: HTMLElement) {
		for (let d = field.closest('details'); d; d = d.parentElement?.closest('details') ?? null) {
			d.open = true;
		}
	}

	function bringIntoView(target: HTMLElement) {
		if (!target.hasAttribute('tabindex')) target.setAttribute('tabindex', '-1');
		target.focus({ preventScroll: true });
		target.scrollIntoView({ block: 'center' });
	}

	/** After a save that stayed on this page, bring its confirmation into view. */
	function focusConfirmation(form: HTMLFormElement, sent: Sent) {
		if (sent.action !== undefined && form.getAttribute('action') !== sent.action) return;
		const status = messageOf(form, STATUS, `${STATUS}, .notice.ok`);
		if (status) bringIntoView(status);
	}

	function fieldIn(form: HTMLFormElement): HTMLElement | null {
		const code = page.form && typeof page.form === 'object' ? page.form.error : undefined;
		for (const name of fieldsFor(code)) {
			const field = form.querySelector<HTMLElement>(
				`[name="${CSS.escape(name)}"]:not([type="hidden"])`
			);
			if (field) return field;
		}
		return null;
	}

	let errorIds = 0;

	const describedIds = (field: Element) =>
		(field.getAttribute('aria-describedby') ?? '').split(' ').filter(Boolean);

	/** A field the page already explains with its own error (not just a hint). */
	const hasOwnError = (field: Element) =>
		describedIds(field).some((id) => document.getElementById(id)?.matches('.field-error') ?? false);

	/** The first field, in page order, that the page marked invalid with its own error. */
	const firstOwnError = (form: HTMLFormElement) =>
		Array.from(form.querySelectorAll<HTMLElement>('[aria-invalid="true"]')).find(hasOwnError) ??
		null;

	function focusError(sent: Sent) {
		if (sent.path !== location.pathname) return; // a success redirected elsewhere
		const form = postForms()[sent.index];
		if (!form) return;
		// Fields that carry their own error keep only that (and their hints): the summary
		// would repeat it and add guidance about other fields.
		const own = firstOwnError(form);
		if (own) {
			reveal(own);
			own.focus({ preventScroll: true });
			own.scrollIntoView({ block: 'center' });
			return;
		}
		const error = errorOf(form);
		if (!error) {
			focusConfirmation(form, sent);
			return;
		}
		const field = fieldIn(form);
		if (field) {
			if (!error.id) error.id = `form-error-${++errorIds}`;
			const described = describedIds(field);
			if (!described.includes(error.id)) {
				field.setAttribute('aria-describedby', [...described, error.id].join(' '));
			}
			field.setAttribute('aria-invalid', 'true');
			// Typing a new value clears the mark; the message stays until the next save.
			field.addEventListener('input', () => field.removeAttribute('aria-invalid'), { once: true });
			reveal(field);
			field.focus({ preventScroll: true });
			field.scrollIntoView({ block: 'center' });
			return;
		}
		bringIntoView(error);
	}

	// A client-side navigation (links, search forms) never carries a POST result here.
	afterNavigate(({ type }) => {
		if (type !== 'enter') remember(null);
	});

	onMount(() => {
		const sent = recalled();
		remember(null);
		if (sent) focusError(sent);

		// Bubble phase: a form's own handler runs first and may cancel the submit.
		const onSubmit = (event: SubmitEvent) => {
			const form = event.target;
			if (!(form instanceof HTMLFormElement) || event.defaultPrevented) return;
			if (navigator.onLine) {
				const index = postForms().indexOf(form);
				if (index >= 0) {
					remember({
						path: location.pathname,
						index,
						action: form.getAttribute('action') ?? undefined
					});
				}
				return;
			}
			event.preventDefault();
			let notice = form.querySelector<HTMLElement>(':scope > [data-offline-notice]');
			if (!notice) {
				notice = document.createElement('p');
				notice.className = 'form-error';
				notice.setAttribute('role', 'alert');
				notice.dataset.offlineNotice = '';
				notice.textContent = OFFLINE;
				form.insertBefore(notice, form.firstChild);
			}
			notice.scrollIntoView({ block: 'nearest' });
		};
		const onOnline = () => {
			for (const notice of document.querySelectorAll('[data-offline-notice]')) notice.remove();
		};
		document.addEventListener('submit', onSubmit);
		window.addEventListener('online', onOnline);
		// Tests wait for this before submitting, so the listener is in place.
		document.documentElement.dataset.formGuard = 'ready';
		return () => {
			document.removeEventListener('submit', onSubmit);
			window.removeEventListener('online', onOnline);
			delete document.documentElement.dataset.formGuard;
		};
	});
</script>
