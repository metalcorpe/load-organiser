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
	<meta name="description" content="Whether the Load Organiser API and database are reachable." />
</svelte:head>

<h1>Service status</h1>
<p class="lede">A live check of the Load Organiser API and its database, run when this page loads.</p>

<div data-testid="health" data-state={health.kind}>
	{#if health.kind === 'operational'}
		<Notice title="Operational" tone="ok">
			<p>The API and its database responded.</p>
			<p>Checked <time datetime={health.checkedAt}>{formatUtc(health.checkedAt)}</time>.</p>
		</Notice>
	{:else if health.kind === 'degraded'}
		<Notice title="Degraded" tone="bad">
			<p>The API responded, but it cannot reach its database. Saving or reading records would fail.</p>
			<p>Checked <time datetime={health.checkedAt}>{formatUtc(health.checkedAt)}</time>.</p>
		</Notice>
	{:else if health.kind === 'timeout'}
		<Notice title="No response yet" tone="warn">
			<p>
				The API did not answer within {API_TIMEOUT_MS / 1000} seconds. That does not prove it is
				down; it may be starting up.
			</p>
		</Notice>
	{:else if health.kind === 'unreachable'}
		<Notice title="API unreachable" tone="bad">
			<p>The web server could not connect to the API.</p>
		</Notice>
	{:else if health.kind === 'upstream_error'}
		<Notice title="Unexpected API response" tone="bad">
			<p>The API answered with HTTP {health.status}.</p>
		</Notice>
	{:else if health.kind === 'invalid_response'}
		<Notice title="Unexpected API response" tone="bad">
			<p>The API answered, but not in the expected format.</p>
		</Notice>
	{:else}
		<Notice title="Not configured" tone="warn">
			<p>This deployment has no API origin configured.</p>
		</Notice>
	{/if}
</div>

<form method="GET" data-sveltekit-reload>
	<button class="button" type="submit">Check again</button>
</form>
