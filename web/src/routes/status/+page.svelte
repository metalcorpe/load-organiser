<script lang="ts">
	import Notice from '#lib/components/Notice.svelte';
	import { API_TIMEOUT_MS } from '#lib/api-timeouts.ts';
	import type { PageProps } from './$types';

	let { data }: PageProps = $props();
	const health = $derived(data.health);

	function formatUtc(iso: string): string {
		return `${iso.slice(0, 10)} ${iso.slice(11, 19)} UTC`;
	}
</script>

<svelte:head>
	<title>Service status · Load Organiser</title>
	<meta name="description" content="Whether Load Organiser is working right now." />
</svelte:head>

<h1>Service status</h1>
<p class="lede">Whether Load Organiser is working right now. Checked each time this page loads.</p>

<div data-testid="health" data-state={health.kind}>
	{#if health.kind === 'operational'}
		<Notice title="Operational" tone="ok">
			<p>The service and its database responded.</p>
			<p>Checked <time datetime={health.checkedAt}>{formatUtc(health.checkedAt)}</time>.</p>
		</Notice>
	{:else if health.kind === 'degraded'}
		<Notice title="Degraded" tone="bad">
			<p>The service is up but cannot reach its database. Reading and saving records will fail.</p>
			<p>Checked <time datetime={health.checkedAt}>{formatUtc(health.checkedAt)}</time>.</p>
		</Notice>
	{:else if health.kind === 'timeout'}
		<Notice title="No response yet" tone="warn">
			<p>
				The service did not answer within {API_TIMEOUT_MS / 1000} seconds. It may be starting up: check
				again in a minute.
			</p>
		</Notice>
	{:else if health.kind === 'unreachable'}
		<Notice title="Service unreachable" tone="bad">
			<p>This site could not connect to the service. Signing in and your records are unavailable.</p>
		</Notice>
	{:else if health.kind === 'upstream_error'}
		<Notice title="Unexpected response" tone="bad">
			<p>The service answered with an error (HTTP {health.status}).</p>
		</Notice>
	{:else if health.kind === 'invalid_response'}
		<Notice title="Unexpected response" tone="bad">
			<p>The service answered, but not as expected.</p>
		</Notice>
	{:else}
		<Notice title="Not configured" tone="warn">
			<p>This site is not connected to a service yet.</p>
		</Notice>
	{/if}
</div>

<form method="GET" data-sveltekit-reload>
	<button class="button" type="submit">Check again</button>
</form>
