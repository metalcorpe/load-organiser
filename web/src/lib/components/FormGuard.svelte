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
	//    navigations and ordinary visits never move focus.
	import { onMount } from 'svelte';
	import { afterNavigate } from '$app/navigation';
	import { page } from '$app/state';
	import { fieldsFor } from '#lib/field-errors.ts';

	const OFFLINE =
		'You are offline, so nothing was sent. What you entered is still here: send it again when you have a connection.';
	const SUBMITTED = 'form-submitted';
	const ALERT = '.form-error[role="alert"]';

	type Sent = { path: string; index: number };

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

	/** The refusal shown for `form`: inside it, or the alert placed just before it. */
	function errorOf(form: HTMLFormElement): HTMLElement | null {
		const inside = form.querySelector<HTMLElement>(ALERT);
		if (inside) return inside;
		let previous = form.previousElementSibling;
		for (let step = 0; previous && step < 2; step++, previous = previous.previousElementSibling) {
			if (previous.matches(ALERT)) return previous as HTMLElement;
			if (previous.matches('form')) break;
		}
		return null;
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

	function focusError(sent: Sent) {
		if (sent.path !== location.pathname) return; // a success redirected elsewhere
		const form = postForms()[sent.index];
		const error = form ? errorOf(form) : null;
		if (!form || !error) return;
		const field = fieldIn(form);
		if (field) {
			if (!error.id) error.id = `form-error-${++errorIds}`;
			const described = (field.getAttribute('aria-describedby') ?? '').split(' ').filter(Boolean);
			if (!described.includes(error.id)) {
				field.setAttribute('aria-describedby', [...described, error.id].join(' '));
			}
			field.setAttribute('aria-invalid', 'true');
			// Typing a new value clears the mark; the message stays until the next save.
			field.addEventListener('input', () => field.removeAttribute('aria-invalid'), { once: true });
			field.focus({ preventScroll: true });
			field.scrollIntoView({ block: 'center' });
			return;
		}
		if (!error.hasAttribute('tabindex')) error.setAttribute('tabindex', '-1');
		error.focus({ preventScroll: true });
		error.scrollIntoView({ block: 'center' });
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
				if (index >= 0) remember({ path: location.pathname, index });
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
