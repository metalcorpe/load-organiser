<script lang="ts">
	import Notice from '#lib/components/Notice.svelte';
	import type { LayoutProps } from './$types';

	let { data, children }: LayoutProps = $props();
</script>

{#if data.viewer && !data.viewer.emailVerified}
	<Notice title="Confirm your email" tone="warn">
		<p>
			Saving private records needs a confirmed email. Use the link we sent, or send a new one from
			<a href="/profile">Profile</a>.
		</p>
	</Notice>
{/if}

{@render children()}
