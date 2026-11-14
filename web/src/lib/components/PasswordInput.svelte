<script lang="ts">
	import { onMount } from 'svelte';

	/**
	 * A password input with a Show/Hide button beside it. The button is added once the page is
	 * interactive (without JavaScript it could do nothing). Showing changes only the input's type:
	 * name and autocomplete stay as given, so password managers fill and save as before. The
	 * password is hidden again whenever its form is sent.
	 *
	 * `what` names the field in the button's accessible name ("Show password", "Hide repeated
	 * password"); the visible text is just "Show" or "Hide".
	 */
	let {
		id,
		name,
		autocomplete,
		what = 'password',
		required = false,
		minlength,
		maxlength,
		invalid = false,
		describedby,
		input = $bindable()
	}: {
		id: string;
		name: string;
		autocomplete: 'current-password' | 'new-password';
		what?: string;
		required?: boolean;
		minlength?: number;
		maxlength?: number;
		invalid?: boolean;
		describedby?: string;
		input?: HTMLInputElement;
	} = $props();

	let shown = $state(false);
	let ready = $state(false);

	onMount(() => {
		ready = true;
		const form = input?.form;
		// Hidden again before the form is sent, and before the page goes away: a field left as
		// type=text can be stored by the browser's session restore (Firefox) or form cache.
		// The type is set directly too, because leaving the page does not wait for a re-render.
		const hide = () => {
			shown = false;
			if (input) input.type = 'password';
		};
		form?.addEventListener('submit', hide);
		window.addEventListener('pagehide', hide);
		window.addEventListener('beforeunload', hide);
		return () => {
			form?.removeEventListener('submit', hide);
			window.removeEventListener('pagehide', hide);
			window.removeEventListener('beforeunload', hide);
		};
	});
</script>

<div class="password">
	<input
		bind:this={input}
		{id}
		{name}
		type={shown ? 'text' : 'password'}
		{autocomplete}
		{required}
		{minlength}
		{maxlength}
		autocapitalize="off"
		spellcheck="false"
		aria-invalid={invalid ? 'true' : undefined}
		aria-describedby={describedby || undefined}
	/>
	{#if ready}
		<button type="button" class="toggle" aria-controls={id} onclick={() => (shown = !shown)}>
			{shown ? 'Hide' : 'Show'}<span class="visually-hidden"> {what}</span>
		</button>
	{/if}
</div>

<style>
	.password {
		display: flex;
		gap: 0.5rem;
		min-width: 0;
	}

	.password input {
		flex: 1;
	}

	.toggle {
		flex: none;
		min-width: 4.25rem;
		min-height: 44px;
		padding: 0 0.75rem;
		border: 1px solid var(--field-border);
		border-radius: 9px;
		background: var(--surface);
		color: var(--accent);
		font: inherit;
		font-weight: 650;
		cursor: pointer;
	}
</style>
