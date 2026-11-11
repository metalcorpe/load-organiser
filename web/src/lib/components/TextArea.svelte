<script lang="ts">
	import type { HTMLTextareaAttributes } from 'svelte/elements';

	/**
	 * A textarea that keeps both the saved text and early typing.
	 *
	 * The server renders `initial` as the content, so forms work without JavaScript and an
	 * early submit never posts an empty field. `bind:value` lets Svelte keep text typed before
	 * hydration (it compares the field's value with its default when hydrating).
	 */
	let { initial = '', ...rest }: { initial?: string | null } & HTMLTextareaAttributes = $props();
	// Intentionally the first value only: after load the field owns its text.
	// svelte-ignore state_referenced_locally
	let value = $state(initial ?? '');
</script>

<textarea {...rest} bind:value></textarea>
