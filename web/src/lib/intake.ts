/** Owner switches as the web app sees them (#162). Client-safe. */

/**
 * Whether the submit form should show "Sending is paused". When the check itself fails
 * the answer is unknown: the form stays, and sending reports a pause if there is one.
 */
export function intakePaused(intake: { ok: true; value: { open: boolean } } | { ok: false }): boolean {
	return intake.ok && !intake.value.open;
}
