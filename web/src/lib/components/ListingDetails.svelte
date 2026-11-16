<script lang="ts">
	import { formatDay, hostOf } from '#lib/listings.ts';

	/**
	 * Where a public listing came from, folded under "Listing details": secondary to the facts
	 * and actions above it. Only what is known is shown; with nothing known it renders nothing,
	 * so there is never an empty label or a disclosure that opens onto nothing.
	 *
	 * `checkedOn` is the day a reviewer last checked the listing against its source, so it is
	 * labelled as exactly that: not "verified" or "confirmed" by the place or organizer.
	 * The source is attribution: it may be a third party, so it is never called "official".
	 */
	let {
		sourceUrl = null,
		checkedOn = null,
		note = null
	}: {
		sourceUrl?: string | null;
		checkedOn?: string | null;
		/** One short line on what the listing is, shown under the facts. */
		note?: string | null;
	} = $props();

	const host = $derived(sourceUrl ? hostOf(sourceUrl) : null);
</script>

{#if sourceUrl || checkedOn}
	<details class="listing-details">
		<summary>Listing details</summary>
		<dl>
			{#if sourceUrl}
				<dt>Source</dt>
				<dd>
					<a href={sourceUrl} rel="external noopener noreferrer nofollow">{host}</a>
				</dd>
			{/if}
			{#if checkedOn}
				<dt>Last checked against the source</dt>
				<dd><time datetime={checkedOn}>{formatDay(checkedOn)}</time></dd>
			{/if}
		</dl>
		{#if note}<p>{note}</p>{/if}
	</details>
{/if}

<style>
	.listing-details {
		/* The layout follows the disclosure's own width, not the window's: the same component
		   sits in full-width and narrow columns. */
		container-type: inline-size;
		margin: 1.25rem 0 0.5rem;
		border-top: 1px solid var(--border);
		padding-top: 0.25rem;
		color: var(--muted);
	}

	/* Narrow: each label above its value, so a long label never squeezes the value (a source
	   domain) into a sliver. */
	dl {
		display: grid;
		grid-template-columns: minmax(0, 1fr);
		margin: 0.25rem 0 0.5rem;
	}

	dd {
		margin: 0 0 0.5rem;
		overflow-wrap: anywhere;
		color: var(--fg);
	}

	/* Wide enough for both: labels in a capped first column, values in the rest. */
	@container (min-width: 30rem) {
		dl {
			grid-template-columns: minmax(8rem, 15rem) minmax(0, 1fr);
			gap: 0.35rem 1rem;
		}

		dd {
			margin: 0;
		}
	}

	p {
		margin: 0 0 0.5rem;
		max-width: var(--measure);
	}
</style>
