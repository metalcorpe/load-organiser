<script lang="ts">
	// Invite jump buddies to a discoverable profile. Without JavaScript the link is shown
	// to copy by hand; with it, the button opens the phone's share sheet, or copies the
	// link where there is none, and says which happened.
	let { url, name }: { url: string; name: string } = $props();
	let status = $state('');
	let canShare = $state(false);

	$effect(() => {
		canShare = typeof navigator !== 'undefined' && (typeof navigator.share === 'function' || Boolean(navigator.clipboard));
	});

	async function share() {
		const text = `Follow ${name} on Load Organiser`;
		try {
			if (typeof navigator.share === 'function') {
				await navigator.share({ title: text, text, url });
				status = '';
				return;
			}
			await navigator.clipboard.writeText(url);
			status = 'Link copied.';
		} catch (error) {
			// Closing the share sheet is not a failure.
			if (error instanceof DOMException && error.name === 'AbortError') return;
			status = 'Could not share from here. Copy the link above instead.';
		}
	}
</script>

<div class="invite">
	<p class="link"><a href={url}>{url}</a></p>
	{#if canShare}
		<button class="button secondary" type="button" onclick={share}>Invite jump buddies</button>
	{/if}
	<p class="hint" role="status">{status}</p>
</div>

<style>
	.link {
		overflow-wrap: anywhere;
		margin: 0.25rem 0 0.75rem;
	}

	.hint:empty {
		display: none;
	}
</style>
