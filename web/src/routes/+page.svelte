<script lang="ts">
	import Notice from '#lib/components/Notice.svelte';
</script>

<svelte:head>
	<title>Discover · Load Organiser</title>
	<meta
		name="description"
		content="Find dated skydiving events, boogies, camps and courses in Europe. Listings are not published yet."
	/>
</svelte:head>

<h1>Discover</h1>
<p class="lede">
	Dated skydiving events, boogies, camps and courses in Europe, linked to their original organizers.
</p>

<Notice title="No listings published yet" tone="warn">
	<p>
		Discovery is not available in this preview. Listings will appear only after curated,
		source-backed records have been reviewed, so nothing here represents real availability.
	</p>
</Notice>

<p>
	Looking for a dropzone? Browse the <a href="/dz">dropzone directory</a> of source-backed listings.
</p>

<p>You can check whether the service is reachable on the <a href="/status">service status</a> page.</p>
