<script lang="ts">
	import { formatDay } from '#lib/listings.ts';
	import { DECISIONS, REPORT_REASONS, disciplineLabel, socialMessage } from '#lib/social.ts';
	import type { PageProps } from './$types';

	let { data, form }: PageProps = $props();
	const errorFor = (name: string, key: string) =>
		form && form.form === name && 'error' in form && (('id' in form && form.id === key) || ('handle' in form && form.handle === key))
			? socialMessage(form.error)
			: undefined;
	const day = (instant: string) => formatDay(instant.slice(0, 10));
	const text = (value: unknown) =>
		(typeof value === 'string' && value) || (typeof value === 'number' && String(value)) || '–';
	const reported = (snapshot: Record<string, unknown>) =>
		(snapshot.post && typeof snapshot.post === 'object' ? snapshot.post : {}) as Record<string, unknown>;
	const decisions = (isPost: boolean) =>
		Object.entries(DECISIONS).filter(([value]) => isPost || value !== 'remove_post');
</script>

<svelte:head>
	<title>Profile reports · Maintenance · Load Organiser</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<p><a href="/review">Maintenance</a></p>
<h1>Profile reports</h1>
<p class="lede">
	Reports about public profiles, separate from listing corrections. You see the reported profile's
	public fields and the report, never anyone's logbook or gear. The reported person is not told
	who reported them.
</p>
<p class="actions">
	<a href="/review/social" aria-current={data.status === 'open' ? 'page' : undefined}>Open</a>
	<a href="/review/social?status=closed" aria-current={data.status === 'closed' ? 'page' : undefined}>Decided</a>
</p>

{#if !data.reports.ok}
	<p class="form-error" role="alert">{socialMessage(data.reports.reason)}</p>
{:else if data.reports.items.length === 0}
	<p class="hint">{data.status === 'open' ? 'No open reports.' : 'No decided reports yet.'}</p>
{:else}
	<ul class="results rows" aria-label="Reports">
		{#each data.reports.items as report (report.id)}
			<li>
				<span class="title wrap-anywhere"
					>{report.post_id ? 'Shared jump by ' : ''}@{report.target.handle} · {report.target.display_name}</span
				>
				<span class="meta">
					{REPORT_REASONS[report.reason] ?? report.reason} · reported {day(report.created_at)}
					by {report.reporter ? `@${report.reporter.handle}` : 'an account without a profile'}
				</span>
				{#if report.note}<span class="meta">“{report.note}”</span>{/if}
				{#if report.post_id}
					{@const post = reported(report.snapshot)}
					<span class="meta">
						As reported: jumped {text(post.jumped_on)}; type: {text(post.jump_type)}; dropzone:
						{text(post.venue)}; exit altitude: {text(post.exit_altitude)}
						{post.altitude_unit ? text(post.altitude_unit) : ''}; freefall: {text(post.freefall_seconds)};
						audience: {text(post.audience)}
					</span>
					<span class="meta">Caption: {text(post.caption)}; link: {text(post.link)}</span>
					<span class="meta">
						Now: post {report.post_live ? 'published' : 'no longer published'}; profile
						{report.target_hidden ? 'hidden' : 'visible'}{report.target_publishing_restricted ? ', publishing restricted' : ''}
					</span>
				{:else}
					<span class="meta">
						As reported: {text(report.snapshot.display_name)}; bio: {text(report.snapshot.bio)}; disciplines:
						{Array.isArray(report.snapshot.disciplines) && report.snapshot.disciplines.length
							? report.snapshot.disciplines.map((d) => disciplineLabel(String(d))).join(', ')
							: '–'}
					</span>
					<span class="meta">
						Now: {report.target_hidden ? 'hidden' : 'visible'}{report.target_publishing_restricted ? ', publishing restricted' : ''}
					</span>
				{/if}

				{#if report.status === 'open'}
					<form method="POST" action="?/decide" class="form">
						{#if errorFor('decide', report.id)}<p class="form-error" role="alert">{errorFor('decide', report.id)}</p>{/if}
						<input type="hidden" name="id" value={report.id} />
						<div class="field">
							<label for="decision-{report.id}">Decision</label>
							<select id="decision-{report.id}" name="decision">
								{#each decisions(report.post_id !== null && report.post_id !== undefined) as [value, label] (value)}
									<option {value}>{label}</option>
								{/each}
							</select>
						</div>
						<div class="field">
							<label for="reason-{report.id}">Reason (shown to the profile owner; required unless no action)</label>
							<input id="reason-{report.id}" name="reason" maxlength="280" />
						</div>
						<div class="form-actions"><button class="button" type="submit">Record decision</button></div>
					</form>
				{:else}
					<span class="meta">
						Decided {report.decided_at ? day(report.decided_at) : ''}: {DECISIONS[report.decision ?? ''] ?? report.decision}{report.decision_reason
							? ` (${report.decision_reason})`
							: ''}
					</span>
					{#if report.target_hidden || report.target_publishing_restricted}
						<form method="POST" action="?/moderate" class="form">
							{#if errorFor('moderate', report.target.handle)}<p class="form-error" role="alert">{errorFor('moderate', report.target.handle)}</p>{/if}
							{#if form && form.form === 'moderate' && 'done' in form && form.handle === report.target.handle}<p role="status" class="ok">Updated.</p>{/if}
							<input type="hidden" name="handle" value={report.target.handle} />
							<label class="choice"><input type="checkbox" name="hidden" checked={report.target_hidden} /> Keep hidden</label>
							<label class="choice"><input type="checkbox" name="restricted" checked={report.target_publishing_restricted} /> Keep publishing restricted</label>
							<div class="field">
								<label for="mod-{report.id}">Reason for the change</label>
								<input id="mod-{report.id}" name="reason" maxlength="280" />
							</div>
							<div class="form-actions"><button class="button secondary" type="submit">Update restrictions</button></div>
						</form>
					{/if}
				{/if}
			</li>
		{/each}
	</ul>
{/if}
