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
	//    and the error is in view. Only a marker is kept between the two pages, never
	//    form content; ordinary visits never move focus.
	import { onMount } from 'svelte';

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

	function focusFirstError() {
		const error = document.querySelector<HTMLElement>('main .form-error[role="alert"]');
		if (!error) return;
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
