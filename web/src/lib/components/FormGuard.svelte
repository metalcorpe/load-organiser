<script lang="ts">
	// Forms are plain posts: they work without JavaScript and each save loads a new page.
	// With JavaScript, two things are added on top:
	//
	// 1. Offline: the browser would replace the page with its own error and the typed
	//    entry could be lost (private pages are no-store, so Back may not restore them).
	//    An offline submit is stopped and the form stays as typed. A connection that
	//    drops while sending is not detectable here.
	// 2. After a submit, the page that comes back moves focus to its first error, so a
	//    screen reader announces it (an alert already present at load often is not)
	//    and the error is in view. When the error code names a field (field-errors.ts),
	//    that field is marked aria-invalid, described by the alert, and focused instead.
	//    Only a marker is kept between the two pages, never form content; ordinary
	//    visits never move focus.
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { fieldsFor } from '#lib/field-errors.ts';

	const OFFLINE =
		'You are offline, so nothing was sent. What you entered is still here: send it again when you have a connection.';
	const SUBMITTED = 'form-submitted';

	function remember(on: boolean) {
		try {
			if (on) sessionStorage.setItem(SUBMITTED, '1');
			else sessionStorage.removeItem(SUBMITTED);
		} catch {
			// Storage blocked: errors stay visible, focus just does not move.
		}
	}

	function submittedBefore(): boolean {
		try {
			return sessionStorage.getItem(SUBMITTED) === '1';
		} catch {
			return false;
		}
	}

	let errorIds = 0;

	/** The field this error is about, inside the form that shows it. */
	function fieldFor(error: HTMLElement): HTMLElement | null {
		const code = page.form && typeof page.form === 'object' ? page.form.error : undefined;
		const scope = error.closest('form') ?? error.parentElement?.querySelector('form');
		if (!scope) return null;
		for (const name of fieldsFor(code)) {
			const field = scope.querySelector<HTMLElement>(
				`[name="${CSS.escape(name)}"]:not([type="hidden"])`
			);
			if (field) return field;
		}
		return null;
	}

	function focusFirstError() {
		const error = document.querySelector<HTMLElement>('main .form-error[role="alert"]');
		if (!error) return;
		const field = fieldFor(error);
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

	onMount(() => {
		if (submittedBefore()) {
			remember(false);
			focusFirstError();
		}
		const onSubmit = (event: SubmitEvent) => {
			if (!(event.target instanceof HTMLFormElement) || event.defaultPrevented) return;
			if (navigator.onLine) {
				remember(true);
				return;
			}
			event.preventDefault();
			const form = event.target;
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
		document.addEventListener('submit', onSubmit, true);
		window.addEventListener('online', onOnline);
		return () => {
			document.removeEventListener('submit', onSubmit, true);
			window.removeEventListener('online', onOnline);
		};
	});
</script>
