<script lang="ts">
	import { goto } from '$app/navigation';
	import DestinationList, { type DestinationGroup } from '#lib/components/DestinationList.svelte';
	import { authMessage } from '#lib/auth-messages.ts';
	import { LICENCE_LABEL, isLicence } from '#lib/currency.ts';
	import { formatWeight } from '#lib/wing-loading.ts';
	import { onMount } from 'svelte';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();
	const account = $derived(data.account);
	// The account's name, else the public profile's; without either, the email alone, once.
	const named = $derived(account.displayName ?? (data.profile ? data.profile.displayName : null));
	const name = $derived(named ?? account.email);
	const initials = $derived(
		name
			.split(/[\s@._-]+/)
			.filter(Boolean)
			.slice(0, 2)
			.map((part) => part[0]!.toUpperCase())
			.join('')
	);
	const resendError = $derived(
		form && form.form === 'resend' && 'error' in form ? authMessage(form.error) : undefined
	);
	const resent = $derived(Boolean(form && form.form === 'resend' && 'done' in form && form.done));

	const n = (count: number, one: string, many: string) =>
		`${count.toLocaleString('en-GB')} ${count === 1 ? one : many}`;
	const plansSummary = $derived(
		data.plans === null || data.saved === null
			? 'Visit plans and events you saved'
			: `${n(data.plans, 'plan', 'plans')} · ${n(data.saved, 'saved event', 'saved events')}`
	);
	// "None" alone reads as nothing loaded; on its own row it says what it is.
	const licenceSummary = $derived(
		data.licence === null
			? 'Could not be loaded'
			: data.licence === 'none' || !isLicence(data.licence)
				? 'No licence'
				: LICENCE_LABEL[data.licence]
	);
	const weight = $derived(data.exitWeight?.exit_weight ?? null);
	const weightSummary = $derived(
		data.exitWeight === null ? 'Could not be loaded' : weight ? formatWeight(weight.grams, weight.unit) : 'Not set'
	);
	const profileSummary = $derived(
		data.profile === undefined
			? 'How others find you'
			: data.profile === null
				? 'Not set up: needed to follow people'
				: `@${data.profile.handle} · ${data.profile.discoverable ? 'people can find you' : 'only approved followers see it'}`
	);

	const groups = $derived<DestinationGroup[]>([
		{
			id: 'plans',
			heading: 'Plans and gear',
			items: [
				{ href: '/plans', label: 'Plans and saved events', summary: plansSummary },
				{ href: '/gear', label: 'Gear', summary: 'Containers, canopies, AADs and service dates' }
			]
		},
		{
			id: 'preferences',
			heading: 'Profile and jump preferences',
			items: [
				// The old anchors of these settings on this page (#licence-heading, #weight-heading)
				// land on these rows, and with scripts on go on to the form (below).
				{
					href: '/profile/preferences#licence-heading',
					id: 'licence-heading',
					label: 'Licence',
					summary: licenceSummary,
					verb: 'Edit'
				},
				{
					href: '/profile/preferences#weight-heading',
					id: 'weight-heading',
					label: 'Exit weight',
					summary: weightSummary,
					verb: 'Edit'
				},
				{ href: '/profile/public', label: 'Public profile', summary: profileSummary, verb: 'Edit' }
			]
		},
		{
			id: 'account',
			heading: 'Account',
			items: [
				{
					href: '/profile/account',
					label: 'Account and security',
					summary: 'Password, signing out everywhere, deleting your account'
				}
			]
		},
		{
			id: 'data',
			heading: 'Your data',
			items: [
				{ href: '/records/import', label: 'Import a logbook', summary: 'From a spreadsheet (CSV)' },
				{ href: '/profile/data', label: 'Export or restore', summary: 'All your records as one file' },
				{ href: '/records/print', label: 'Printable logbook', summary: 'Paper or PDF, with a signature column' }
			]
		},
		{
			id: 'more',
			heading: 'More',
			quiet: true,
			items: [
				{ href: '/places', label: 'Private places' },
				{ href: '/submit', label: 'Suggestions and reports' },
				{ href: '/submit?kind=feedback', label: 'Send feedback' },
				{ href: '/privacy', label: 'Privacy and the beta' },
				...(data.viewer?.reviewer ? [{ href: '/review', label: 'Maintenance (reviewer tools)' }] : [])
			]
		}
	]);

	// Links from before the settings had their own page point at their anchors here: go on to
	// the form itself. Without scripts the anchor is the setting's row, one tap from it.
	onMount(() => {
		if (location.hash === '#licence-heading' || location.hash === '#weight-heading') {
			void goto(`/profile/preferences${location.hash}`, { replaceState: true });
		}
	});
</script>

<svelte:head>
	<title>Me · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<h1>Me</h1>

<section class="identity" aria-label="Your account">
	<span class="avatar" aria-hidden="true">{initials}</span>
	<div class="who">
		<p class="name wrap-anywhere" data-testid={named ? undefined : 'account-email'}>{name}</p>
		<p class="meta">
			{#if named}<span class="wrap-anywhere" data-testid="account-email">{account.email}</span>{/if}
			<span data-testid="email-status">{account.emailVerified ? 'Email confirmed' : 'Email not confirmed'}</span>
		</p>
	</div>
	<form method="POST" action="/sign-out" class="sign-out">
		<button class="button secondary" type="submit">Sign out</button>
	</form>
</section>

<!-- The banner on every private page asks to confirm the address; its button lands here. -->
{#if resent}
	<p role="status" class="ok">We sent a new confirmation link. It expires in 30 minutes.</p>
{:else if resendError}
	<p class="form-error" role="alert">{resendError}</p>
{/if}

<nav aria-label="Your things and settings">
	<DestinationList {groups} />
</nav>

<style>
	/* Who is signed in: the screen's one summary, quiet; the rows below are the content. */
	.identity {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.75rem 1rem;
		margin: 0.25rem 0 1.5rem;
	}

	.avatar {
		display: inline-grid;
		place-items: center;
		flex: none;
		width: 3rem;
		height: 3rem;
		border-radius: 999px;
		background: var(--brand);
		color: var(--brand-fg);
		font-family: var(--font-display);
		font-weight: 600;
	}

	.who {
		flex: 1 1 12rem;
		min-width: 0;
	}

	.who p {
		margin: 0;
	}

	.name {
		font-weight: 700;
		font-size: 1.1rem;
	}

	.meta {
		display: flex;
		flex-wrap: wrap;
		gap: 0 0.75rem;
		color: var(--muted);
		font-size: 0.9rem;
	}

	.sign-out {
		margin: 0;
	}

	nav {
		margin-top: 1rem;
	}
</style>
