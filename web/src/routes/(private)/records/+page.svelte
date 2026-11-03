<script lang="ts">
	import Notice from '#lib/components/Notice.svelte';
</script>

<svelte:head>
	<title>Records · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<h1>Records</h1>
<p class="lede">Your logbook, gear and saved visits.</p>

<ul>
	<li><a href="/gear">Gear</a>: your containers, canopies and AADs, rigs and service dates.</li>
	<li><a href="/saved">Saved listings</a>: private bookmarks from Discover.</li>
	<li><a href="/plans">Visit plans</a>: your own dated plans, visible only to you.</li>
	<li><a href="/places">Private places</a>: dropzones and fields you keep for your own records.</li>
	<li><a href="/submit">Suggestions and reports</a>: what you sent and its status.</li>
</ul>

<Notice title="Logbook not available yet" tone="warn">
	<p>Jump entries have not been built yet.</p>
</Notice>
