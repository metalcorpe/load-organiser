<script lang="ts">
	import Notice from '#lib/components/Notice.svelte';
	import type { LayoutProps } from './$types';

	let { data, children }: LayoutProps = $props();
</script>

<!-- On every private page, Me included; its button's result shows on Me. -->
{#if data.viewer && !data.viewer.emailVerified}
	<Notice title="Confirm your email" tone="warn">
		<p>Saving private records needs a confirmed email. Use the link we sent to
			<span class="wrap-anywhere">{data.viewer.email}</span>.
		</p>
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
