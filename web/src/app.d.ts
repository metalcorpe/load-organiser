// See https://svelte.dev/docs/kit/types#app.d.ts
import type { Viewer } from '#lib/server/identity.ts';

declare global {
	namespace App {
		interface Locals {
			/** Request-local identity validated by the API for this request only. */
			viewer: Viewer | null;
			/** A session cookie was present but the API could not be reached to confirm it. */
			sessionUnconfirmed: boolean;
			/** Set by account-changing actions; the hook adds `Clear-Site-Data: "cache"`. */
			clearSiteCache?: boolean;
		}
		interface PageState {
			/** Return path while the sign-in sheet is open (shallow routing; Back closes it). */
			signIn?: string;
		}
	}
}

export {};
