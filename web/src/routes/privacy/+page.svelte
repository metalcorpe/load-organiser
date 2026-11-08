<svelte:head>
	<title>Privacy and the beta · Load Organiser</title>
	<meta
		name="description"
		content="What Load Organiser keeps private, what you can share, how deletion and recovery work, and the beta's known limits."
	/>
</svelte:head>

<h1>Privacy and the beta</h1>
<p class="lede">
	What this beta keeps private, what you choose to share, what deleting your account removes, and
	what does not work yet. It describes the current version and changes with it.
</p>

<nav aria-label="On this page" class="toc">
	<ul>
		<li><a href="#private">Private by default</a></li>
		<li><a href="#sharing">What you can share</a></li>
		<li><a href="#reviewers">Reports and reviewers</a></li>
		<li><a href="#account">Your account and sign-in</a></li>
		<li><a href="#data">Export and restore</a></li>
		<li><a href="#deletion">Deleting your account</a></li>
		<li><a href="#recovery">Backups and recovery</a></li>
		<li><a href="#limits">Known limits</a></li>
		<li><a href="#feedback">Feedback</a></li>
	</ul>
</nav>

<section aria-labelledby="private">
	<h2 id="private">Private by default</h2>
	<p>
		Your jumps and their notes, gear and serial numbers, service entries, private places, prior jump
		count, saved listings and visit plans are visible only to you. Following someone, or being
		followed, gives nobody access to them. Reviewers do not get routine access to them either.
	</p>
	<p>
		Nothing private is published automatically. Logging a jump never shares it, and a visit plan never
		appears in a feed, on a profile or on a dropzone page.
	</p>
</section>

<section aria-labelledby="sharing">
	<h2 id="sharing">What you can share</h2>
	<ul>
		<li>
			<strong>A public profile</strong> is optional and separate from your account: a handle, display
			name and, if you add them, a short bio, disciplines and a home dropzone. Your email, the name you
			registered with, your logbook and totals are never copied into it. Others can find it only if
			you turn on "Let people find my profile".
		</li>
		<li>
			<strong>Follows</strong> always need your approval.
		</li>
		<li>
			<strong>Shared jumps</strong> are published one at a time from a preview. Only the activity date
			is always included; jump type, listed dropzone, exit altitude and freefall time are your choice,
			with an optional caption and link. Notes, equipment, serial numbers, jump numbers and private
			places are never shared.
		</li>
		<li>
			<strong>Audience:</strong> approved followers, including people you approve later, or public.
			Public posts can be read by anyone, including people who are not signed in; blocking someone
			cannot hide public content from them if they sign out.
		</li>
		<li>
			<strong>Taking it back:</strong> unpublishing, narrowing the audience, removing a follower,
			blocking or deleting your account stops the service from showing the post on the next page
			load. Nobody can recall screenshots or copies already made.
		</li>
	</ul>
</section>

<section aria-labelledby="reviewers">
	<h2 id="reviewers">Reports and reviewers</h2>
	<p>
		Reviewers, at first the people running the beta, check reported profiles and posts and suggestions
		about listings. When you report a profile or post, the reviewer sees your handle and display name
		so that misuse of reporting can be judged; the person you reported never sees who reported them. Suggestions, corrections and
		feedback reach reviewers without your name or email.
	</p>
	<p>
		A reviewer can hide a profile, stop it from publishing or remove a post, and must give a reason
		that the owner sees.
	</p>
</section>

<section aria-labelledby="account">
	<h2 id="account">Your account and sign-in</h2>
	<ul>
		<li>
			Your email address is used to sign in, to confirm the address, for password resets, and to tell
			you if someone tries to register with it again.
		</li>
		<li>
			Signing in sets one cookie that your browser cannot read from page scripts. A sign-in lasts at
			most seven days and is not extended by use; up to five can be active at once.
		</li>
		<li>
			You can sign out everywhere from your <a href="/profile">profile</a>. Changing your password
			signs out your other devices; a password reset signs out all of them.
		</li>
		<li>No advertising or analytics scripts run on these pages.</li>
	</ul>
</section>

<section aria-labelledby="data">
	<h2 id="data">Export and restore</h2>
	<p>
		From <a href="/profile/data">Your data</a> you can download your records as one JSON file at any
		time: jumps and their history, gear, prior jump count, private places, saved listings and plans.
		It contains your private notes and serial numbers, so keep it safe. It does not include your
		password, email address, profile, posts or anyone else's records.
	</p>
	<p>
		A restore brings an export back into empty records only. It never overwrites or merges, and does
		not republish posts. A saved listing that is no longer public is left out, and a dropzone that is
		no longer listed comes back as one of your private places.
	</p>
</section>

<section aria-labelledby="deletion">
	<h2 id="deletion">Deleting your account</h2>
	<p>
		From your <a href="/profile">profile</a>, with your password. Deletion is immediate and cannot
		be undone, so export first if you want a copy. It removes your account, sessions, public profile,
		follows both ways, blocks, posts, logbook, gear, places, history, saved listings, plans, and
		reports made by or about you.
	</p>
	<p>
		Kept without any link to you: suggestions, problem reports and feedback you sent, including what
		you wrote, and reviewers' records of decisions about public listings. If you are a reviewer, the
		reports you decided stay, without your name.
		Your email address can be used to register again; the new account starts empty.
	</p>
</section>

<section aria-labelledby="recovery">
	<h2 id="recovery">Backups and recovery</h2>
	<p>
		The plan for the beta is one encrypted database backup a day, keeping at most seven. These are
		operating targets, not a guarantee, and backups are not running yet. Do not keep the only copy of
		important records here: export them.
	</p>
	<p>If the service ever has to be restored from a backup:</p>
	<ul>
		<li>
			Deleted records, unpublished posts, blocks, removed follows, visibility changes, hidden or
			restricted profiles and removed posts are applied again before the service reopens, so they do
			not come back. This works for changes recorded in a copy kept apart from the backups; changes
			made after the last such copy can still come back, and how often copies are made is not settled.
			A deletion that would break a restored record, such as a private place a restored jump still
			uses, is listed for a person to resolve.
		</li>
		<li>
			To do this, the service keeps a record of the identifiers of deleted records and of the settings
			that changed, never notes, names or other content, until it is cleared after the backups that
			need it have expired.
		</li>
		<li>Everyone has to sign in again.</li>
		<li>If you changed your password after the backup, you will need to reset it by email.</li>
		<li>Other edits and records created after the backup may be lost.</li>
	</ul>
</section>

<section aria-labelledby="limits">
	<h2 id="limits">Known limits</h2>
	<ul>
		<li>
			Listings cover a limited set of dropzones and events, entered by hand from their own sources. An
			external link or saved plan is not a registration.
		</li>
		<li>
			No notifications, comments or reactions. No app to install and no offline use: this is a website
			for phones and computers.
		</li>
		<li>No grace period or undo after deleting your account.</li>
		<li>
			Text limits: jump notes 2,000 characters, gear notes 1,000, bio and captions 280. Storage and
			rate limits are set for a small beta and may change.
		</li>
	</ul>
</section>

<section aria-labelledby="feedback">
	<h2 id="feedback">Feedback</h2>
	<p>
		Signed in with a confirmed email address, you can
		<a href="/submit?kind=feedback">send feedback about the beta</a>, suggest a listing or correct one,
		and follow what happened to it on the same page. Sending can be paused while reviewers catch up;
		the form then says so when you send. To report a profile or post, use "Report" on its page.
	</p>
</section>

<style>
	section {
		margin-top: 1.75rem;
	}

	.toc ul {
		padding-left: 1.2rem;
	}

	.toc li,
	li {
		margin: 0.35rem 0;
	}

	.toc a {
		display: inline-block;
		min-height: 44px;
		line-height: 44px;
	}
</style>
