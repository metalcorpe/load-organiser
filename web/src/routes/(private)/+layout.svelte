<script lang="ts">
	import { page } from '$app/state';
	import Notice from '#lib/components/Notice.svelte';
	import type { LayoutProps } from './$types';

	let { data, children }: LayoutProps = $props();
</script>

<!-- Profile has its own resend button next to the account details. -->
{#if data.viewer && !data.viewer.emailVerified && page.url.pathname !== '/profile'}
	<Notice title="Confirm your email" tone="warn">
		<p>Saving private records needs a confirmed email. Use the link we sent to {data.viewer.email}.</p>
		<form method="POST" action="/profile?/resend">
			<button class="button secondary" type="submit">Send a new link</button>
		</form>
	</Notice>
{/if}

{@render children()}

<style>
	form {
		margin-top: 0.75rem;
	}
</style>
