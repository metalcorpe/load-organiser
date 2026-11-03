import { fail } from '@sveltejs/kit';
import { statusFor } from '#lib/auth-messages.ts';
import { createRequestApi } from '#lib/server/api/client.ts';
import { field } from '#lib/server/forms.ts';
import { requestPasswordReset } from '#lib/server/identity.ts';
import type { Actions } from './$types';

export const actions: Actions = {
	default: async ({ request, getClientAddress }) => {
		const data = await request.formData();
		const email = field(data, 'email', { max: 254, trim: true });
		if (!email) return fail(400, { email, error: 'missing' });
		const outcome = await requestPasswordReset(createRequestApi(), email, getClientAddress());
		// Only service-wide failures are shown; never whether the account exists.
		if (!outcome.ok) return fail(statusFor(outcome.reason), { email, error: outcome.reason });
		return { sent: true };
	}
};
