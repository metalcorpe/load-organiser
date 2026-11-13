/** User-facing text for identity outcomes. No upstream detail is ever shown. */
export const AUTH_MESSAGES: Record<string, string> = {
	missing: 'Fill in every field.',
	// One field each (sign-in and registration: account-form.ts).
	email_required: 'Enter your email address.',
	email_invalid: 'Enter an email address in the form name@example.com.',
	password_required: 'Enter your password.',
	new_password_required: 'Choose a password of 15 to 128 characters.',
	password_confirm_required: 'Enter the same password again.',
	invalid_credentials: 'Email or password is incorrect.',
	not_authenticated: 'Your session has ended. Sign in again.',
	too_many_attempts: 'Too many attempts. Wait a while, then try again.',
	registration_closed: 'Registration is closed for this beta right now.',
	invalid_or_expired_token:
		'This link is invalid, expired or already used. Request a new one below.',
	password_too_short: 'Use at least 15 characters.',
	password_too_long: 'Use at most 128 characters.',
	password_mismatch: 'The two new passwords do not match.',
	password_confirmation_failed: 'That password is incorrect.',
	confirm_delete: 'Tick the box to confirm that you want to delete your account.',
	mail_unavailable: 'Email cannot be sent right now, so this cannot continue. Try again later.',
	invalid_input: 'Check the details you entered.',
	uncertain:
		'The service did not answer in time. Your request may or may not have gone through; check before trying again.',
	unavailable: 'The service is unavailable right now. Try again later.'
};

export function authMessage(code: string | undefined): string | undefined {
	return code ? (AUTH_MESSAGES[code] ?? AUTH_MESSAGES.unavailable) : undefined;
}

export function statusFor(reason: string): number {
	switch (reason) {
		case 'too_many_attempts':
			return 429;
		case 'unavailable':
		case 'uncertain':
		case 'mail_unavailable':
			return 503;
		case 'registration_closed':
			return 403;
		default:
			return 400;
	}
}
