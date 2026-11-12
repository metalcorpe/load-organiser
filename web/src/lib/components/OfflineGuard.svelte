<script lang="ts">
	// Forms are plain posts (they work without JavaScript). Offline, the browser would
	// replace the page with its own error and the typed entry could be lost: private
	// pages are no-store, so Back may not restore them. With JavaScript, an offline
	// submit is stopped here and the form stays as typed. Nothing is stored on the
	// device. A connection that drops while sending is not detectable here.
	import { onMount } from 'svelte';

	const MESSAGE =
		'You are offline, so nothing was sent. What you entered is still here: send it again when you have a connection.';

	onMount(() => {
		const onSubmit = (event: SubmitEvent) => {
			if (navigator.onLine || !(event.target instanceof HTMLFormElement)) return;
			event.preventDefault();
			const form = event.target;
			let notice = form.querySelector<HTMLElement>(':scope > [data-offline-notice]');
			if (!notice) {
				notice = document.createElement('p');
				notice.className = 'form-error';
				notice.setAttribute('role', 'alert');
				notice.dataset.offlineNotice = '';
				notice.textContent = MESSAGE;
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
