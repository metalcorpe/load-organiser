<script lang="ts">
	import { page } from '$app/state';

	const notFound = $derived(page.status === 404);
</script>

<svelte:head>
	<title>{notFound ? 'Page not found' : 'Something went wrong'} · Load Organiser</title>
</svelte:head>

<h1>{notFound ? 'Page not found' : 'Something went wrong'}</h1>
<p role="alert">
	{#if notFound}
		This page is unavailable.
	{:else}
		{page.error?.message ?? 'The page could not be loaded.'} (Error {page.status})
	{/if}
</p>
<p><a class="button secondary" href="/">Go to Discover</a></p>
