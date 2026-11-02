// See https://svelte.dev/docs/kit/types#app.d.ts
import type { Viewer } from '#lib/server/viewer.ts';

declare global {
	namespace App {
		interface Locals {
			/** Request-local; always null until backend sessions land in #145. */
			viewer: Viewer | null;
		}
	}
}

export {};
