import { fail, redirect } from '@sveltejs/kit';
import { safeReturnPath } from '#lib/safe-return.ts';
import { statusFor } from '#lib/auth-messages.ts';
import { fieldErrorsForReason, firstInvalid, registrationErrors } from '#lib/account-form.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { field } from '#lib/server/forms.ts';
import { register } from '#lib/server/identity.ts';
import type { Actions, PageServerLoad } from './$types';

export const load: PageServerLoad = ({ locals, url }) => {
	const returnTo = safeReturnPath(url.searchParams.get('returnTo'));
	if (locals.viewer) redirect(303, returnTo ?? '/profile');
	return { returnTo };
};

export const actions: Actions = {
	default: async ({ request, getClientAddress }) => {
		const data = await request.formData();
		const email = field(data, 'email', { max: 254, trim: true });
		const displayName = field(data, 'display_name', { max: 80, trim: true });
		const password = field(data, 'password', { max: 1024 });
		const confirm = field(data, 'password_confirm', { max: 1024 });
		// Only the non-secret values come back; passwords are never echoed.
		const echo = { email, displayName };

		const fields = registrationErrors({ email, password, confirm });
		const first = firstInvalid(fields);
		// `error` is the first problem's code, so FormGuard focuses that field.
		if (first) return fail(400, { ...echo, error: fields[first], fields });

		const outcome = await register(
			createRequestApi(),
			{ email, password, display_name: displayName || null },
			getClientAddress()
		);
		if (!outcome.ok) {
			return fail(statusFor(outcome.reason), {
				...echo,
				error: outcome.reason,
				fields: fieldErrorsForReason(outcome.reason)
			});
		}
		// Neutral: the same answer whether or not the email already had an account.
		return { sent: true, email };
	}
};
