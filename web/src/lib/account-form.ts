/**
 * Field-level checks for the sign-in and registration forms, shared by the server actions
 * (the no-JavaScript path, always authoritative) and the sign-in sheet (checked before
 * sending). Only presence, a basic address shape and the repeated password are checked here:
 * password length and every account rule stay with the API, so nothing is weakened or
 * duplicated, and nothing here can tell whether an account exists.
 */
import { AUTH_MESSAGES } from '#lib/auth-messages.ts';

export type AccountField = 'email' | 'display_name' | 'password' | 'password_confirm';

/** Field name → error code; only the fields with a problem. */
export type FieldErrors = Partial<Record<AccountField, string>>;

/** Field order on the forms: the first problem in this order is the one focused. */
const ORDER: readonly AccountField[] = ['email', 'display_name', 'password', 'password_confirm'];

// Something before and after one @, without spaces: enough to catch a typo or a name typed in
// the wrong box. The API remains the judge of a valid address.
const EMAIL_SHAPE = /^[^\s@]+@[^\s@]+$/;

function emailError(email: string): string | undefined {
	if (!email) return 'email_required';
	if (!EMAIL_SHAPE.test(email)) return 'email_invalid';
	return undefined;
}

function compact(errors: Record<string, string | undefined>): FieldErrors {
	return Object.fromEntries(Object.entries(errors).filter(([, code]) => code)) as FieldErrors;
}

export function signInErrors({ email, password }: { email: string; password: string }): FieldErrors {
	return compact({
		email: emailError(email),
		password: password ? undefined : 'password_required'
	});
}

/** The name is optional and never checked here. */
export function registrationErrors({
	email,
	password,
	confirm
}: {
	email: string;
	password: string;
	confirm: string;
}): FieldErrors {
	return compact({
		email: emailError(email),
		password: password ? undefined : 'new_password_required',
		password_confirm: !confirm
			? password
				? 'password_confirm_required'
				: undefined
			: confirm !== password
				? 'password_mismatch'
				: undefined
	});
}

/** The API's refusals that are about one field of these forms. */
const REASON_FIELD: Record<string, AccountField> = {
	password_too_short: 'password',
	password_too_long: 'password'
};

export function fieldErrorsForReason(reason: string | undefined): FieldErrors {
	const name = reason ? REASON_FIELD[reason] : undefined;
	return name ? { [name]: reason as string } : {};
}

/** The first field with a problem, in form order. */
export function firstInvalid(errors: FieldErrors): AccountField | undefined {
	return ORDER.find((name) => errors[name]);
}

export function fieldMessage(code: string | undefined): string | undefined {
	return code ? (AUTH_MESSAGES[code] ?? AUTH_MESSAGES.invalid_input) : undefined;
}

/** One sentence per problem, in form order: the form's alert. */
export function errorSummary(errors: FieldErrors): string | undefined {
	const messages = ORDER.flatMap((name) => (errors[name] ? [fieldMessage(errors[name])] : []));
	return messages.length ? messages.join(' ') : undefined;
}
