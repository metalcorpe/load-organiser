<script lang="ts">
	import Notice from '#lib/components/Notice.svelte';
</script>

<svelte:head>
	<title>Records · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<h1>Records</h1>
<p class="lede">Your logbook, gear and saved visits.</p>

<p><a href="/places">Private places</a>: dropzones and fields you keep for your own records.</p>

<Notice title="Logbook and gear not available yet" tone="warn">
	<p>Jump entries, gear and saved visits have not been built yet.</p>
</Notice>
